"""Environment configuration (§18 WP3). Secrets come only from the environment;
missing secrets outside pure mock mode → refuse to start (exit 78), printing
only the variable names, never values."""
from __future__ import annotations

import math
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from . import EXIT_USAGE, ConfigRefused

DEFAULT_ROSTER = "team/.build/roster.json"
DEFAULT_STATE_DIR = "~/.local/state/manufacturing-skill/team"
DEFAULT_DENYLIST = "team/local/names.denylist"
STATE_DIR_VAR = "MFG_TEAM_STATE_DIR"
# All the gateway (and the claude-code driver) ever writes there.
STATE_ENTRIES = frozenset({"audit", "post-limits.json", "driver-tmp", "driver-home", "daily-spend.json",
                           "daily-spend.json.tmp", "daily-spend.json.lock"})
DENYLIST_VAR = "MFG_TEAM_DENYLIST"
AUDIT_KEY_VAR = "MFG_TEAM_AUDIT_HMAC_KEY"
APPROVAL_KEY_VAR = "MFG_TEAM_APPROVAL_HMAC_KEY"
MIN_KEY_LEN = 16
# Public, deliberately weak keys for mock-only demos (banner printed when used).
DEMO_AUDIT_KEY = b"demo-audit-key--not-a-secret"
DEMO_APPROVAL_KEY = b"demo-approval-key--not-a-secret"
# Numeric limits (EXT-02): finite, > 0 and below a sane ceiling. `nan` and `inf` are refused
# (`spent >= nan` is always false, so a nan daily budget would never stop anything).
MAX_DAILY_BUDGET_USD = 1000.0
DAILY_BUDGET_VAR = "MFG_TEAM_DAILY_BUDGET_USD"
# Drivers that bill a real account: the daily budget is mandatory for them (refuse start, exit 64).
BILLED_DRIVERS = frozenset({"claude-code"})
MAX_CALL_BUDGET_USD = 5.0
TIMEOUT_RANGE_S = (5, 600)


def resolve_state_dir(env: Mapping[str, str]) -> Path:
    """The state directory from `MFG_TEAM_STATE_DIR` (absolute) or the default, unresolved."""
    state = Path(env.get(STATE_DIR_VAR) or DEFAULT_STATE_DIR).expanduser()
    if not state.is_absolute():
        raise ConfigRefused(f"{STATE_DIR_VAR} must be an absolute path")
    return state


def ensure_state_dir(state: Path) -> Path:
    """EXT-05: the state dir holds the audit log, rate-limit state, the driver's temp prompts and
    the model process's private HOME. Create it 0700 when missing; refuse a symlink, a
    non-directory, another owner, or a group/other-writable mode (a shared or world-writable dir
    such as /tmp would let another account plant or swap files)."""
    if not state.is_absolute():
        raise ConfigRefused(f"{STATE_DIR_VAR} must be an absolute path")
    try:
        state.mkdir(parents=True, mode=0o700)
        os.chmod(state, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise ConfigRefused(f"cannot create the state directory {state} ({type(exc).__name__})") from None
    st = os.lstat(state)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise ConfigRefused(f"state directory {state} is not a plain directory (symlink or file)")
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        raise ConfigRefused(f"state directory {state} is not owned by the user running the gateway")
    if st.st_mode & 0o022:
        raise ConfigRefused(f"state directory {state} is group- or world-writable; run: chmod 700 {state}")
    return state


def stale_state_help(state_dir: Path, env: Mapping[str, str]) -> str:
    """What to do when the audit log in `state_dir` does not verify (printed with the refusal)."""
    origin = "the default" if not env.get(STATE_DIR_VAR) else f"set by {STATE_DIR_VAR}"
    return (
        f"\n  State directory: {state_dir} ({origin}); the audit log is in {state_dir / 'audit'}."
        "\n  A log left by an earlier run (another key, or the public demo key) cannot be resumed."
        "\n  On a dev machine you can move it aside (nothing is deleted):"
        "\n      python3 team/tools/teamctl.py state-reset --confirm"
        f"\n  Or keep it and start with a different directory: {STATE_DIR_VAR}=/absolute/other/dir"
        "\n  On a real deployment do not reset: run `audit-verify`, the log may have been tampered with.")


def move_state_aside(state_dir: Path, now: float | None = None) -> Path | None:
    """Rename `state_dir` to `<name>.stale-YYYYmmdd-HHMMSS[-N]` next to it (never deletes).

    Returns the new path, or None if there is nothing to move. Refuses (ConfigRefused) when the
    directory holds anything the gateway does not write, e.g. a wrongly configured $HOME."""
    if not state_dir.exists():
        return None
    if not state_dir.is_dir() or state_dir.is_symlink():
        raise ConfigRefused(f"{state_dir} is not a plain directory; refusing to move it")
    foreign = sorted(p.name for p in state_dir.iterdir() if p.name not in STATE_ENTRIES)
    if foreign:
        raise ConfigRefused(f"{state_dir} holds files the gateway does not write ({', '.join(foreign[:5])}); "
                            "refusing to move it, check the path")
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    target, n = state_dir.with_name(f"{state_dir.name}.stale-{stamp}"), 1
    while target.exists():
        n += 1
        target = state_dir.with_name(f"{state_dir.name}.stale-{stamp}-{n}")
    state_dir.rename(target)
    return target


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
    denylist: Path | None = None       # optional local denylist (inbound DLP + output filter)


def _num(env: Mapping[str, str], name: str, default: float | None, cast=float, *,
         low: float = 0.0, high: float = math.inf):
    """A finite number in (`low`, `high`] (or [`low`, `high`] when `low` > 0); refusal exit 64."""
    raw = env.get(name)
    if raw in (None, ""):
        return default
    try:
        value = cast(raw.strip())
    except (ValueError, OverflowError):
        raise ConfigRefused(f"{name} must be a number", exit=EXIT_USAGE) from None
    if not math.isfinite(value):
        raise ConfigRefused(f"{name} must be a finite number (not nan/inf)", exit=EXIT_USAGE)
    if value <= 0 or value < low or value > high:
        bounds = f"between {low:g} and {high:g}" if low > 0 else f"> 0 and at most {high:g}"
        raise ConfigRefused(f"{name} must be {bounds}", exit=EXIT_USAGE)
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
    state = resolve_state_dir(env)
    deny_raw = env.get(DENYLIST_VAR)
    if deny_raw and not Path(deny_raw).expanduser().is_file():
        raise ConfigRefused(f"{DENYLIST_VAR} is set but is not a file")
    deny = Path(deny_raw or DEFAULT_DENYLIST).expanduser()
    daily = _num(env, DAILY_BUDGET_VAR, None, high=MAX_DAILY_BUDGET_USD)
    if daily is None and driver in BILLED_DRIVERS:
        raise ConfigRefused(
            f"{DAILY_BUDGET_VAR} is required with --driver {driver}: set it to the most this gateway may "
            f"spend per twin per UTC day, in USD (a number > 0 and at most {MAX_DAILY_BUDGET_USD:g}); "
            "the day's total is kept in the state dir (daily-spend.json) and survives restarts",
            exit=EXIT_USAGE)
    return GatewayConfig(
        roster=Path(roster or env.get("MFG_TEAM_ROSTER") or DEFAULT_ROSTER),
        adapter=adapter, driver=driver, state_dir=state.resolve(),
        audit_key=env[AUDIT_KEY_VAR].encode() if env.get(AUDIT_KEY_VAR) else DEMO_AUDIT_KEY,
        approval_key=env[APPROVAL_KEY_VAR].encode() if env.get(APPROVAL_KEY_VAR) else DEMO_APPROVAL_KEY,
        demo_keys=bool(missing),
        daily_budget_usd=daily,
        max_budget_usd=_num(env, "MFG_TEAM_MAX_BUDGET_USD", 0.10, high=MAX_CALL_BUDGET_USD),
        timeout_s=int(_num(env, "MFG_TEAM_TIMEOUT_S", 60, int, low=TIMEOUT_RANGE_S[0], high=TIMEOUT_RANGE_S[1])),
        denylist=deny if deny.is_file() else None,
    )
