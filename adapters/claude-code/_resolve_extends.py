#!/usr/bin/env python3
"""Profile inheritance resolver.

Reads a profile markdown file with `extends:` in frontmatter, merges it
against the referenced core file, and writes (or prints) the resolved
output. Also exposes lint mode used by CI.

Spec: docs/superpowers/specs/2026-05-08-profile-inheritance-design.md
"""
from __future__ import annotations

import argparse
import dataclasses
import posixpath
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml",
          file=sys.stderr)
    sys.exit(2)


class _IndentedDumper(yaml.Dumper):
    """Force sequence items to be indented under their parent key.

    PyYAML's default emits:
        tools:
        - Read
    Prettier and most markdown formatters expect:
        tools:
          - Read
    Aligning here avoids a tug-of-war between the resolver and the
    formatter that runs on test fixtures.
    """
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# ---------- frontmatter parsing ----------

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


def _oneline(msg: object) -> str:
    return " ".join(str(msg).split())


def parse_file(path: Path) -> tuple[dict, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"{path}: cannot read file ({_oneline(e)})")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValueError(
            f"{path}: frontmatter is not valid YAML ({_oneline(e)})"
        )
    if not isinstance(fm, dict):
        raise ValueError(
            f"{path}: frontmatter must be a YAML mapping (got "
            f"{type(fm).__name__})"
        )
    bad_keys = [k for k in fm if not isinstance(k, str)]
    if bad_keys:
        raise ValueError(
            f"{path}: frontmatter keys must be strings (got "
            f"{bad_keys[0]!r})"
        )
    body = text[m.end():]
    return fm, body


def emit_file(fm: dict, body: str) -> str:
    fm_clean = {k: v for k, v in fm.items()
                if not k.startswith("extends") and not k.endswith("-replace")}
    fm_yaml = yaml.dump(
        fm_clean, allow_unicode=True, sort_keys=False,
        default_flow_style=False, Dumper=_IndentedDumper,
    ).rstrip()
    body_clean = body.strip("\n")
    return f"---\n{fm_yaml}\n---\n\n{body_clean}\n"


# ---------- frontmatter merge (H1 — per-field rules) ----------

def merge_frontmatter(core: dict, profile: dict) -> dict:
    """Merge core + profile frontmatter per spec §6.4.

    - Scalar fields: profile wins on conflict, core fills gap.
    - List fields: union (deduplicated, preserving order: core first, then
      profile entries not in core).
    - Dict fields: deep merge with same rules.
    - Opt-out: `<field>-replace: true` in profile forces replacement
      semantics for that single field.
    """
    out = dict(core)
    for key, prof_value in profile.items():
        if key.endswith("-replace") or key == "extends":
            continue
        replace_flag = profile.get(f"{key}-replace") is True
        if key not in out:
            out[key] = prof_value
            continue
        core_value = out[key]
        if isinstance(prof_value, list) and isinstance(core_value, list):
            if replace_flag:
                out[key] = list(prof_value)
            else:
                seen = []
                for v in core_value + prof_value:
                    if v not in seen:
                        seen.append(v)
                out[key] = seen
        elif isinstance(prof_value, dict) and isinstance(core_value, dict):
            out[key] = merge_frontmatter(core_value, prof_value)
        else:
            out[key] = prof_value
    return out


# ---------- code-region masking (M1) ----------
#
# Directives and `## ` headings inside code are documentation, not
# structure. Every scanner below works on a *masked* copy of the text in
# which code is replaced by spaces of equal length (newlines kept), so a
# match offset in the masked copy is the same offset in the raw text.
# One scan therefore drives both validation (parse_directives) and
# emission (assemble_profile_body).

_FENCE_OPEN_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _blank(s: str) -> str:
    return "".join("\n" if c == "\n" else " " for c in s)


def mask_fences(text: str) -> str:
    """Blank out fenced code blocks (``` or ~~~), keeping offsets.

    A fence closes on a line of the same character, at least as long as
    the opener, with nothing else on it. An unclosed fence runs to EOF
    (CommonMark behaviour).
    """
    lines = text.split("\n")
    out: list[str] = []
    fence_char = ""
    fence_len = 0
    for line in lines:
        bare = line.rstrip("\r")
        if fence_char:
            out.append(_blank(line))
            m = _FENCE_CLOSE_RE.match(bare)
            if m and m.group(1)[0] == fence_char \
                    and len(m.group(1)) >= fence_len:
                fence_char = ""
            continue
        m = _FENCE_OPEN_RE.match(bare)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence_char = m.group(1)[0]
            fence_len = len(m.group(1))
            out.append(_blank(line))
            continue
        out.append(line)
    return "\n".join(out)


def mask_code(text: str) -> str:
    """Blank out fenced and inline code, keeping offsets."""
    masked = mask_fences(text)
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), masked)


def strip_code_regions(body: str) -> str:
    """Backward-compatible alias for :func:`mask_code`."""
    return mask_code(body)


# ---------- directive scanning ----------

INHERIT_RE = re.compile(r"<!--\s*inherit\s*-->")
OVERRIDE_BODY_RE = re.compile(r"<!--\s*override-body\s*-->")
REPLACE_SECTION_RE = re.compile(
    r"<!--\s*replace-section:\s*(.+?)\s*-->"
)
H2_LINE_RE = re.compile(r"^## .*$", re.MULTILINE)


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s.strip())


@dataclasses.dataclass
class _Directive:
    kind: str      # "inherit" | "override-body" | "replace-section"
    start: int     # offsets into the RAW body
    end: int
    heading: str = ""            # replace-section only
    block_end: int = 0           # replace-section only: end of its block


def scan_body(body: str) -> list[_Directive]:
    """Find every real (non-code) directive, in document order.

    For replace-section, `block_end` is where its captured block stops:
    the next real `## ` heading or the next real directive, whichever
    comes first.
    """
    masked = mask_code(body)
    fence_masked = mask_fences(body)
    found: list[_Directive] = []
    for m in INHERIT_RE.finditer(masked):
        found.append(_Directive("inherit", m.start(), m.end()))
    for m in OVERRIDE_BODY_RE.finditer(masked):
        found.append(_Directive("override-body", m.start(), m.end()))
    for m in REPLACE_SECTION_RE.finditer(masked):
        found.append(_Directive(
            "replace-section", m.start(), m.end(),
            heading=body[m.start(1):m.end(1)].strip(),
        ))
    found.sort(key=lambda d: d.start)
    for i, d in enumerate(found):
        if d.kind != "replace-section":
            continue
        block_end = len(body)
        h = H2_LINE_RE.search(fence_masked, d.end)
        if h:
            block_end = h.start()
        for nd in found[i + 1:]:
            if nd.start >= d.end:
                block_end = min(block_end, nd.start)
                break
        d.block_end = block_end
    return found


@dataclasses.dataclass
class ParsedDirectives:
    mode: str  # "inherit" | "override-body"
    inherit_count: int
    replace_sections: dict[str, str]  # nfkc(heading) -> replacement_text
    raw_replace_keys: dict[str, str]  # nfkc -> original heading (for errors)


def parse_directives(body: str) -> ParsedDirectives:
    """Scan the body for mode + replace-section directives.

    Directives inside fenced or inline code are ignored. Returns a
    ParsedDirectives or raises ValueError on structural errors
    (multiple modes, no mode, etc.).
    """
    directives = scan_body(body)
    inherit_count = sum(1 for d in directives if d.kind == "inherit")
    override_count = sum(1 for d in directives
                         if d.kind == "override-body")

    if inherit_count > 0 and override_count > 0:
        raise ValueError(
            "both `<!-- inherit -->` and `<!-- override-body -->` "
            "present — pick exactly one"
        )
    if inherit_count == 0 and override_count == 0:
        raise ValueError(
            "extends: declared but no mode marker found. Add either "
            "`<!-- inherit -->` (to inherit core body) or "
            "`<!-- override-body -->` (to discard core body)"
        )
    if inherit_count > 1:
        raise ValueError(
            f"`<!-- inherit -->` may appear at most once "
            f"(found {inherit_count})"
        )
    if override_count > 1:
        raise ValueError(
            f"`<!-- override-body -->` may appear at most once "
            f"(found {override_count})"
        )

    mode = "inherit" if inherit_count == 1 else "override-body"

    # Collect replace-section blocks. Each block runs from its directive
    # to the next real `## ` heading or directive (whichever comes first).
    # The block text comes from the raw body so code examples stay intact.
    replace_sections: dict[str, str] = {}
    raw_keys: dict[str, str] = {}
    for d in directives:
        if d.kind != "replace-section":
            continue
        key = nfkc(d.heading)
        block = body[d.end:d.block_end].strip()
        if key in replace_sections:
            raise ValueError(
                f"replace-section heading {d.heading!r} declared twice"
            )
        replace_sections[key] = block
        raw_keys[key] = d.heading

    return ParsedDirectives(
        mode=mode,
        inherit_count=inherit_count,
        replace_sections=replace_sections,
        raw_replace_keys=raw_keys,
    )


# ---------- core body section operations ----------

H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def find_section_spans(core_body: str) -> dict[str, tuple[int, int, str]]:
    """Map nfkc(heading) -> (start_offset, end_offset, raw_heading).

    A section runs from its `## Heading` line to (exclusive) the next
    `## ` heading or EOF. Headings inside fenced code blocks are ignored.
    """
    spans: dict[str, tuple[int, int, str]] = {}
    # `## ` lines inside fenced code are not headings.
    matches = list(H2_RE.finditer(mask_fences(core_body)))
    for i, m in enumerate(matches):
        heading_raw = core_body[m.start(1):m.end(1)].strip()
        key = nfkc(heading_raw)
        if key in spans:
            raise ValueError(
                f"core body has duplicate `## {heading_raw}` heading — "
                f"section replacement would be ambiguous"
            )
        end = matches[i + 1].start() if i + 1 < len(matches) \
            else len(core_body)
        spans[key] = (m.start(), end, heading_raw)
    return spans


def apply_section_replacements(
    core_body: str,
    replacements: dict[str, str],
    raw_keys: dict[str, str],
) -> str:
    """Return core_body with each `## X` section replaced.

    Replacement content already includes the `## X` line if the author
    wrote one; otherwise we emit `## X\\n\\n<replacement>` to preserve
    the heading.
    """
    spans = find_section_spans(core_body)
    out = []
    cursor = 0
    sorted_replacements = sorted(
        replacements.items(),
        key=lambda kv: spans[kv[0]][0] if kv[0] in spans else -1,
    )
    seen = set()
    for key, replacement in sorted_replacements:
        if key not in spans:
            raise ValueError(
                f"replace-section: {raw_keys[key]!r} — no matching "
                f"`## {raw_keys[key]}` in core body"
            )
        start, end, heading_raw = spans[key]
        out.append(core_body[cursor:start])
        if replacement.lstrip().startswith("## "):
            out.append(replacement.rstrip() + "\n\n")
        else:
            out.append(f"## {heading_raw}\n\n{replacement.rstrip()}\n\n")
        cursor = end
        seen.add(key)
    unused = set(replacements.keys()) - seen
    if unused:
        raise ValueError(
            f"replace-section directives never applied: "
            f"{sorted(raw_keys[k] for k in unused)}"
        )
    out.append(core_body[cursor:])
    return "".join(out)


# ---------- profile body assembly ----------

def assemble_profile_body(
    profile_body: str,
    modified_core_body: str,
    directives: ParsedDirectives,
) -> str:
    """Walk profile body, emitting verbatim text + substituted core body.

    `replace-section` directives + their captured blocks are skipped.
    `<!-- inherit -->` is replaced by the modified core body.
    `<!-- override-body -->` is stripped (its presence is the signal).

    Uses the same scan as parse_directives, so directive-looking text in
    code blocks is emitted verbatim and never edited.
    """
    found = scan_body(profile_body)

    if directives.mode == "override-body":
        edits = [(d.start, d.end, "") for d in found
                 if d.kind == "override-body"]
        return _apply_edits(profile_body, edits).lstrip("\n")

    edits: list[tuple[int, int, str]] = []
    for d in found:
        if d.kind == "inherit":
            edits.append((d.start, d.end, modified_core_body.strip("\n")))
        elif d.kind == "replace-section":
            edits.append((d.start, d.block_end, ""))
    return _apply_edits(profile_body, edits)


def _apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    out = []
    cursor = 0
    for start, end, repl in sorted(edits, key=lambda e: e[0]):
        out.append(text[cursor:start])
        out.append(repl)
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


# ---------- top-level resolve ----------

@dataclasses.dataclass
class ResolveResult:
    frontmatter: dict
    body: str
    text: str  # full file output
    core_path: Path


def _describe(value: object) -> str:
    return f"{type(value).__name__} {value!r}"[:80]


def resolve_profile_file(
    profile_path: Path,
    repo_root: Path,
) -> ResolveResult:
    """Top-level: parse profile, locate core, merge, return result.

    Raises ValueError on any spec-defined failure mode.
    """
    profile_path = profile_path.resolve()
    repo_root = repo_root.resolve()
    rel = profile_path.relative_to(repo_root)
    parts = rel.parts
    if len(parts) < 4 or parts[0] != "profiles":
        raise ValueError(
            f"profile file must live under profiles/<name>/<kind>/, "
            f"got {rel}"
        )
    kind = parts[2]  # agents | skills | know-how | hooks | commands
    if kind == "commands":
        raise ValueError(
            f"`extends:` is not allowed for commands (Q3 / spec §10.1). "
            f"Found in {rel}. Add a new command with a different name "
            f"instead of inheriting."
        )

    fm, body = parse_file(profile_path)
    if "extends" not in fm:
        raise ValueError(
            f"{rel}: no `extends:` field — cannot resolve. Use plain "
            f"override (no extends) for full replacement."
        )

    extends_raw = fm["extends"]
    if not isinstance(extends_raw, str) or not extends_raw.strip():
        raise ValueError(
            f"{rel}: `extends:` must be a non-empty string path like "
            f"core/agents/<name>, got {_describe(extends_raw)}"
        )
    extends_path = extends_raw.strip()
    if extends_path.endswith(".md"):
        extends_path = extends_path[:-3]
    # Normalise and check path components BEFORE touching the filesystem:
    # a textual prefix test would let `core-evil/...` through.
    norm = posixpath.normpath(extends_path.replace("\\", "/"))
    norm_parts = norm.split("/")
    if (norm.startswith("/") or len(norm_parts) < 2
            or norm_parts[0] != "core" or ".." in norm_parts):
        raise ValueError(
            f"{rel}: extends must point at a core/ file, got "
            f"{extends_raw!r}"
        )
    core_root = (repo_root / "core").resolve()
    core_path = repo_root / f"{norm}.md"
    if core_root not in core_path.resolve().parents:
        raise ValueError(
            f"{rel}: extends must point at a core/ file, got "
            f"{extends_raw!r}"
        )
    if not core_path.is_file():
        raise ValueError(
            f"{rel}: extends points to {extends_path}.md but no such "
            f"file exists in the repo"
        )

    core_fm, core_body = parse_file(core_path)
    merged_fm = merge_frontmatter(core_fm, fm)
    directives = parse_directives(body)

    # Validate replace-section keys are in core
    if directives.replace_sections:
        try:
            core_spans = find_section_spans(core_body)
        except ValueError as e:
            raise ValueError(
                f"{rel}: {e} (declared in extended file {extends_path})"
            )
        for key, raw in directives.raw_replace_keys.items():
            if key not in core_spans:
                raise ValueError(
                    f"{rel}: replace-section: {raw!r} — no matching "
                    f"`## {raw}` heading in core file {extends_path}"
                )

    if directives.mode == "inherit":
        modified_core = apply_section_replacements(
            core_body,
            directives.replace_sections,
            directives.raw_replace_keys,
        )
        assembled = assemble_profile_body(body, modified_core, directives)
    else:
        if directives.replace_sections:
            print(
                f"WARN: {rel}: replace-section directives are ignored "
                f"in override-body mode",
                file=sys.stderr,
            )
        assembled = assemble_profile_body(body, "", directives)

    text = emit_file(merged_fm, assembled)
    return ResolveResult(
        frontmatter=merged_fm,
        body=assembled,
        text=text,
        core_path=core_path.relative_to(repo_root),
    )


# ---------- core-side anchor protection (Step 10b / H2) ----------

def find_referencing_profiles(
    repo_root: Path,
    core_rel: Path,
    removed_headings: list[str],
) -> list[tuple[Path, str]]:
    """Return [(profile_path, heading)] of profiles whose
    replace-section references the given removed headings.
    """
    parts = core_rel.parts
    if len(parts) < 3 or parts[0] != "core":
        return []
    kind = parts[1]
    basename = Path(parts[2]).stem
    extends_target = f"core/{kind}/{basename}"
    out: list[tuple[Path, str]] = []
    nfkc_removed = [nfkc(h) for h in removed_headings]
    for pj in (repo_root / "profiles").glob(f"*/{kind}/*.md"):
        try:
            fm, body = parse_file(pj)
        except ValueError:
            continue
        if fm.get("extends") not in (extends_target, f"{extends_target}.md"):
            continue
        for d in scan_body(body):
            if d.kind != "replace-section":
                continue
            heading = d.heading
            if nfkc(heading) in nfkc_removed:
                out.append((pj.relative_to(repo_root), heading))
    return out


# ---------- CLI ----------

def cmd_resolve(args) -> int:
    profile_path = Path(args.profile_file)
    repo_root = Path(args.repo_root or ".")
    try:
        result = resolve_profile_file(profile_path, repo_root)
    except ValueError as e:
        print(f"::error file={profile_path}::{e}", file=sys.stderr)
        return 1
    if args.out:
        try:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result.text, encoding="utf-8")
        except OSError as e:
            print(f"::error file={profile_path}::cannot write --out "
                  f"{args.out}: {_oneline(e)}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(result.text)
    return 0


def cmd_lint(args) -> int:
    profile_path = Path(args.profile_file)
    repo_root = Path(args.repo_root or ".")
    try:
        resolve_profile_file(profile_path, repo_root)
    except ValueError as e:
        print(f"::error file={profile_path}::{e}", file=sys.stderr)
        return 1
    print(f"ok  {profile_path}")
    return 0


def cmd_lint_anchors(args) -> int:
    repo_root = Path(args.repo_root or ".")
    core_rel = Path(args.core_file)
    headings = args.removed_heading
    fail = False
    refs = find_referencing_profiles(repo_root, core_rel, headings)
    for profile_path, heading in refs:
        print(
            f"::error file={profile_path}::removed/renamed core heading "
            f"`## {heading}` is still referenced by this profile via "
            f"`<!-- replace-section: {heading} -->`. Update the profile "
            f"in this PR or restore the heading.",
            file=sys.stderr,
        )
        fail = True
    if not refs:
        print(f"ok  no profiles reference removed headings of {core_rel}")
    return 1 if fail else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile inheritance resolver"
    )
    parser.add_argument(
        "--repo-root", help="repo root (default: current directory)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_resolve = sub.add_parser(
        "resolve", help="merge profile + core, write or print result"
    )
    p_resolve.add_argument("profile_file")
    p_resolve.add_argument("--out", help="output path (default: stdout)")
    p_resolve.set_defaults(func=cmd_resolve)

    p_lint = sub.add_parser(
        "lint", help="validate without writing (for CI)"
    )
    p_lint.add_argument("profile_file")
    p_lint.set_defaults(func=cmd_lint)

    p_anchors = sub.add_parser(
        "lint-anchors",
        help="check no profile references a removed core heading"
    )
    p_anchors.add_argument("core_file")
    p_anchors.add_argument("removed_heading", nargs="+")
    p_anchors.set_defaults(func=cmd_lint_anchors)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
