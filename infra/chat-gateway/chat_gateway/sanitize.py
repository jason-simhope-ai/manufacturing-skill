"""Inbound normalisation, UNTRUSTED envelopes, tripwires, DLP and output filtering (§9.4, §11.1, §11.5).

Everything here is pure and deterministic given its inputs; randomness (envelope
ids) is injected by the caller.
"""
from __future__ import annotations

import re
import secrets
import unicodedata
from pathlib import Path
from typing import Callable, Iterable

from . import tier_rank
from .patterns import DLP_PATTERNS, DLP_TIERS, GENERIC_SECRET, SECRET_PATTERNS, valid_ubn

# ── inbound normalisation ────────────────────────────────────────────
# Invisible / format characters that can split a marker ("機\u00ad密") without being
# seen. Every Unicode category-Cf character (zero-width, bidi controls, soft hyphen,
# U+2060–2064, U+180E, tags U+E0000–E007F, …) is removed, plus these non-Cf ones:
# combining grapheme joiner, variation selectors, Mongolian FVS, Hangul fillers.
_INVISIBLE_EXTRA = re.compile(
    "[\u034f\u115f\u1160\u180b-\u180d\u3164\ufe00-\ufe0f\uffa0\U000e0100-\U000e01ef]"
)
_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)


def strip_invisible(text: str) -> str:
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return _INVISIBLE_EXTRA.sub("", text)


def sanitize_for_model(text: str) -> str:
    """Text actually sent to the driver and echoed in replies: drop only format /
    zero-width / bidi / tag / CGJ / variation-selector / Hangul-filler characters and
    HTML comments (hidden content). No NFKC, so zh-TW full-width punctuation stays."""
    return _HTML_COMMENT.sub("", strip_invisible(text))


_SPACES = re.compile(r"\s+")


def normalize_for_match(text: str) -> str:
    """Detection view for DLP, tripwires, the denylist and @-mention parsing:
    sanitize_for_model + NFKC + whitespace runs folded to one space."""
    text = unicodedata.normalize("NFKC", sanitize_for_model(text))
    return _SPACES.sub(" ", strip_invisible(text))


normalize = normalize_for_match      # backwards-compatible name (detection view)


def _fold(text: str) -> str:
    """Detection-only view: normalize_for_match + casefold."""
    return normalize_for_match(text).casefold()


# ── UNTRUSTED envelopes ──────────────────────────────────────────────
_BOUNDARY = re.compile(r"<<\s*/?\s*UNTRUSTED[^>]*>>", re.IGNORECASE)


def strip_envelopes(text: str) -> tuple[str, int]:
    """Remove forged envelope boundaries; returns (clean_text, n_removed). Full-width
    look-alikes (＜＜UNTRUSTED…＞＞) are counted via the match view so they still flag."""
    clean, n = _BOUNDARY.subn("", text)
    return clean, n or len(_BOUNDARY.findall(normalize_for_match(clean)))


def wrap_untrusted(text: str, source: str, nonce: str | None = None) -> str:
    """Wrap `text` as zero-authority content. `nonce` = 128-bit hex (random by default)."""
    nid = nonce or secrets.token_hex(16)
    clean, _ = strip_envelopes(text)
    src = re.sub(r"[^a-z0-9_-]", "", source.lower())[:24] or "unknown"
    return f"<<UNTRUSTED id={nid} source={src}>>\n{clean}\n<</UNTRUSTED id={nid}>>"


_FENCE = re.compile(r"```.*?(?:```|$)", re.DOTALL)


def split_untrusted(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Separate the author's own words from quoted (`>`) lines and code fences."""
    segments: list[tuple[str, str]] = []

    def _code(m: re.Match) -> str:
        segments.append(("code", m.group(0).strip("`").strip()))
        return ""

    text = _FENCE.sub(_code, text)
    authored, quote = [], []
    for line in text.splitlines():
        if line.lstrip().startswith(">"):
            quote.append(line.lstrip()[1:].strip())
        else:
            if quote:
                segments.append(("quote", "\n".join(quote)))
                quote = []
            authored.append(line)
    if quote:
        segments.append(("quote", "\n".join(quote)))
    return "\n".join(authored).strip(), segments


def build_user_text(text: str, nonce_fn: Callable[[], str] | None = None) -> tuple[str, int]:
    """Authored text + enveloped untrusted segments. Returns (user_text, n_untrusted)."""
    authored, segments = split_untrusted(text)
    parts = [authored] if authored else []
    for source, seg in segments:
        parts.append(wrap_untrusted(seg, source, nonce_fn() if nonce_fn else None))
    return "\n".join(parts), len(segments)


# ── injection tripwire ───────────────────────────────────────────────
TRIPWIRES: list[tuple[str, re.Pattern]] = [
    ("ignore-previous", re.compile(r"ignore\s+(?:all\s+)?(?:previous|above|prior)")),
    ("system-prompt", re.compile(r"system\s*prompt")),
    ("you-are-now", re.compile(r"you\s+are\s+now")),
    ("ignore-zh", re.compile(r"忽略(?:以上|先前|之前|上面)")),
    ("role-swap-zh", re.compile(r"你現在是")),
    ("secret-request", re.compile(
        r"(?:貼出|給我|提供|列出|告訴我|reveal|print|show|paste|send).{0,20}"
        r"(?:密碼|token|權杖|金鑰|圖紙|password|api\s*key|secret|drawing)")),
    ("delegation", re.compile(r"以後都(?:由)?你(?:來)?決定|from now on,? you decide")),
    ("claims-approval", re.compile(r"(?:已經?|已被)核准|already\s+approved")),
    ("impersonation", re.compile(r"我是.{0,6}(?:主管|董事長|廠長|經理)|i\s+am\s+the\s+(?:ceo|manager|boss)")),
    ("path-traversal", re.compile(r"(?:\.\./){2,}|/etc/passwd|~/\.ssh")),
]


def tripwire_hits(text: str) -> list[str]:
    folded = _fold(text)
    return [name for name, pat in TRIPWIRES if pat.search(folded)]


def tripwire(text: str) -> bool:
    return bool(tripwire_hits(text))


# ── DLP ──────────────────────────────────────────────────────────────
_WORD_MARKERS = frozenset({"confidential-zh", "restricted-zh", "defense-zh", "confidential-en", "restricted-en"})
_WS = re.compile(r"\s+")


def dlp_hits(text: str, extra: Iterable[tuple[str, re.Pattern]] = ()) -> list[tuple[str, str]]:
    """[(pattern_name, tier)] for every DLP hit. `extra` = local denylist (tier T2).

    Scans the normalized text; word markers and the denylist are also matched on a
    whitespace-free copy so "機 密" or "DWG- 123" still trip."""
    folded = normalize_for_match(text)
    squeezed = _WS.sub("", folded)
    hits = []
    for name, pat in DLP_PATTERNS:
        views = (folded, squeezed) if name in _WORD_MARKERS else (folded,)
        for view in views:
            m = next((m for m in pat.finditer(view) if name != "tw-ubn" or valid_ubn(m.group(0))), None)
            if m:
                hits.append((name, DLP_TIERS[name]))
                break
    hits.extend((name, "T2") for name, pat in extra if pat.search(folded) or pat.search(squeezed))
    return hits


def load_denylist(path: str | Path) -> list[tuple[str, re.Pattern]]:
    """Local denylist (`team/local/names.denylist`): one regex per line, `#` comments.
    Raises ValueError naming the line number only (never the line's content)."""
    pats: list[tuple[str, re.Pattern]] = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        try:
            pats.append((f"denylist:{n}", re.compile(unicodedata.normalize("NFKC", s))))
        except re.error:
            raise ValueError(f"denylist line {n}: bad regex") from None
    return pats


def dlp_tier(text: str, extra: Iterable[tuple[str, re.Pattern]] = ()) -> str | None:
    """Highest tier implied by DLP markers in `text`, or None."""
    tiers = [t for _, t in dlp_hits(text, extra)]
    return max(tiers, key=tier_rank) if tiers else None


# ── outbound filter (order fixed by §9.4) ───────────────────────────
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_SLACK_LINK = re.compile(r"<(?:https?|ftp|mailto):[^>|]*(?:\|([^>]*))?>", re.IGNORECASE)
_BARE_URL = re.compile(r"(?i)\b(?:https?|ftp|file)://[!-~]+|\bwww\.[!-~]+|\bdata:[a-z/+-]+;[!-~]+")
_MASS_MENTION = re.compile(r"@(everyone|here|channel)\b|<!(channel|here|everyone)[^>]*>|<@[^>]+>", re.IGNORECASE)
MAX_REPLY_CHARS = 3000


def filter_output(text: str, channel_tier: str,
                  extra: Iterable[tuple[str, re.Pattern]] = ()) -> tuple[str, dict]:
    """Strip URLs/images → neutralise mass mentions → mask secrets → tier block → cap length.
    `extra` = local denylist (tier T2), same as inbound DLP."""
    stats = {"urls": 0, "mentions": 0, "secret": 0, "blocked": None, "truncated": False}
    text, n1 = _MD_IMAGE.subn("[圖片已移除]", text)
    text, n2 = _MD_LINK.subn(lambda m: m.group(1), text)
    text, n3 = _SLACK_LINK.subn(lambda m: m.group(1) or "[連結已移除]", text)
    text, n4 = _BARE_URL.subn("[連結已移除]", text)
    stats["urls"] = n1 + n2 + n3 + n4
    text, stats["mentions"] = _MASS_MENTION.subn(
        lambda m: "＠" + (m.group(1) or m.group(2) or "mention"), text)
    for name, pat in [*SECRET_PATTERNS, GENERIC_SECRET]:
        text, n = pat.subn(f"[REDACTED:{name}]", text)
        stats["secret"] += n
    tier = dlp_tier(text, extra)
    if tier and tier_rank(tier) > tier_rank(channel_tier):
        stats["blocked"] = tier
    if len(text) > MAX_REPLY_CHARS:
        text = text[: MAX_REPLY_CHARS - 1] + "…"
        stats["truncated"] = True
    return text, stats
