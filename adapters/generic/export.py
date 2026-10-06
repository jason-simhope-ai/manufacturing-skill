#!/usr/bin/env python3
"""Generic adapter — export manufacturing-skill as plain markdown.

Produces the same merged content that `adapters/claude-code/install.sh`
would install (core layer + profile overlay, `extends:` resolved), but
as platform-neutral markdown for any other LLM agent: a Cursor rules
folder, Gemini CLI / Codex context files, an on-prem Ollama system
prompt, or a printout.

Usage:
    python3 adapters/generic/export.py --profiles cnc-machining --out DIR
    python3 adapters/generic/export.py --profiles cnc-machining,injection-molding \
        --out DIR --format bundle
    python3 adapters/generic/export.py --core-only --out DIR \
        --include agents,skills --reproducible

Formats:
    files   (default) DIR/{agents,skills,know-how,hooks,commands}/*.md
            plus DIR/MANIFEST.json (sources, versions, sha256 per file).
    bundle  DIR/manufacturing-skill.<profiles>.md — one self-contained
            markdown file with a preamble and table of contents.

Overlay and `extends:` semantics are NOT reimplemented here: conflict
detection uses `_multiprofile.scan_set` and inheritance uses
`_resolve_extends.resolve_profile_file` from adapters/claude-code/.
PyYAML is only required when a profile file uses `extends:` (same as
install.sh); without it, frontmatter tables in the bundle fall back to
a simple `key: value` reader.

Exit codes: 0 ok · 1 export error (one line on stderr) · 2 usage error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = HERE.parents[1]
CLAUDE_ADAPTER_DIR = DEFAULT_REPO_ROOT / "adapters" / "claude-code"
sys.path.insert(0, str(CLAUDE_ADAPTER_DIR))

import _multiprofile  # noqa: E402  (stdlib-only helper)

GENERATOR = "adapters/generic/export.py"
SCHEMA = 1

# Canonical kind order (also the order of sections in the bundle).
KINDS = ("agents", "skills", "know-how", "hooks", "commands")
# Kinds a profile may overlay — mirrors install.sh Stage 2 (commands are
# core-only; `extends:` on commands is rejected by the resolver anyway).
PROFILE_OVERLAY_KINDS = ("agents", "skills", "know-how", "hooks")

KIND_TITLES = {
    "agents": "Agents（角色）",
    "skills": "Skills（流程技能）",
    "know-how": "Know-how（領域知識）",
    "hooks": "Hooks（檢查點，僅文件）",
    "commands": "Playbooks（原 slash commands）",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
EXTENDS_LINE_RE = re.compile(r"^extends:\s", re.MULTILINE)


class ExportError(Exception):
    """A user-facing, one-line export failure."""


@dataclass
class ExportedFile:
    kind: str
    name: str          # basename incl. .md
    text: str          # final content as written
    origin: str        # "core" | "profile" | "profile+extends"
    profile: str | None
    source: str        # repo-relative source path
    extends: str | None = None

    @property
    def path(self) -> str:
        return f"{self.kind}/{self.name}"


# ---------- small helpers ----------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _has_extends(text: str) -> bool:
    m = FRONTMATTER_RE.match(text)
    return bool(m and EXTENDS_LINE_RE.search(m.group(1)))


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def _parse_frontmatter(raw: str) -> list[tuple[str, object]]:
    """Return ordered (key, value) pairs. Uses PyYAML if present,
    otherwise a minimal top-level `key: value` reader."""
    if importlib.util.find_spec("yaml") is not None:
        import yaml
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError:
            data = None
        if isinstance(data, dict):
            return list(data.items())
    pairs: list[tuple[str, object]] = []
    for line in raw.splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        pairs.append((k.strip(), _scalar(v.strip())))
    return pairs


def _scalar(v: str) -> object:
    """Best-effort YAML scalar / flow-list reading for the no-PyYAML path."""
    if v.startswith("[") and v.endswith("]"):
        return [_scalar(x.strip()) for x in v[1:-1].split(",") if x.strip()]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolver():
    """Import _resolve_extends lazily: it exits at import time without
    PyYAML, and most exports never need it."""
    if importlib.util.find_spec("yaml") is None:
        raise ExportError(
            "PyYAML is required to resolve `extends:` profile files — "
            "run: python3 -m pip install pyyaml"
        )
    import _resolve_extends
    return _resolve_extends


def _md_cell(value: object) -> str:
    if isinstance(value, (list, tuple)):
        s = ", ".join(str(v) for v in value)
    elif isinstance(value, dict):
        s = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif value is None:
        s = ""
    else:
        s = str(value)
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _anchor(kind: str, name: str) -> str:
    stem = name[:-3] if name.endswith(".md") else name
    slug = re.sub(r"[^\w\-]+", "-", stem, flags=re.UNICODE).strip("-").lower()
    return f"{kind}--{slug}"


# ---------- notes injected for non-Claude agents ----------

def _command_note(name: str) -> str:
    cmd = name[:-3]
    return (
        f"> **Playbook** — 原為 Claude Code slash command `/{cmd}`；"
        f"`/{cmd}` 這種語法只在 Claude Code 有效。在其他 agent 中，"
        f"請直接說「依照 {cmd} playbook 執行」並附上參數。\n"
        f">\n"
        f"> Originally the Claude Code slash command `/{cmd}`. The `/name` "
        f"syntax is Claude Code specific — elsewhere, ask the agent to "
        f"\"follow the {cmd} playbook\" with the same arguments.\n"
    )


HOOK_NOTE = (
    "> **Documentation only** — 這是流程檢查點說明，不會自動執行。"
    "請在 frontmatter `trigger` 所述時機由 agent 或人工自行套用。\n"
    ">\n"
    "> This hook is a checklist, not an executable hook. Apply it "
    "manually (or instruct the agent to) at the moment named in "
    "`trigger`.\n"
)


def _inject_note(text: str, note: str) -> str:
    raw, body = _split_frontmatter(text)
    body = body.lstrip("\n")
    if raw is None:
        return f"{note}\n{body}"
    return f"---\n{raw}\n---\n\n{note}\n{body}"


# ---------- collect (core + overlay + extends) ----------

def parse_profiles(raw: str) -> list[str]:
    """Comma list → ordered, de-duplicated names (install.sh semantics)."""
    out: list[str] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if entry in out:
            print(f"WARN: duplicate profile '{entry}' in argument list, "
                  f"ignoring", file=sys.stderr)
            continue
        out.append(entry)
    return out


def validate_profiles(repo_root: Path, profiles: list[str]) -> None:
    for name in profiles:
        if not (repo_root / "profiles" / name / "profile.json").is_file():
            raise ExportError(
                f"unknown profile {name!r} (no profiles/{name}/profile.json)"
            )
    if len(profiles) > 1:
        conflicts = _multiprofile.scan_set(repo_root, profiles)
        if conflicts:
            detail = "; ".join(c.render() for c in conflicts)
            raise ExportError(f"profile conflict — {detail}")


def collect(repo_root: Path, profiles: list[str],
            include: list[str]) -> list[ExportedFile]:
    files: dict[str, ExportedFile] = {}

    # Stage 1: core
    for kind in include:
        d = repo_root / "core" / kind
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            ef = ExportedFile(kind, f.name, _read(f), "core", None,
                              f.relative_to(repo_root).as_posix())
            files[ef.path] = ef

    # Stage 2: profile overlay (whole-file override or extends-merge)
    for prof in profiles:
        for kind in PROFILE_OVERLAY_KINDS:
            if kind not in include:
                continue
            d = repo_root / "profiles" / prof / kind
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                if f.name.startswith("_"):
                    continue
                rel = f.relative_to(repo_root).as_posix()
                text = _read(f)
                if _has_extends(text):
                    rx = _resolver()
                    try:
                        res = rx.resolve_profile_file(f, repo_root)
                    except ValueError as e:
                        raise ExportError(
                            f"extends resolve failed for {rel}: {e}"
                        ) from None
                    ef = ExportedFile(kind, f.name, res.text,
                                      "profile+extends", prof, rel,
                                      res.core_path.as_posix())
                else:
                    ef = ExportedFile(kind, f.name, text, "profile",
                                      prof, rel)
                files[ef.path] = ef

    # Platform notes for non-Claude agents
    for ef in files.values():
        if ef.kind == "commands":
            ef.text = _inject_note(ef.text, _command_note(ef.name))
        elif ef.kind == "hooks":
            ef.text = _inject_note(ef.text, HOOK_NOTE)
        if not ef.text.endswith("\n"):
            ef.text += "\n"

    order = {k: i for i, k in enumerate(KINDS)}
    return sorted(files.values(), key=lambda e: (order[e.kind], e.name))


def profile_meta(repo_root: Path, profiles: list[str]) -> list[dict]:
    out = []
    for name in profiles:
        pj = _load_json(repo_root / "profiles" / name / "profile.json")
        out.append({
            "name": name,
            "displayName": pj.get("displayName", name),
            "version": pj.get("version", "unknown"),
            "status": pj.get("status", "complete"),
        })
    return out


# ---------- writers ----------

def write_files(out: Path, exported: list[ExportedFile], meta: dict,
                force: bool) -> list[Path]:
    managed = [out / k for k in KINDS] + [out / "MANIFEST.json"]
    existing = [p for p in managed if p.exists()]
    if existing and not force:
        raise ExportError(
            f"{out} already contains a previous export "
            f"({existing[0].name}); pass --force to replace it"
        )
    for p in existing:
        shutil.rmtree(p) if p.is_dir() else p.unlink()

    written = []
    for ef in exported:
        dst = out / ef.kind / ef.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(ef.text)
        written.append(dst)

    entries = []
    for ef in exported:
        entry = {
            "path": ef.path,
            "kind": ef.kind,
            "origin": ef.origin,
            "source": ef.source,
            "sha256": _sha256(ef.text),
            "bytes": len(ef.text.encode("utf-8")),
        }
        if ef.profile:
            entry["profile"] = ef.profile
        if ef.extends:
            entry["extends"] = ef.extends
        entries.append(entry)
    manifest = dict(meta)
    manifest["files"] = entries
    mpath = out / "MANIFEST.json"
    with open(mpath, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    written.append(mpath)
    return written


PREAMBLE_ZH = """\
這份檔案是 **manufacturing-skill** 的純 markdown 匯出，可給任何 LLM agent 使用
（Cursor、Gemini CLI、Codex、地端 Ollama、或直接列印給人看）。

- **Agents**：角色設定。要 agent 扮演某角色時，把該段當作 system prompt 或說「請以 quote-specialist 的角色回答」。
- **Skills**：流程步驟（報價、接單、排程…）。要求 agent「依照 01-quote skill 的步驟」執行。
- **Know-how**：領域知識參考，回答時可引用。
- **Hooks**：檢查清單，**不會自動執行**，請在 `trigger` 所述時機自行套用。
- **Playbooks**：原為 Claude Code 的 slash commands；`/name` 語法只在 Claude Code 有效，其他 agent 請用自然語言呼叫。
- 內文提到的 `core/...`、`profiles/...` 路徑指的是本檔中同名段落。
- 不包含 MCP server 設定；涉及 ERP / MES 的動作請以人工確認。"""

PREAMBLE_EN = """\
This file is a plain-markdown export of **manufacturing-skill** for any LLM
agent (Cursor, Gemini CLI, Codex, an on-prem Ollama chat, or print).

- **Agents** are personas: paste one as a system prompt, or ask "answer as quote-specialist".
- **Skills** are step-by-step processes: ask the agent to "follow the 01-quote skill".
- **Know-how** is reference material the agent may cite.
- **Hooks** are checklists, **not executed automatically** — apply them at the moment named in `trigger`.
- **Playbooks** were Claude Code slash commands; the `/name` syntax is Claude Code specific — invoke them in plain language elsewhere.
- Paths such as `core/...` or `profiles/...` in the text refer to the same-named sections below.
- MCP servers are not bundled; treat any ERP / MES action as requiring human confirmation."""


def _demote_headings(body: str, by: int) -> str:
    out, in_fence = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        elif not in_fence:
            m = re.match(r"^(#{1,6})(\s.*)$", line)
            if m:
                line = "#" * min(6, len(m.group(1)) + by) + m.group(2)
        out.append(line)
    return "\n".join(out)


def render_bundle(exported: list[ExportedFile], meta: dict,
                  label: str) -> str:
    L: list[str] = []
    L.append(f"# manufacturing-skill — {label}")
    L.append("")
    L.append(f"> Generated by `{GENERATOR}` · plugin v{meta['pluginVersion']}"
             f" · format: bundle · files: {len(exported)}")
    L.append("")
    L.append("| profile | displayName | version | status |")
    L.append("|---|---|---|---|")
    if meta["profiles"]:
        for p in meta["profiles"]:
            L.append(f"| {_md_cell(p['name'])} | {_md_cell(p['displayName'])}"
                     f" | {_md_cell(p['version'])} | {_md_cell(p['status'])} |")
    else:
        L.append("| (core-only) | — | — | — |")
    L.append("")
    L.append("## 使用方式 / How to use this with any LLM agent")
    L.append("")
    L.append(PREAMBLE_ZH)
    L.append("")
    L.append(PREAMBLE_EN)
    L.append("")
    L.append("## 目錄 / Table of contents")
    L.append("")
    by_kind: dict[str, list[ExportedFile]] = {}
    for ef in exported:
        by_kind.setdefault(ef.kind, []).append(ef)
    for kind in KINDS:
        if kind not in by_kind:
            continue
        L.append(f"- [{KIND_TITLES[kind]}](#{kind}) ({len(by_kind[kind])})")
        for ef in by_kind[kind]:
            L.append(f"  - [{ef.path}](#{_anchor(kind, ef.name)})")
    L.append("")
    for kind in KINDS:
        if kind not in by_kind:
            continue
        L.append("---")
        L.append("")
        L.append(f'<a id="{kind}"></a>')
        L.append("")
        L.append(f"## {KIND_TITLES[kind]}")
        L.append("")
        for ef in by_kind[kind]:
            raw, body = _split_frontmatter(ef.text)
            L.append(f'<a id="{_anchor(kind, ef.name)}"></a>')
            L.append("")
            L.append(f"### {ef.path}")
            L.append("")
            L.append("| field | value |")
            L.append("|---|---|")
            for k, v in (_parse_frontmatter(raw) if raw else []):
                L.append(f"| {_md_cell(k)} | {_md_cell(v)} |")
            src = ef.source + (f" (extends {ef.extends})" if ef.extends
                               else "")
            L.append(f"| _source_ | {_md_cell(src)} |")
            L.append("")
            L.append(_demote_headings(body.strip("\n"), 3))
            L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def write_bundle(out: Path, exported: list[ExportedFile], meta: dict,
                 profiles: list[str]) -> list[Path]:
    tag = "+".join(profiles) if profiles else "core"
    label = ", ".join(profiles) if profiles else "core-only"
    dst = out / f"manufacturing-skill.{tag}.md"
    with open(dst, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(render_bundle(exported, meta, label))
    return [dst]


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="export.py",
        description="Export manufacturing-skill (core + profile overlay, "
                    "extends resolved) as plain markdown for any LLM agent.",
    )
    sel = p.add_mutually_exclusive_group(required=True)
    sel.add_argument("--profiles", metavar="P1[,P2...]",
                     help="comma-separated profile list "
                          "(e.g. cnc-machining,injection-molding)")
    sel.add_argument("--core-only", action="store_true",
                     help="export core only, no profile overlay")
    p.add_argument("--out", required=True, type=Path, metavar="DIR",
                   help="output directory (created if missing)")
    p.add_argument("--format", choices=("files", "bundle"), default="files",
                   help="files: directory tree + MANIFEST.json (default); "
                        "bundle: one markdown file")
    p.add_argument("--include", default=",".join(KINDS),
                   metavar="KINDS",
                   help=f"comma-separated subset of {','.join(KINDS)} "
                        f"(default: all)")
    p.add_argument("--reproducible", action="store_true",
                   help="omit the generatedAt timestamp from MANIFEST.json")
    p.add_argument("--force", action="store_true",
                   help="files format: replace a previous export in DIR")
    p.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT,
                   help=argparse.SUPPRESS)
    return p


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        include = [k.strip() for k in args.include.split(",") if k.strip()]
        bad = [k for k in include if k not in KINDS]
        if bad or not include:
            raise ExportError(
                f"--include: unknown kind(s) {bad or '(empty)'}; "
                f"choose from {','.join(KINDS)}"
            )
        include = [k for k in KINDS if k in include]
        profiles = [] if args.core_only else parse_profiles(args.profiles)
        if not args.core_only and not profiles:
            raise ExportError(f"no valid profiles in {args.profiles!r}")
        validate_profiles(repo_root, profiles)
        exported = collect(repo_root, profiles, include)

        plugin = _load_json(repo_root / "plugin.json")
        meta: dict = {
            "schema": SCHEMA,
            "generator": GENERATOR,
            "plugin": plugin.get("name", "manufacturing-skill"),
            "pluginVersion": plugin.get("version", "unknown"),
            "format": args.format,
            "profiles": profile_meta(repo_root, profiles),
            "include": include,
        }
        if not args.reproducible:
            meta["generatedAt"] = _dt.datetime.now(_dt.timezone.utc) \
                .strftime("%Y-%m-%dT%H:%M:%SZ")

        out = args.out
        if out.exists() and not out.is_dir():
            raise ExportError(f"--out {out} exists and is not a directory")
        out.mkdir(parents=True, exist_ok=True)
        if args.format == "files":
            written = write_files(out, exported, meta, args.force)
        else:
            written = write_bundle(out, exported, meta, profiles)
    except ExportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    total = sum(p.stat().st_size for p in written)
    label = ",".join(profiles) if profiles else "core-only"
    print(f"ok  exported {len(exported)} files ({label}) as {args.format} "
          f"→ {out} [{total:,} bytes]")
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
