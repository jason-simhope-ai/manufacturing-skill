"""Environment configuration (§18 WP3). Secrets come only from the environment;
missing secrets outside pure mock mode → refuse to start (exit 78), printing
only the variable names, never values."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from . import ConfigRefused

DEFAULT_ROSTER = "team/.build/roster.json"
DEFAULT_STATE_DIR = "~/.local/state/manufacturing-skill/team"
AUDIT_KEY_VAR = "MFG_TEAM_AUDIT_HMAC_KEY"
APPROVAL_KEY_VAR = "MFG_TEAM_APPROVAL_HMAC_KEY"
MIN_KEY_LEN = 16
# Public, deliberately weak keys for mock-only demos (banner printed when used).
DEMO_AUDIT_KEY = b"demo-audit-key--not-a-secret"
DEMO_APPROVAL_KEY = b"demo-approval-key--not-a-secret"


@dataclass(frozen=True)
class GatewayConfig:
    roster: Path
    adapter: str
    driver: str
    state_dir: Path
    audit_key: bytes
    approval_key: bytes
    demo_keys: bool
    daily_budget_usd: float | None
    max_budget_usd: float
    timeout_s: int


def _num(env: Mapping[str, str], name: str, default: float | None, cast=float):
    raw = env.get(name)
    if raw in (None, ""):
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigRefused(f"{name} must be a number") from None
    if value <= 0:
        raise ConfigRefused(f"{name} must be > 0")
    return value


def config_from_env(env: Mapping[str, str], *, roster: str | None = None, adapter: str | None = None,
                    driver: str | None = None) -> GatewayConfig:
    adapter = adapter or env.get("MFG_TEAM_ADAPTER") or "mock"
    driver = driver or env.get("MFG_TEAM_DRIVER") or "mock"
    mock_mode = adapter == "mock" and driver == "mock"
    missing = [v for v in (AUDIT_KEY_VAR, APPROVAL_KEY_VAR) if not env.get(v)]
    if missing and not mock_mode:
        raise ConfigRefused("missing required environment variables: " + ", ".join(missing))
    short = [v for v in (AUDIT_KEY_VAR, APPROVAL_KEY_VAR) if env.get(v) and len(env[v]) < MIN_KEY_LEN]
    if short:
        raise ConfigRefused(f"environment variables shorter than {MIN_KEY_LEN} chars: " + ", ".join(short))
    state = Path(env.get("MFG_TEAM_STATE_DIR") or DEFAULT_STATE_DIR).expanduser()
    if not state.is_absolute():
        raise ConfigRefused("MFG_TEAM_STATE_DIR must be an absolute path")
    return GatewayConfig(
        roster=Path(roster or env.get("MFG_TEAM_ROSTER") or DEFAULT_ROSTER),
        adapter=adapter, driver=driver, state_dir=state.resolve(),
        audit_key=env[AUDIT_KEY_VAR].encode() if env.get(AUDIT_KEY_VAR) else DEMO_AUDIT_KEY,
        approval_key=env[APPROVAL_KEY_VAR].encode() if env.get(APPROVAL_KEY_VAR) else DEMO_APPROVAL_KEY,
        demo_keys=bool(missing),
        daily_budget_usd=_num(env, "MFG_TEAM_DAILY_BUDGET_USD", None),
        max_budget_usd=_num(env, "MFG_TEAM_MAX_BUDGET_USD", 0.10),
        timeout_s=int(_num(env, "MFG_TEAM_TIMEOUT_S", 60, int)),
    )
