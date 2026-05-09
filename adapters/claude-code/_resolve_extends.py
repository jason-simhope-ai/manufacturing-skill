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


def parse_file(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict):
        raise ValueError(
            f"{path}: frontmatter must be a YAML mapping (got "
            f"{type(fm).__name__})"
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


# ---------- code-region stripping (M1) ----------

FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def strip_code_regions(body: str) -> str:
    """Replace fenced + inline code with placeholders preserving line counts.

    Used only for directive scanning — the original body is preserved for
    verbatim emission of code examples (so docs that demonstrate
    inheritance syntax don't get their examples processed).
    """
    def _placeholder(m):
        return "\n" * m.group(0).count("\n")
    out = FENCED_CODE_RE.sub(_placeholder, body)
    out = INLINE_CODE_RE.sub("", out)
    return out


# ---------- directive scanning ----------

INHERIT_RE = re.compile(r"<!--\s*inherit\s*-->")
OVERRIDE_BODY_RE = re.compile(r"<!--\s*override-body\s*-->")
REPLACE_SECTION_RE = re.compile(
    r"<!--\s*replace-section:\s*(.+?)\s*-->"
)


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s.strip())


@dataclasses.dataclass
class ParsedDirectives:
    mode: str  # "inherit" | "override-body"
    inherit_count: int
    replace_sections: dict[str, str]  # nfkc(heading) -> replacement_text
    raw_replace_keys: dict[str, str]  # nfkc -> original heading (for errors)


def parse_directives(body: str) -> ParsedDirectives:
    """Scan the (code-stripped) body for mode + replace-section directives.

    Returns a ParsedDirectives or raises ValueError on structural errors
    (multiple modes, no mode, etc.).
    """
    stripped = strip_code_regions(body)
    inherit_count = len(INHERIT_RE.findall(stripped))
    override_count = len(OVERRIDE_BODY_RE.findall(stripped))

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
    # to the next `## ` heading or directive (whichever comes first).
    replace_sections: dict[str, str] = {}
    raw_keys: dict[str, str] = {}
    matches = list(REPLACE_SECTION_RE.finditer(stripped))
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        key = nfkc(heading)
        # Block ends at next directive or `## ` heading, whichever first
        block_start = m.end()
        block_end = len(stripped)
        # Find next `## ` heading (line-anchored) after block_start
        for line_match in re.finditer(r"^## .*$", stripped[block_start:],
                                       re.MULTILINE):
            block_end = block_start + line_match.start()
            break
        # Or next replace-section / inherit / override-body directive
        for next_m in matches[i + 1:]:
            if next_m.start() < block_end:
                block_end = next_m.start()
            break
        for r in (INHERIT_RE, OVERRIDE_BODY_RE):
            nm = r.search(stripped, block_start)
            if nm and nm.start() < block_end:
                block_end = nm.start()
        # Use the original (un-stripped) body to grab content with code
        # examples intact.
        block = body[block_start:block_end].strip()
        if key in replace_sections:
            raise ValueError(
                f"replace-section heading {heading!r} declared twice"
            )
        replace_sections[key] = block
        raw_keys[key] = heading

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
    `## ` heading or EOF.
    """
    spans: dict[str, tuple[int, int, str]] = {}
    matches = list(H2_RE.finditer(core_body))
    for i, m in enumerate(matches):
        heading_raw = m.group(1).strip()
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
    """
    if directives.mode == "override-body":
        return OVERRIDE_BODY_RE.sub("", profile_body).lstrip("\n")

    # Build a list of (start, end, replacement) edits to apply to
    # profile_body. Sources of edits:
    #   - <!-- inherit --> directive → replaced with modified_core_body
    #   - each <!-- replace-section: X --> + captured block → removed
    edits: list[tuple[int, int, str]] = []

    # Inherit marker
    inherit_match = INHERIT_RE.search(strip_code_regions(profile_body))
    if inherit_match:
        # Use stripped position but body indices align (placeholders preserve newlines but inline code is dropped — search original instead)
        m = INHERIT_RE.search(profile_body)
        if m is None:
            # The directive was inside code-stripped region but not the
            # raw body — that means it WAS in a code block, ignore.
            raise ValueError(
                "inherit marker disappeared after code-strip; this "
                "shouldn't happen — please file a bug"
            )
        edits.append((m.start(), m.end(), modified_core_body.strip("\n")))

    # Replace-section blocks (skip them entirely)
    matches = list(REPLACE_SECTION_RE.finditer(profile_body))
    for i, m in enumerate(matches):
        block_start = m.start()
        block_end = len(profile_body)
        for line_match in re.finditer(r"^## .*$",
                                       profile_body[m.end():], re.MULTILINE):
            block_end = m.end() + line_match.start()
            break
        for next_m in matches[i + 1:]:
            if next_m.start() < block_end:
                block_end = next_m.start()
            break
        for r in (INHERIT_RE, OVERRIDE_BODY_RE):
            nm = r.search(profile_body, m.end())
            if nm and nm.start() < block_end:
                block_end = nm.start()
        edits.append((block_start, block_end, ""))

    # Apply edits in order
    edits.sort(key=lambda e: e[0])
    out = []
    cursor = 0
    for start, end, repl in edits:
        out.append(profile_body[cursor:start])
        out.append(repl)
        cursor = end
    out.append(profile_body[cursor:])
    return "".join(out)


# ---------- top-level resolve ----------

@dataclasses.dataclass
class ResolveResult:
    frontmatter: dict
    body: str
    text: str  # full file output
    core_path: Path


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

    extends_path = fm["extends"]
    if extends_path.endswith(".md"):
        extends_path = extends_path[:-3]
    core_path = repo_root / f"{extends_path}.md"
    if not core_path.is_file():
        raise ValueError(
            f"{rel}: extends points to {extends_path}.md but no such "
            f"file exists in the repo"
        )
    if not str(core_path.resolve()).startswith(str(repo_root / "core")):
        raise ValueError(
            f"{rel}: extends must point at a core/ file, got "
            f"{extends_path}"
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
        for m in REPLACE_SECTION_RE.finditer(body):
            heading = m.group(1).strip()
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
        Path(args.out).write_text(result.text, encoding="utf-8")
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
