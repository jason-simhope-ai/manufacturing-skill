"""Content scan of a data root (`MFG_TEAM_DATA_T1`) before the model may read it (S10). Stdlib only.

The claude-code driver hands the data root to the model with `--add-dir`, and the model's
Read/Grep go straight to the cloud: the gateway's inbound DLP and output filter never see
those files. So the driver scans the tree at startup and before every call:

* every regular file ≤ `MAX_FILE_BYTES` that decodes as text (UTF-16/32 with a BOM, UTF-8, Big5/
  cp950, or UTF-8 with a few stray bytes replaced) is run through `DLP_PATTERNS` and the local
  denylist (`sanitize.dlp_hits`, the same view as chat) and through `DATA_SECRET_PATTERNS`
  (private keys, cloud/chat tokens, `api_key=`; a hit counts as T3);
* document and image formats (PDF, Office/ZIP, OLE, PNG, JPEG …), other binaries (a NUL byte,
  or mostly undecodable bytes) and files over `MAX_FILE_BYTES` are listed as unscanned; the
  caller refuses them unless the operator opted in (`MFG_TEAM_DATA_ALLOW_UNSCANNED=1`);
* anything that is not a regular file or a directory (FIFO, device or other special file) is a
  problem and is never opened (a FIFO would block the scan);
* a file is re-read only when its size, mtime, ctime or inode changed since the last scan; the
  result per file is cached in `<state dir>/data-scan.json` (pattern names only, never text),
  keyed by a fingerprint of the pattern set, so a changed denylist rescans everything;
* more than `MAX_FILES` entries, a symlink, or a roster / identity / binding / prompt file is a
  problem (the caller refuses).

It is the same word-and-shape alarm as the chat DLP, not content understanding.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import tier_rank
from .patterns import DATA_SECRET_PATTERNS, DLP_PATTERNS, DLP_TIERS
from .sanitize import dlp_hits

MAX_FILES = 5000
MAX_FILE_BYTES = 2_000_000
CACHE_NAME = "data-scan.json"
CACHE_VERSION = 2
# Formats the Read tool can render (PDF, images) or that hide text in compressed parts (Office/ZIP):
# never scanned as text, always "binary" (refused by default).
BINARY_MAGIC = (b"%PDF", b"PK\x03\x04", b"PK\x05\x06", b"\xd0\xcf\x11\xe0", b"\x89PNG", b"\xff\xd8\xff",
                b"GIF8", b"RIFF", b"\x1f\x8b", b"7z\xbc\xaf", b"II*\x00", b"MM\x00*")
BINARY_SUFFIXES = frozenset(".pdf .docx .xlsx .pptx .doc .xls .ppt .odt .ods .zip .7z .gz .png .jpg .jpeg "
                            ".gif .webp .bmp .tif .tiff .heic".split())
_BOMS = ((b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
         (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"))
FORBIDDEN_NAMES = frozenset({"identities.json", "bindings.json", "roster.json"})
_SNIFF = 8192


@dataclass
class ScanResult:
    files: int = 0
    reread: int = 0
    hits: dict[str, tuple[str, list[str]]] = field(default_factory=dict)   # rel path -> (tier, pattern names)
    fresh: set[str] = field(default_factory=set)                            # rel paths read in this scan
    unscanned: dict[str, str] = field(default_factory=dict)                 # rel path -> "binary" | "large"
    secrets: dict[str, list[str]] = field(default_factory=dict)             # rel path -> secret pattern names
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
    parts += [f"secret:{n}\x1f{p.pattern}\x1f{p.flags}" for n, p in DATA_SECRET_PATTERNS]
    parts += [f"{n}\x1f{p.pattern}\x1f{p.flags}" for n, p in extra]
    return "sha256:" + hashlib.sha256("\x1e".join(parts).encode("utf-8")).hexdigest()


def _decode(data: bytes, name: str = "") -> list[str] | None:
    """Text views of `data` to scan, or None when it is not text (a binary or document format).

    UTF-16/32 need a BOM. Without one: strict UTF-8, else strict cp950 *and* UTF-8 with errors
    replaced (both views are scanned, so a stray byte cannot hide UTF-8 text behind a lucky cp950
    decode). Mostly undecodable bytes (more than 1% replaced, at least 16) count as binary."""
    if os.path.splitext(name)[1].lower() in BINARY_SUFFIXES or data.startswith(BINARY_MAGIC):
        return None
    for bom, enc in _BOMS:
        if data.startswith(bom):
            return [data.decode(enc, errors="replace")]
    if b"\x00" in data[:_SNIFF]:
        return None
    try:
        return [data.decode("utf-8-sig")]
    except UnicodeDecodeError:
        pass
    views = []
    try:
        views.append(data.decode("cp950"))
    except UnicodeDecodeError:
        pass
    loose = data.decode("utf-8", errors="replace")
    if not views and loose.count("\ufffd") > max(16, len(loose) // 100):
        return None
    return views + [loose]


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


class _NotRegular(Exception):
    """The path stopped being the regular file `lstat` saw (swapped for a FIFO, device or link)."""


def _read_regular(full: str, st: os.stat_result, max_bytes: int) -> bytes:
    """Read up to `max_bytes + 1` bytes of the regular file `lstat` returned as `st`. Opened with
    O_NOFOLLOW | O_NONBLOCK and re-checked with fstat, so a file swapped for a FIFO or a symlink
    between the lstat and the open is never read (and never blocks)."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(full, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise _NotRegular() from None
        raise
    try:
        now = os.fstat(fd)
        if not stat.S_ISREG(now.st_mode) or (now.st_ino, now.st_dev) != (st.st_ino, st.st_dev):
            raise _NotRegular()
        with os.fdopen(fd, "rb") as fh:
            fd = -1
            return fh.read(max_bytes + 1)
    finally:
        if fd >= 0:
            os.close(fd)


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
            if stat.S_ISLNK(st.st_mode):
                res.problems.append(("symlink", rel))
                return res
            if not stat.S_ISREG(st.st_mode):              # FIFO, device, other special file: never opened
                res.problems.append(("special_file", rel))
                return res
            key = [st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_ino]
            entry = cache.get(rel)
            if not (isinstance(entry, dict) and entry.get("k") == key):
                entry = {"k": key, "tier": None, "hits": [], "skip": None}
                if st.st_size > max_bytes:
                    entry["skip"] = "large"
                else:
                    try:
                        data = _read_regular(full, st, max_bytes)
                    except _NotRegular:
                        res.problems.append(("special_file", rel))
                        return res
                    except OSError as exc:
                        res.problems.append(("unreadable", type(exc).__name__))
                        continue
                    views = _decode(data, name)
                    if views is None:
                        entry["skip"] = "binary"
                    else:
                        found = {hit for view in views for hit in dlp_hits(view, extra)}
                        found |= {(f"secret:{n}", "T3") for view in views for n, p in DATA_SECRET_PATTERNS
                                  if p.search(view)}
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
                names = [n for n in res.hits[rel][1] if n.startswith("secret:")]
                if names:
                    res.secrets[rel] = names
    _save_cache(cache_path, root, fp, new_cache)
    return res
