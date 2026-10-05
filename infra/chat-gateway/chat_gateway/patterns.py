"""Single source of truth for secret / name / DLP regexes (§11.1, §11.4).

Used by the gateway (inbound DLP, outbound masking, config scanning) and by
`team/tools/teamctl.py` (repo hygiene). Every list is `list[tuple[name, re.Pattern]]`.

Some literals are built by concatenation so this file never matches its own
patterns when a scanner reads it.
"""
from __future__ import annotations

import re

_P = re.compile

SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("slack-token", _P(r"xox[abprs]-[0-9A-Za-z-]{10,}")),
    ("slack-app-token", _P(r"xapp-\d-[A-Z0-9]+-\d+-[a-f0-9]{20,}")),
    ("slack-webhook", _P(r"https://hooks\.slack\.com/services/\S+")),
    ("discord-token", _P(r"[MNO][A-Za-z\d_-]{23,27}\.[\w-]{6}\.[\w-]{27,}")),
    ("discord-webhook", _P(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\S+")),
    ("anthropic-key", _P(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("github-token", _P(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("aws-key-id", _P(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private-key", _P("-----" + r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY" + "-----")),
]

# Generic `secret=...` assignment; teamctl applies it only to team/** and
# infra/chat-gateway/**, the gateway applies it to its own output.
GENERIC_SECRET: tuple[str, re.Pattern] = (
    "generic-assignment",
    _P(r"(?i)\b(?:secret|token|password|passwd|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+]{8,}"),
)

_SURNAMES = ("陳林黃張李王吳劉蔡楊許鄭謝郭洪曾邱廖賴周徐蘇葉莊呂江何蕭羅高簡朱鍾施游詹沈彭胡余盧潘顏梁趙柯翁魏方孫戴范宋")
_TITLES = "廠長|經理|協理|課長|組長|副總|總經理|董事長|處長|特助|主任|先生|小姐|主管"

NAME_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Surname immediately followed by a title ("X廠長"); previous char must not be CJK.
    ("surname-title", _P(r"(?<![一-鿿])[" + _SURNAMES + r"](?:" + _TITLES + r")")),
    ("en-honorific", _P(r"\b(?:Mr|Ms|Mrs|Dr)\.\s?[A-Z][a-z]+")),
    ("email", _P(r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|test)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("tw-mobile", _P(r"09\d{2}-?\d{3}-?\d{3}")),
    ("slack-id", _P(r"\b[UWCGT][A-Z0-9]{8,}\b")),
    ("discord-id", _P(r"\b\d{17,20}\b")),
]

# DLP tripwire (alert, not a defence). Tier of each pattern lives in DLP_TIERS.
DLP_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("confidential-zh", _P(r"機密")),
    ("confidential-en", _P(r"(?i)(?<![a-z])confidential(?![a-z])")),
    ("restricted-en", _P(r"(?i)(?<![a-z])restricted(?![a-z])")),
    ("restricted-zh", _P(r"受限")),
    ("defense-zh", _P(r"國防")),
    ("tw-ubn", _P(r"(?<!\d)\d{8}(?!\d)")),          # 統一編號; checksum in valid_ubn()
    ("tw-national-id", _P(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?!\d)")),
    ("amount-ntd", _P(r"NT\$\s?[\d,]{4,}")),
]
DLP_TIERS: dict[str, str] = {
    "confidential-zh": "T2", "confidential-en": "T2", "tw-ubn": "T2",
    "tw-national-id": "T2", "amount-ntd": "T2",
    "restricted-en": "T3", "restricted-zh": "T3", "defense-zh": "T3",
}


def valid_ubn(digits: str) -> bool:
    """Taiwan unified business number checksum (weights 12121241, mod 5)."""
    if len(digits) != 8 or not digits.isdigit():
        return False
    weights = (1, 2, 1, 2, 1, 2, 4, 1)
    total = 0
    for d, w in zip(digits, weights):
        p = int(d) * w
        total += p // 10 + p % 10
    if total % 5 == 0:
        return True
    return digits[6] == "7" and (total + 1) % 5 == 0


def find_secrets(text: str) -> list[str]:
    """Names of SECRET_PATTERNS that match `text` (no generic rule)."""
    return [name for name, pat in SECRET_PATTERNS if pat.search(text)]
