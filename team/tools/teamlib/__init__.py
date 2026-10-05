"""Digital-twin team tier: hand-written validator + deterministic compiler.

Single source of truth for the team-tier schemas (spec
docs/superpowers/specs/2026-10-05-digital-twin-team-design.md, section 5).
There is no JSON Schema file; every rule lives here and carries an error
code (E0xx) or warning code (W00x) from the `CODES` table.

Public interface (spec section 18, WP2):

    load_roster(path) -> dict
    load_twin(path) -> (frontmatter dict, body str)
    validate(repo_root, roster_path, *, mode, today) -> list[Finding]
    validate_ex(...) -> (list[Finding], stats dict)     # + outsource/bytes stats
    effective_autonomy(cap, twin, position, policy, channel) -> str
    build(repo_root, roster_path, out_dir) -> BuildResult
    compile_all(repo_root, roster_path) -> Compiled      # in-memory build

Modules (each imports only from the ones above it):

    schema.py    constants, BUDGETS, CODES, id/date regexes, Finding / LoadError / BuildError,
                 field specs, and the secret/name/PII/DLP regexes loaded from
                 infra/chat-gateway/chat_gateway/patterns.py (the single source)
    io.py        YAML (SafeLoader, duplicate keys rejected, ISO dates), JSON, date and hash helpers
    compile.py   reference resolution, prompt assembly, compile_all / render_summary / build
    validate.py  schema walker, effective_autonomy, _Validator, validate / validate_ex

`team/tools/_teamlib.py` is a compatibility shim that re-exports every name (public and
private) of these modules, so `build.py`, `teamctl.py`, `deid.py` and the tests keep their
`import _teamlib as lib`.

Runtime: Python 3.11, stdlib only, plus PyYAML (build / validate paths only).
"""
from __future__ import annotations

from .schema import (ACTING_MAX_DAYS, ADAPTER_MAX_TIER, ADAPTERS, AUTONOMY, BUDGETS, BUILT_BY, CATEGORY_LABEL,
                     CATEGORY_VALUES, CODES, DOER_HINT_WORDS, GATE_RESULTS, GATE_STALE_DAYS, IDENTITY_KEYS,
                     NAME_OTHER, NAME_ZH, NOBODY_TODAY_RE, OUTSOURCE_MAX_DAYS, OUTSOURCE_WARN_DAYS, PII_PATTERNS,
                     REF_PREFIX, REQUIRED_GITIGNORE, REQUIRED_SECTIONS, REVIEW_FILLER_WORDS, REVIEW_ONLY_WORDS,
                     SAFETY_KEYWORDS, SECRET_PATTERNS, TIER_CAP, TIERS, TOOL_REPO, VERSION,
                     BuildError, Finding, LoadError, dlp_scan, load_lint_allow, shared_secret_patterns)
from .io import canon, est_tokens, load_roster, load_twin, split_frontmatter, yaml_load
from .compile import (BuildResult, Compiled, build, check_deterministic, compile_all, default_roster, find_ref,
                      render_summary, resolved_text)
from .validate import effective_autonomy, validate, validate_ex

__all__ = [
    "ACTING_MAX_DAYS", "ADAPTER_MAX_TIER", "ADAPTERS", "AUTONOMY", "BUDGETS", "BUILT_BY", "CATEGORY_LABEL",
    "CATEGORY_VALUES", "CODES", "DOER_HINT_WORDS", "GATE_RESULTS", "GATE_STALE_DAYS", "IDENTITY_KEYS",
    "NAME_OTHER", "NAME_ZH", "NOBODY_TODAY_RE", "OUTSOURCE_MAX_DAYS", "OUTSOURCE_WARN_DAYS", "PII_PATTERNS",
    "REF_PREFIX", "REQUIRED_GITIGNORE", "REQUIRED_SECTIONS", "REVIEW_FILLER_WORDS", "REVIEW_ONLY_WORDS",
    "SAFETY_KEYWORDS", "SECRET_PATTERNS", "TIER_CAP", "TIERS", "TOOL_REPO", "VERSION",
    "BuildError", "BuildResult", "Compiled", "Finding", "LoadError",
    "build", "canon", "check_deterministic", "compile_all", "default_roster", "dlp_scan", "effective_autonomy",
    "est_tokens", "find_ref", "load_lint_allow", "load_roster", "load_twin", "render_summary", "resolved_text",
    "shared_secret_patterns", "split_frontmatter", "validate", "validate_ex", "yaml_load",
]
