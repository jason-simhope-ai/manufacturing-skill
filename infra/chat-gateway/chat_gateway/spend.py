"""Daily spend per twin (MFG_TEAM_DAILY_BUDGET_USD).

Without a path the totals live in memory (tests, mock demos). With a path they are kept in a
0600 JSON file in the state dir, keyed by UTC date and twin id:

    {"2026-10-05": {"qa-manager": 0.0123, "production-manager": 0.0045}}

so a restart, or a separate `chat_gateway post` process started by cron, sees the same day's
total. Every read and write takes an exclusive `flock` on a sibling lock file and re-reads the
file, so two gateway processes sharing one state dir do not lose each other's spend.

A file that is not a plain 0600 file owned by this user, or is not valid JSON of the shape above,
refuses start (exit 78): the gateway never silently restarts the day's count from zero.
"""
from __future__ import annotations

import contextlib
import json
import math
import os
import stat
from pathlib import Path

from . import ConfigRefused

try:  # POSIX; the gateway's supported hosts are Linux and macOS.
    import fcntl
except ImportError:  # pragma: no cover - Windows: single-process use only
    fcntl = None  # type: ignore[assignment]

SPEND_FILE = "daily-spend.json"
SPEND_TMP = SPEND_FILE + ".tmp"
SPEND_LOCK = SPEND_FILE + ".lock"
KEEP_DAYS = 7


class SpendPersistError(OSError):
    """The day's spend could not be written; the gateway stops calling the model."""


class DailySpend:
    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path is not None else None
        self._days: dict[str, dict[str, float]] = {}
        if self.path is not None:
            with self._locked():
                self._days = self._read()

    # ── public ──
    def get(self, twin: str, day: str) -> float:
        if self.path is not None:
            with self._locked():
                self._days = self._read()
        return self._days.get(day, {}).get(twin, 0.0)

    def add(self, twin: str, day: str, cost: float) -> float:
        """Add `cost` (USD, finite, >= 0) to `twin` on `day`; returns the new total."""
        if not (isinstance(cost, (int, float)) and math.isfinite(cost) and cost >= 0):
            raise ValueError("cost must be a finite number >= 0")
        if self.path is None:
            return self._bump(twin, day, cost)
        try:
            with self._locked():
                self._days = self._read()
                total = self._bump(twin, day, cost)
                self._write()
                return total
        except ConfigRefused as exc:   # the file changed under us into something unusable
            raise SpendPersistError(str(exc)) from None

    # ── internals ──
    def _bump(self, twin: str, day: str, cost: float) -> float:
        days = self._days.setdefault(day, {})
        days[twin] = round(days.get(twin, 0.0) + float(cost), 6)
        for old in sorted(self._days)[:-KEEP_DAYS]:
            del self._days[old]
        return days[twin]

    @contextlib.contextmanager
    def _locked(self):
        if fcntl is None or self.path is None:
            yield
            return
        lock = self.path.with_name(SPEND_LOCK)
        try:
            fd = os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except OSError as exc:
            raise ConfigRefused(f"daily spend lock {lock} unusable ({type(exc).__name__})") from None
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)   # closing releases the lock

    def _read(self) -> dict[str, dict[str, float]]:
        assert self.path is not None
        try:
            st = os.lstat(self.path)
        except FileNotFoundError:
            return {}
        bad = None
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            bad = "is not a plain file (symlink or other)"
        elif hasattr(os, "getuid") and st.st_uid != os.getuid():
            bad = "is not owned by the user running the gateway"
        elif st.st_mode & 0o077:
            bad = "is readable or writable by group/other (want 0600)"
        if bad:
            raise ConfigRefused(f"daily spend file {self.path} {bad}")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            data = None
        days: dict[str, dict[str, float]] = {}
        ok = isinstance(data, dict)
        for day, twins in (data.items() if ok else ()):
            if not (isinstance(day, str) and len(day) == 10 and isinstance(twins, dict)):
                ok = False
                break
            for twin, usd in twins.items():
                if not (isinstance(twin, str) and isinstance(usd, (int, float)) and not isinstance(usd, bool)
                        and math.isfinite(usd) and usd >= 0):
                    ok = False
                    break
                days.setdefault(day, {})[twin] = float(usd)
        if not ok:
            raise ConfigRefused(
                f"daily spend file {self.path} is not valid; it is never reset automatically. "
                "Check it (it should map UTC dates to {twin: usd}), fix or move it aside, then restart")
        return days

    def _write(self) -> None:
        assert self.path is not None
        tmp = self.path.with_name(SPEND_TMP)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._days, fh, sort_keys=True, separators=(",", ":"))
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise SpendPersistError(f"cannot write {self.path} ({type(exc).__name__})") from None
