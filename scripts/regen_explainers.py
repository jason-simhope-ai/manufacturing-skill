#!/usr/bin/env python3
"""Regenerate auto-managed sections inside docs/explainers/*.html.

Sections that drift over time (file counts, version, profile status)
are wrapped in `<!-- AUTO-START: <id> -->` / `<!-- AUTO-END: <id> -->`
markers in the HTML. This script regenerates them from authoritative
sources:
- `plugin.json` for version + profile lists
- the actual filesystem under `core/` and `profiles/` for counts

Run locally:
    python scripts/regen_explainers.py

CI check (in the validate job):
    python scripts/regen_explainers.py
    git diff --exit-code docs/explainers/

Why a regen + diff approach (not a Jinja template):
- Keeps the human-authored narrative intact and editable
- Output is concrete HTML, no build step at install time
- Diff failure on PR = the manifest grew but the explainer stayed
  stale, exactly the bug we kept hitting in v0.1.x
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def count_md(d: Path) -> int:
    if not d.is_dir():
        return 0
    return sum(
        1 for f in d.iterdir()
        if f.suffix == ".md" and not f.name.startswith("_")
    )


def gather_metrics() -> dict:
    """Gather counts that show up in explainer 01's stat panel."""
    plugin_json = json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))
    version = plugin_json["version"]

    # Core counts
    core_agents = count_md(REPO / "core" / "agents")
    core_skills = count_md(REPO / "core" / "skills")
    core_kh = count_md(REPO / "core" / "know-how")
    core_hooks = count_md(REPO / "core" / "hooks")

    # CNC profile (complete)
    cnc_agents = count_md(REPO / "profiles" / "cnc-machining" / "agents")
    cnc_skills = count_md(REPO / "profiles" / "cnc-machining" / "skills")
    cnc_kh = count_md(REPO / "profiles" / "cnc-machining" / "know-how")
    cnc_hooks = count_md(REPO / "profiles" / "cnc-machining" / "hooks")

    # Injection profile (alpha)
    inj_agents = count_md(REPO / "profiles" / "injection-molding" / "agents")
    inj_skills = count_md(REPO / "profiles" / "injection-molding" / "skills")
    inj_kh = count_md(REPO / "profiles" / "injection-molding" / "know-how")
    inj_hooks = count_md(REPO / "profiles" / "injection-molding" / "hooks")

    profiles = plugin_json.get("profiles", {})
    n_complete = len(profiles.get("complete", []))
    n_alpha = len(profiles.get("alpha", []))
    n_stub = len(profiles.get("stub", []))
    n_total_profiles = n_complete + n_alpha + n_stub

    return {
        "version": version,
        "agents": {
            "core": core_agents, "cnc": cnc_agents, "inj": inj_agents,
            "total": core_agents + cnc_agents + inj_agents,
        },
        "skills": {
            "core": core_skills, "cnc": cnc_skills, "inj": inj_skills,
            "total": core_skills + cnc_skills + inj_skills,
        },
        "kh": {
            "core": core_kh, "cnc": cnc_kh, "inj": inj_kh,
            "total": core_kh + cnc_kh + inj_kh,
        },
        "hooks": {
            "core": core_hooks, "cnc": cnc_hooks, "inj": inj_hooks,
            "total": core_hooks + cnc_hooks + inj_hooks,
        },
        "profiles": {
            "complete": n_complete, "alpha": n_alpha, "stub": n_stub,
            "total": n_total_profiles,
        },
    }


def render_explainer01_stats(m: dict) -> str:
    """Block content for `explainer01-stats` marker.

    Format mirrors the hand-crafted version: single line per stat,
    2-space indent (matches surrounding HTML), no trailing newline
    after the last stat (the closing AUTO-END marker provides one).
    """
    lines = [
        f'<div class="panel-title">當前規模 v{m["version"]}</div>',
        f'<div class="stat"><div class="stat-num">{m["agents"]["total"]}</div>'
        f'<div class="stat-label">Agents（'
        f'{m["agents"]["core"]} + {m["agents"]["cnc"]} + '
        f'{m["agents"]["inj"]}α）</div></div>',
        f'<div class="stat"><div class="stat-num">{m["skills"]["total"]}</div>'
        f'<div class="stat-label">Skills（'
        f'{m["skills"]["core"]} + {m["skills"]["cnc"]} + '
        f'{m["skills"]["inj"]}α）</div></div>',
        f'<div class="stat"><div class="stat-num">{m["kh"]["total"]}</div>'
        f'<div class="stat-label">Know-how（'
        f'{m["kh"]["core"]} + {m["kh"]["cnc"]} + '
        f'{m["kh"]["inj"]}α）</div></div>',
        f'<div class="stat"><div class="stat-num">{m["hooks"]["total"]}</div>'
        f'<div class="stat-label">Hooks（'
        f'{m["hooks"]["core"]} + {m["hooks"]["cnc"]}）</div></div>',
        f'<div class="stat"><div class="stat-num">'
        f'{m["profiles"]["total"]}</div>'
        f'<div class="stat-label">Profile（'
        f'{m["profiles"]["complete"]} 完整 + '
        f'{m["profiles"]["alpha"]}α + '
        f'{m["profiles"]["stub"]} stub）</div></div>',
    ]
    indent = "      "
    return "\n".join(indent + ln for ln in lines)


# Map of marker_id → (file relative to repo, render function)
SECTIONS: list[tuple[str, str, callable]] = [
    (
        "explainer01-stats",
        "docs/explainers/01-架構總覽.html",
        render_explainer01_stats,
    ),
]


MARKER_RE_TPL = (
    r"(<!--\s*AUTO-START:\s*{id}\s*-->\n"
    r"(?:[^\n]*\n)?"  # optional regenerate-with comment line
    r")(.*?)"
    r"(\n\s*<!--\s*AUTO-END(?::\s*{id})?\s*-->)"
)


def regen_section(text: str, marker_id: str, content: str) -> tuple[str, bool]:
    """Replace the body between the AUTO-START/AUTO-END markers.

    Returns (new_text, changed).
    """
    pat = re.compile(
        MARKER_RE_TPL.format(id=re.escape(marker_id)),
        flags=re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        raise ValueError(
            f"marker `AUTO-START: {marker_id}` not found"
        )
    new_block = m.group(1) + content + m.group(3)
    if m.group(0) == new_block:
        return text, False
    return text[: m.start()] + new_block + text[m.end():], True


def main(check: bool = False) -> int:
    metrics = gather_metrics()
    any_changed = False
    for marker_id, rel_path, render in SECTIONS:
        path = REPO / rel_path
        original = path.read_text(encoding="utf-8")
        new_content = render(metrics)
        try:
            updated, changed = regen_section(original, marker_id, new_content)
        except ValueError as e:
            print(f"::error file={rel_path}::{e}", file=sys.stderr)
            return 1
        if changed:
            any_changed = True
            if check:
                print(
                    f"::error file={rel_path}::"
                    f"AUTO section `{marker_id}` is out of date. "
                    f"Run: python scripts/regen_explainers.py",
                    file=sys.stderr,
                )
            else:
                path.write_text(updated, encoding="utf-8")
                print(f"updated {rel_path} (section: {marker_id})")
        else:
            print(f"ok      {rel_path} (section: {marker_id})")
    if check and any_changed:
        return 1
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument(
        "--check", action="store_true",
        help="exit 1 if any section is stale, do not write",
    )
    args = p.parse_args()
    sys.exit(main(check=args.check))
