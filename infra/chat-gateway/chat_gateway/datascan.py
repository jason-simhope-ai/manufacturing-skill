"""Content scan of a data root (`MFG_TEAM_DATA_T1`) before the model may read it (S10). Stdlib only.

The claude-code driver hands the data root to the model with `--add-dir`, and the model's
Read/Grep go straight to the cloud: the gateway's inbound DLP and output filter never see
those files. So the driver scans the tree at startup and before every call:

* every regular file ≤ `MAX_FILE_BYTES` that decodes as text (UTF-8, else Big5/cp950) is run
  through `DLP_PATTERNS` and the local denylist (`sanitize.dlp_hits`, the same view as chat);
  binaries (a NUL byte, or neither encoding decodes) and larger files are listed as unscanned;
* a file is re-read only when its size, mtime, ctime or inode changed since the last scan; the
  result per file is cached in `<state dir>/data-scan.json` (pattern names only, never text),
  keyed by a fingerprint of the pattern set, so a changed denylist rescans everything;
* more than `MAX_FILES` entries, a symlink, or a roster / identity / binding / prompt file is a
  problem (the caller refuses).

It is the same word-and-shape alarm as the chat DLP, not content understanding.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import tier_rank
from .patterns import DLP_PATTERNS, DLP_TIERS
from .sanitize import dlp_hits

MAX_FILES = 5000
MAX_FILE_BYTES = 2_000_000
CACHE_NAME = "data-scan.json"
CACHE_VERSION = 1
FORBIDDEN_NAMES = frozenset({"identities.json", "bindings.json", "roster.json"})
_SNIFF = 8192


@dataclass
class ScanResult:
    files: int = 0
    reread: int = 0
    hits: dict[str, tuple[str, list[str]]] = field(default_factory=dict)   # rel path -> (tier, pattern names)
    fresh: set[str] = field(default_factory=set)                            # rel paths read in this scan
    unscanned: dict[str, str] = field(default_factory=dict)                 # rel path -> "binary" | "large"
    problems: list[tuple[str, str]] = field(default_factory=list)          # (kind, detail)

    def tier_files(self, tier: str) -> list[str]:
        return sorted(rel for rel, (t, _) in self.hits.items() if t == tier)

    @property
    def max_tier(self) -> str | None:
        tiers = [t for t, _ in self.hits.values()]
        return max(tiers, key=tier_rank) if tiers else None

    def summary(self) -> dict:
        return {"files": self.files, "t2_files": len(self.tier_files("T2")), "t3_files": len(self.tier_files("T3")),
                "unscanned": len(self.unscanned)}


def fingerprint(extra: Iterable[tuple[str, re.Pattern]] = ()) -> str:
    """Hash of every pattern that decides a file's tier (built-in DLP + local denylist)."""
    parts = [f"v{CACHE_VERSION}"]
    parts += [f"{n}\x1f{DLP_TIERS[n]}\x1f{p.pattern}\x1f{p.flags}" for n, p in DLP_PATTERNS]
    parts += [f"{n}\x1f{p.pattern}\x1f{p.flags}" for n, p in extra]
    return "sha256:" + hashlib.sha256("\x1e".join(parts).encode("utf-8")).hexdigest()


def _decode(data: bytes) -> str | None:
    if b"\x00" in data[:_SNIFF]:
        return None
    for enc in ("utf-8-sig", "cp950"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def _load_cache(path: Path | None, root: str, fp: str) -> dict:
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("root") != root or data.get("fingerprint") != fp:
        return {}
    files = data.get("files")
    return files if isinstance(files, dict) else {}


def _save_cache(path: Path | None, root: str, fp: str, files: dict) -> None:
    if path is None:
        return
    tmp = path.with_name(path.name + ".tmp")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"v": CACHE_VERSION, "root": root, "fingerprint": fp, "files": files}, fh,
                      ensure_ascii=False, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass                                          # a missing cache only costs a rescan


def scan_tree(root: str, extra: Iterable[tuple[str, re.Pattern]] = (), *, cache_path: Path | None = None,
              max_files: int = MAX_FILES, max_bytes: int = MAX_FILE_BYTES) -> ScanResult:
    """Scan `root` (a realpath). Never follows symlinks; never returns file content."""
    extra = tuple(extra)
    fp = fingerprint(extra)
    cache = _load_cache(cache_path, root, fp)
    res, new_cache = ScanResult(), {}

    def walk_error(exc: OSError) -> None:
        res.problems.append(("unreadable", type(exc).__name__))

    for top, dirs, files in os.walk(root, onerror=walk_error, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            full = os.path.join(top, name)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                res.problems.append(("symlink", rel))
                return res
            if name in files and (name in FORBIDDEN_NAMES or name.endswith(".prompt.md")):
                res.problems.append(("forbidden", name))
                return res
        for name in sorted(files):
            res.files += 1
            if res.files > max_files:
                res.problems.append(("too_many_files", str(max_files)))
                return res
            full = os.path.join(top, name)
            rel = os.path.relpath(full, root)
            try:
                st = os.lstat(full)
            except OSError as exc:
                res.problems.append(("unreadable", type(exc).__name__))
                continue
            key = [st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino]
            entry = cache.get(rel)
            if not (isinstance(entry, dict) and entry.get("k") == key):
                entry = {"k": key, "tier": None, "hits": [], "skip": None}
                if st.st_size > max_bytes:
                    entry["skip"] = "large"
                else:
                    try:
                        with open(full, "rb") as fh:
                            text = _decode(fh.read(max_bytes + 1))
                    except OSError as exc:
                        res.problems.append(("unreadable", type(exc).__name__))
                        continue
                    if text is None:
                        entry["skip"] = "binary"
                    else:
                        found = dlp_hits(text, extra)
                        if found:
                            entry["tier"] = max((t for _, t in found), key=tier_rank)
                            entry["hits"] = sorted({n for n, _ in found})
                res.fresh.add(rel)
                res.reread += 1
            new_cache[rel] = entry
            if entry.get("skip"):
                res.unscanned[rel] = str(entry["skip"])
            elif entry.get("tier"):
                res.hits[rel] = (str(entry["tier"]), list(entry.get("hits") or []))
    _save_cache(cache_path, root, fp, new_cache)
    return res
