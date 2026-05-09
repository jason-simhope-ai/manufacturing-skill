#!/usr/bin/env python3
"""Tests for the multi-profile helper.

Builds mini fake repos in temp dirs and exercises `_multiprofile.py`'s
scan / aggregate functions directly (in-process, fast). Failures stop
the run with a clear assertion trace.

Usage:
    python tests/multiprofile/test_multiprofile.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "adapters" / "claude-code"),
)

import _multiprofile as mp  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_fake_repo(tmp: Path, profiles_spec: dict) -> Path:
    """profiles_spec = {
        'alpha': {'agents': ['foo'], 'skills': ['quoting']},
        'beta':  {'agents': ['foo']},
    }
    Creates profiles/<name>/<kind>/<basename>.md plus profile.json plus
    plugin.json. Each kind dir = agents/skills/know-how/hooks.
    """
    plugin_json = {
        "name": "test-plugin",
        "version": "0.0.1",
        "profiles": {
            "available": list(profiles_spec.keys()),
            "complete": list(profiles_spec.keys()),
            "alpha": [],
            "stub": [],
        },
    }
    (tmp / "plugin.json").write_text(
        json.dumps(plugin_json, indent=2), encoding="utf-8"
    )

    kind_to_dir = {
        "agents": "agents",
        "skills": "skills",
        "knowHow": "know-how",
        "hooks": "hooks",
    }
    for prof_name, kinds in profiles_spec.items():
        prof_dir = tmp / "profiles" / prof_name
        prof_dir.mkdir(parents=True)
        # profile.json
        manifest = {
            "name": prof_name,
            "displayName": prof_name.upper(),
            "version": "0.0.1",
            "description": f"test profile {prof_name}",
            "extends-core": True,
            "applicableTo": [f"{prof_name}-domain"],
            "tags": [prof_name, "test"],
            "agents": kinds.get("agents", []),
            "skills": kinds.get("skills", []),
            "knowHow": kinds.get("knowHow", []),
            "hooks": kinds.get("hooks", []),
            "complianceFrameworks": [f"std-{prof_name}", "shared-std"],
            "mcp": {
                "recommended": [f"mcp-{prof_name}", "mcp-shared"],
                "optional": [],
            },
        }
        (prof_dir / "profile.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        # md files for each kind
        for kind, basenames in kinds.items():
            kind_dir = prof_dir / kind_to_dir[kind]
            kind_dir.mkdir(parents=True, exist_ok=True)
            for bn in basenames:
                (kind_dir / f"{bn}.md").write_text(
                    f"# {bn}\nFrom profile {prof_name}.\n",
                    encoding="utf-8",
                )
    return tmp


def run_test(name: str, fn):
    print(f"  [run] {name} ... ", end="")
    try:
        with tempfile.TemporaryDirectory() as tmpd:
            fn(Path(tmpd))
        print("PASS")
        return True
    except AssertionError as e:
        print("FAIL")
        print(f"        AssertionError: {e}")
        return False
    except Exception as e:  # noqa: BLE001
        print("FAIL")
        print(f"        {type(e).__name__}: {e}")
        return False


# --- Test cases ---

def test_clean_pair(tmp: Path):
    """Two profiles with no overlapping basenames → no conflicts."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["foo"], "skills": ["quoting"]},
        "beta":  {"agents": ["bar"], "skills": ["billing"]},
    })
    conflicts = mp.scan_set(tmp, ["alpha", "beta"])
    assert conflicts == [], f"expected no conflicts, got {conflicts}"


def test_pair_collision_agents(tmp: Path):
    """Two profiles each with agents/foo.md → 1 conflict."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["foo"]},
        "beta":  {"agents": ["foo"]},
    })
    conflicts = mp.scan_set(tmp, ["alpha", "beta"])
    assert len(conflicts) == 1, f"expected 1 conflict, got {len(conflicts)}"
    c = conflicts[0]
    assert c.kind == "agents"
    assert c.basename == "foo"
    assert sorted(c.profiles) == ["alpha", "beta"]


def test_three_way_partial_collision(tmp: Path):
    """A+B+C where only B and C share a basename. A is fine."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["a-only"]},
        "beta":  {"agents": ["shared"]},
        "gamma": {"agents": ["shared", "g-only"]},
    })
    conflicts = mp.scan_set(tmp, ["alpha", "beta", "gamma"])
    assert len(conflicts) == 1, conflicts
    c = conflicts[0]
    assert c.basename == "shared"
    assert sorted(c.profiles) == ["beta", "gamma"]


def test_collision_across_kinds(tmp: Path):
    """Same basename in different kinds is NOT a conflict."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["foo"]},
        "beta":  {"skills": ["foo"]},  # same basename, different kind
    })
    conflicts = mp.scan_set(tmp, ["alpha", "beta"])
    assert conflicts == [], (
        f"different kinds shouldn't collide, got {conflicts}"
    )


def test_aggregate_list_union(tmp: Path):
    """Aggregation unions list fields with order-preserving dedupe."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["a1"]},
        "beta":  {"agents": ["b1"]},
    })
    result = mp.aggregate_profiles(tmp, ["alpha", "beta"])
    assert result["schema"] == 1
    assert result["primary"] == "alpha"
    assert len(result["profiles"]) == 2
    assert result["profiles"][0]["name"] == "alpha"
    # complianceFrameworks: alpha has [std-alpha, shared-std],
    # beta has [std-beta, shared-std]. Union preserving order:
    expected = ["std-alpha", "shared-std", "std-beta"]
    assert result["aggregated"]["complianceFrameworks"] == expected, (
        f"got {result['aggregated']['complianceFrameworks']}"
    )
    # mcp.recommended: alpha [mcp-alpha, mcp-shared], beta [mcp-beta, mcp-shared]
    assert result["aggregated"]["mcp"]["recommended"] == [
        "mcp-alpha", "mcp-shared", "mcp-beta",
    ]


def test_aggregate_single_profile(tmp: Path):
    """N=1 case must still produce a valid active-profiles.json shape."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["a1"]},
    })
    result = mp.aggregate_profiles(tmp, ["alpha"])
    assert result["primary"] == "alpha"
    assert len(result["profiles"]) == 1
    assert result["aggregated"]["complianceFrameworks"] == [
        "std-alpha", "shared-std",
    ]


def test_scan_pair_function(tmp: Path):
    """scan_pair should mirror scan_set's pairwise output."""
    make_fake_repo(tmp, {
        "alpha": {"agents": ["foo"], "skills": ["s1"]},
        "beta":  {"agents": ["foo"], "skills": ["s1"]},
    })
    conflicts = mp.scan_pair(tmp, "alpha", "beta")
    assert len(conflicts) == 2, conflicts
    kinds = {c.kind for c in conflicts}
    assert kinds == {"agents", "skills"}


def test_real_repo_no_conflicts(tmp: Path):
    """The real manufacturing-skill repo's profiles must scan clean —
    if this fails, a contributor introduced a basename collision."""
    conflicts = mp.scan_set(REPO_ROOT, [
        "cnc-machining", "injection-molding",
    ])
    assert conflicts == [], (
        f"cnc + injection should not conflict in current repo, "
        f"got {conflicts}"
    )


# --- Runner ---

TESTS = [
    ("clean pair (no overlap)", test_clean_pair),
    ("pair collision in agents", test_pair_collision_agents),
    ("three-way partial collision (B+C only)", test_three_way_partial_collision),
    ("same basename across kinds is fine", test_collision_across_kinds),
    ("aggregate list union with dedupe", test_aggregate_list_union),
    ("aggregate N=1 still valid", test_aggregate_single_profile),
    ("scan_pair function", test_scan_pair_function),
    ("real repo: cnc + injection clean", test_real_repo_no_conflicts),
]


def main() -> int:
    fails = 0
    for name, fn in TESTS:
        if not run_test(name, fn):
            fails += 1
    total = len(TESTS)
    print(f"\n{total - fails}/{total} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
