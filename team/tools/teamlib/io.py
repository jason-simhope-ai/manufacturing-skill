"""YAML / JSON / date helpers: SafeLoader with duplicate-key rejection and ISO dates,
roster and twin-file loading, frontmatter split, canonical JSON, hashes, small list helpers."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - same convention as _resolve_extends.py
    print("ERROR: PyYAML required. Install with: pip install pyyaml",
          file=sys.stderr)
    sys.exit(2)

from .schema import AUTONOMY, _CJK_RE, _DATE_RE, _FM_RE, LoadError


# --------------------------------------------------------------------------
# YAML loading (SafeLoader; dates -> ISO strings; duplicate keys rejected)
# --------------------------------------------------------------------------

class _Loader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            try:
                if key in seen:
                    raise yaml.constructor.ConstructorError(
                        None, None, f"duplicate key {key!r}",
                        key_node.start_mark)
                seen.add(key)
            except TypeError:
                pass
        return super().construct_mapping(node, deep)


def _construct_timestamp(loader, node):
    try:
        return yaml.SafeLoader.construct_yaml_timestamp(loader, node).isoformat()
    except ValueError:
        # e.g. 2026-02-30: keep the raw string so the schema walker reports E005
        return str(node.value)


_Loader.add_constructor("tag:yaml.org,2002:timestamp", _construct_timestamp)


def yaml_load(text: str) -> Any:
    return yaml.load(text, Loader=_Loader)  # noqa: S506 - SafeLoader subclass


def _yaml_error(e: Exception) -> str:
    return " ".join(str(e).split())[:200]


def load_roster(path) -> dict:
    """Load a roster / overlay YAML file. OSError propagates (exit 2)."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = yaml_load(text)
    except yaml.YAMLError as e:
        raise LoadError("E001", f"YAML parse error: {_yaml_error(e)}")
    if not isinstance(data, dict):
        raise LoadError("E001", "root must be a YAML mapping, got "
                        f"{type(data).__name__}")
    return data


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        raise LoadError("E001", "missing YAML frontmatter block")
    try:
        fm = yaml_load(m.group(1))
    except yaml.YAMLError as e:
        raise LoadError("E001", f"frontmatter YAML parse error: "
                        f"{_yaml_error(e)}")
    if fm is None:
        fm = {}
    if not isinstance(fm, dict):
        raise LoadError("E001", "frontmatter must be a YAML mapping")
    return fm, text[m.end():]


def load_twin(path) -> tuple[dict, str]:
    return split_frontmatter(Path(path).read_text(encoding="utf-8"))



# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _rank(level: str, order: tuple[str, ...]) -> int:
    return order.index(level) if level in order else -1


def _min_level(levels: list[str]) -> str:
    return min(levels, key=lambda lv: AUTONOMY.index(lv))


def _valid_date(s: Any) -> bool:
    if not isinstance(s, str) or not _DATE_RE.match(s):
        return False
    try:
        _dt.date.fromisoformat(s)
    except ValueError:
        return False
    return True


def _date(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def est_tokens(text: str) -> int:
    """Informational estimate: CJK chars + other chars / 4 (spec 10.1)."""
    cjk = len(_CJK_RE.findall(text))
    other = len(text) - cjk
    return cjk + (other + 3) // 4


def canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _posix_rel(root: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return p.name


def _dicts(x: Any) -> list[dict]:
    return [i for i in x if isinstance(i, dict)] if isinstance(x, list) else []


def _strs(x: Any) -> list[str]:
    return [i for i in x if isinstance(i, str)] if isinstance(x, list) else []


def _norm_key(k: str) -> str:
    return re.sub(r"[_\-\s]", "", k).lower()
