#!/usr/bin/env python3
"""Multi-profile active helper for install.sh.

Two subcommands:

  scan <p1> <p2> [...]
      Detect file collisions between active profiles. A collision is
      two profiles containing the same `<kind>/<basename>.md` under
      `agents`, `skills`, `know-how`, or `hooks`. Exit 0 if clean,
      exit 1 with one ::error line per collision.

  scan-all
      Same as `scan` but enumerates every unordered pair from
      `plugin.json`'s `profiles.available` list. Used by CI Step 12.

  aggregate <p1> <p2> [...]
      Emit `active-profiles.json` to stdout per spec §6.3:
      schema-versioned, manifest list preserved, list-typed metadata
      union'd, scalars not aggregated.

Spec: docs/superpowers/specs/2026-05-09-multi-profile-active-design.md
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import sys
from pathlib import Path

KINDS_TO_DIR = {
    "agents": "agents",
    "skills": "skills",
    "knowHow": "know-how",
    "hooks": "hooks",
}

LIST_FIELDS_FOR_AGGREGATION = (
    "applicableTo",
    "tags",
    "complianceFrameworks",
    "wantedContributions",
    "warnings",
)


@dataclasses.dataclass(frozen=True)
class Conflict:
    kind: str          # "agents" / "skills" / "know-how" / "hooks"
    basename: str      # e.g. "quote-specialist"
    profiles: tuple    # tuple of profile names (sorted)

    def render(self) -> str:
        names = ", ".join(self.profiles)
        return (f"{self.kind}/{self.basename}.md present in multiple "
                f"profiles: {names}")


def list_profile_files(profile_dir: Path, kind_dir: str) -> set[str]:
    d = profile_dir / kind_dir
    if not d.is_dir():
        return set()
    return {
        f.stem for f in d.iterdir()
        if f.suffix == ".md" and not f.name.startswith("_")
    }


def scan_pair(repo_root: Path, p1: str, p2: str) -> list[Conflict]:
    """Return conflicts between two profiles."""
    out: list[Conflict] = []
    d1 = repo_root / "profiles" / p1
    d2 = repo_root / "profiles" / p2
    for kind_key, kind_dir in KINDS_TO_DIR.items():
        f1 = list_profile_files(d1, kind_dir)
        f2 = list_profile_files(d2, kind_dir)
        for basename in sorted(f1 & f2):
            out.append(Conflict(
                kind=kind_dir,
                basename=basename,
                profiles=tuple(sorted([p1, p2])),
            ))
    return out


def scan_set(
    repo_root: Path,
    profile_names: list[str],
) -> list[Conflict]:
    """Return all collisions in a set of profiles. Reports per
    basename, not per pair, so a 3-way collision shows once."""
    seen: dict[tuple[str, str], list[str]] = {}
    for name in profile_names:
        d = repo_root / "profiles" / name
        for kind_key, kind_dir in KINDS_TO_DIR.items():
            for basename in list_profile_files(d, kind_dir):
                seen.setdefault((kind_dir, basename), []).append(name)
    out: list[Conflict] = []
    for (kind_dir, basename), profiles in seen.items():
        if len(profiles) > 1:
            out.append(Conflict(
                kind=kind_dir,
                basename=basename,
                profiles=tuple(sorted(profiles)),
            ))
    return sorted(out, key=lambda c: (c.kind, c.basename))


def cmd_scan(args) -> int:
    repo_root = Path(args.repo_root or ".").resolve()
    profile_names = args.profile_name
    missing = [n for n in profile_names
               if not (repo_root / "profiles" / n / "profile.json").is_file()]
    if missing:
        for m in missing:
            print(f"::error::profile {m!r} not found at "
                  f"profiles/{m}/profile.json", file=sys.stderr)
        return 1
    conflicts = scan_set(repo_root, profile_names)
    if conflicts:
        for c in conflicts:
            print(f"::error::{c.render()}", file=sys.stderr)
        print(
            f"\n{len(conflicts)} file collision(s) across "
            f"{len(profile_names)} profiles: "
            f"{profile_names}",
            file=sys.stderr,
        )
        return 1
    print(f"ok  no conflicts across {len(profile_names)} "
          f"profiles: {', '.join(profile_names)}")
    return 0


def cmd_scan_all(args) -> int:
    repo_root = Path(args.repo_root or ".").resolve()
    plugin_json = json.loads(
        (repo_root / "plugin.json").read_text(encoding="utf-8")
    )
    available = plugin_json.get("profiles", {}).get("available", [])
    fail = False
    pair_count = 0
    for p1, p2 in itertools.combinations(sorted(available), 2):
        pair_count += 1
        conflicts = scan_pair(repo_root, p1, p2)
        if conflicts:
            fail = True
            for c in conflicts:
                print(f"::error::{c.render()}", file=sys.stderr)
        else:
            print(f"ok  ({p1}, {p2})")
    print(f"\nscanned {pair_count} pairs from "
          f"{len(available)} available profiles")
    return 1 if fail else 0


def aggregate_lists(
    profiles: list[dict],
    field: str,
    *,
    nested_path: tuple = (),
) -> list:
    """Union all profiles' values for `field`, preserving first-occurrence
    order. `nested_path` lets us aggregate `mcp.recommended`."""
    out: list = []
    seen: set = set()
    for prof in profiles:
        cursor = prof
        for key in nested_path:
            cursor = cursor.get(key, {})
        values = cursor.get(field, [])
        if not isinstance(values, list):
            continue
        for v in values:
            marker = json.dumps(v, sort_keys=True) \
                if not isinstance(v, str) else v
            if marker not in seen:
                seen.add(marker)
                out.append(v)
    return out


def aggregate_profiles(
    repo_root: Path,
    profile_names: list[str],
) -> dict:
    """Build the active-profiles.json content per spec §6.3."""
    manifests: list[dict] = []
    for name in profile_names:
        pj = repo_root / "profiles" / name / "profile.json"
        manifests.append(json.loads(pj.read_text(encoding="utf-8")))

    aggregated: dict = {}
    for field in LIST_FIELDS_FOR_AGGREGATION:
        aggregated[field] = aggregate_lists(manifests, field)
    aggregated["mcp"] = {
        "recommended": aggregate_lists(
            manifests, "recommended", nested_path=("mcp",)
        ),
        "optional": aggregate_lists(
            manifests, "optional", nested_path=("mcp",)
        ),
    }

    return {
        "schema": 1,
        "primary": profile_names[0] if profile_names else None,
        "profiles": manifests,
        "aggregated": aggregated,
    }


def cmd_aggregate(args) -> int:
    repo_root = Path(args.repo_root or ".").resolve()
    profile_names = args.profile_name
    missing = [n for n in profile_names
               if not (repo_root / "profiles" / n / "profile.json").is_file()]
    if missing:
        for m in missing:
            print(f"::error::profile {m!r} not found", file=sys.stderr)
        return 1
    result = aggregate_profiles(repo_root, profile_names)
    out = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-profile helper for install.sh"
    )
    parser.add_argument(
        "--repo-root", help="repo root (default: current directory)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser(
        "scan", help="detect collisions in a given profile list"
    )
    p_scan.add_argument("profile_name", nargs="+")
    p_scan.set_defaults(func=cmd_scan)

    p_all = sub.add_parser(
        "scan-all",
        help="enumerate every pair from plugin.json's available list"
    )
    p_all.set_defaults(func=cmd_scan_all)

    p_agg = sub.add_parser(
        "aggregate",
        help="emit active-profiles.json for a given profile list"
    )
    p_agg.add_argument("profile_name", nargs="+")
    p_agg.add_argument("--out", help="output path (default: stdout)")
    p_agg.set_defaults(func=cmd_aggregate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
