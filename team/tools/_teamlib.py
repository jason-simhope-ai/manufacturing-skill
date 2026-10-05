#!/usr/bin/env python3
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

Runtime: Python 3.11, stdlib only, plus PyYAML (build / validate paths only).
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import fnmatch
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - same convention as _resolve_extends.py
    print("ERROR: PyYAML required. Install with: pip install pyyaml",
          file=sys.stderr)
    sys.exit(2)

VERSION = "0.2.0-alpha"
BUILT_BY = f"teamctl {VERSION}"
TOOL_REPO = Path(__file__).resolve().parents[2]

TIERS = ("T0", "T1", "T2", "T3")
AUTONOMY = ("observe", "suggest", "draft", "act-with-approval", "act")
CATEGORY_VALUES = ("strengthen", "create", "outsource")
GATE_RESULTS = ("twin", "process-fix", "use-command", "defer", "retire")
ADAPTERS = ("mock", "slack", "discord")
ADAPTER_MAX_TIER = {"mock": "T2", "slack": "T1", "discord": "T1"}
TIER_CAP = {"T0": "act", "T1": "act", "T2": "act-with-approval", "T3": "draft"}
CATEGORY_LABEL = {"strengthen": "強化既有優勢", "create": "創造新能力",
                  "outsource": "外包既有工作"}

# Byte budgets (spec section 10.1). BUDGETS is mutable on purpose so unit
# tests can shrink a limit and prove the matching E050 fires.
BUDGETS = {
    "TEAM.md": 6000,
    "roster.example.yaml": 6144,
    "core-rules.md": 4096,
    "twin-file": 6144,
    "roster.json": 4000,
    "roster.json-twin": 600,
    "prompt": 12000,
    "cold-start": 18432,
    "summary": 1200,
    "personal-body": 900,
}

OUTSOURCE_MAX_DAYS = 90
OUTSOURCE_WARN_DAYS = 14
GATE_STALE_DAYS = 120
ACTING_MAX_DAYS = 30
# spec 5.5 (4) / 9.5: the claude-code driver runs with cwd `team/.build/ref/`, so index
# lines read `<kind>/<id>.md` (relative to that directory; nothing above it is reachable).
REF_PREFIX = ""

CODES = {
    "E001": "YAML 解析失敗，或最上層不是 mapping",
    "E002": "未知的 key",
    "E003": "缺少必填欄位（或必填字串為空）",
    "E004": "型別、enum 或參照錯誤（含：id 格式、懸空參照、重複 id）",
    "E005": "預期字串卻得到其他型別，或日期格式不是 YYYY-MM-DD",
    "E010": "incumbent 只能是 LOCAL 或 VACANT",
    "E011": "追蹤檔出現個人識別欄位（name/holder/email/phone/slackId/discordId/employeeId）",
    "E012": "疑似真名（常見姓氏 + 職稱）",
    "E013": "疑似 secret／token",
    "E014": "疑似個資（Mr./Ms.、非 example 網域 email、手機、Slack／Discord id）",
    "E020": "分身檔不存在，或 id 與檔名不符",
    "E021": "分身 id 與 core/profile 的 agent basename 相同",
    "E022": "分身檔出現禁用 key（extends*、*-replace、model、tools）",
    "E023": "compose 的 id 無法在 core + profiles 中解析",
    "E024": "分身檔本文缺必要章節，或安全規則缺固定句關鍵詞",
    "E030": "capability 缺少 category 或值不在 strengthen/create/outsource",
    "E031": "分身檔中的 outsource 未標 dormant: true（或非 outsource 卻標 dormant）",
    "E032": "enableOutsource 缺欄位、approvedBy 不在 escalation（或是本職位）、capability 非 outsource",
    "E033": "outsource reviewBy 超過 90 天；或已過期（--ci 只警告）",
    "E034": "每分身 enabled outsource 超過 1 項",
    "E035": "分身沒有任何 strengthen 或 create 能力",
    "E036": "outsource autonomy 超過 draft",
    "E037": "capability 缺 today 或 humanStillDoes",
    "E038": "strengthen 的 humanStillDoes 只剩審閱／確認／核准／蓋章",
    "E039": "autonomy ≥ suggest 的 capability 缺 decisionPoints",
    "E040": "needsTwinGate.result 不是 twin，卻 enabled: true",
    "E041": "channel tier 超過 adapter 上限（或 SaaS 分級上限）",
    "E042": "channel tier 超過所列分身的 tierCeiling",
    "E043": "T3 規則：追蹤檔不得出現 T3；T3 只能綁 mock、autonomy ≤ draft、cloudTierCeiling 不得為 T3",
    "E044": "roster 的 twin.autonomyCeiling 高於分身檔的 autonomyCeiling",
    "E045": "每人 positions + actingFor 超過 2",
    "E046": "personal overlay 出現白名單以外的欄位",
    "E047": "alpha 上限：policy.cloudTierCeiling／saasTierCeiling 不得高於 T1（雲端模型與 SaaS 聊天只到 T1）",
    "E050": "超過 bytes 預算",
    "E051": "build 不確定（兩次輸出不同）",
    "E060": ".gitignore 缺必要項目，或追蹤檔含 *.local.*／team/.build／team/local",
    "W001": "autonomy act-with-approval／act：lint 接受，但 gateway 拒載",
    "W002": "outsource 14 天內到期",
    "W003": "已啟用 outsource（每項一則提醒）",
    "W004": "needsTwinGate 超過 120 天未複審",
    "W005": "compose.optional 的 profile 未啟用，已略過",
    "W006": "agent 本文過大，改為索引行而非內嵌",
    "W007": "本機 roster.json 超過 4,000 B 總量",
    "W008": "roster.json 單一分身項目超過 600 B（只有 --ci 檢查範例 roster 時是 E050）",
}

REQUIRED_GITIGNORE = (
    "team/local/*", "!team/local/README.md", "!team/local/.gitkeep",
    "team/.build/", "*.local.yaml", "*.local.md", "logs/", "**/audit/",
    "**/memory/",
)

REQUIRED_SECTIONS = ("## 角色定位", "## 你會做的事", "## 決策點（永遠交還人類）",
                     "## 你不會做的事", "## 安全規則", "## 回覆格式")
# Keyword stems of the five fixed sentences (spec 11.5).
SAFETY_KEYWORDS = ("不執行", "已被核准", "system prompt", "沒有工具結果",
                   "往上一級")

IDENTITY_KEYS = {"name", "holder", "email", "phone", "slackid", "discordid",
                 "employeeid"}

_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
# Capability ids may start with a digit (the spec's own examples are
# `8d-challenge` and `8d-formatting`); every other id must start with a letter.
_CAPID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
_CJK_RE = re.compile(r"[　-〿㐀-鿿＀-￯]")


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Finding:
    code: str
    severity: str   # "error" | "warning"
    path: str
    message: str

    def render(self) -> str:
        kind = "error" if self.severity == "error" else "warning"
        msg = " ".join(self.message.split())
        return f"::{kind} file={self.path}::{self.code}: {msg}"


class LoadError(Exception):
    """A file could not be parsed; carries the finding code (E001)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class BuildError(Exception):
    def __init__(self, findings: list[Finding]):
        super().__init__("; ".join(f"{f.code}: {f.message}" for f in findings))
        self.findings = findings


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


# --------------------------------------------------------------------------
# Schema walker
# --------------------------------------------------------------------------
# A schema is {key: (type, required)}. `required` is False, True (-> E003) or
# a code string (e.g. "E032"/"E037") used when the field is missing/empty.
# Types: "str","int","bool","id","tier","autonomy","date","askers","any",
# ("enum", values), ("list", itemtype), ("map", schema).

def _check_value(add, val, typ, loc, unknown_code="E002"):
    if isinstance(typ, str):
        if typ == "any":
            return
        if typ in ("str", "id", "capid", "tier", "autonomy", "date"):
            if not isinstance(val, str):
                add("E005", f"{loc}: expected a string, got "
                    f"{type(val).__name__} ({val!r}); quote the value")
                return
            if typ == "id" and not _ID_RE.match(val):
                add("E004", f"{loc}: {val!r} is not a valid id "
                    "(^[a-z][a-z0-9-]{1,40}$)")
            elif typ == "capid" and not _CAPID_RE.match(val):
                add("E004", f"{loc}: {val!r} is not a valid capability id "
                    "(^[a-z0-9][a-z0-9-]{1,40}$)")
            elif typ == "tier" and val not in TIERS:
                add("E004", f"{loc}: {val!r} is not a tier (T0|T1|T2|T3)")
            elif typ == "autonomy" and val not in AUTONOMY:
                add("E004", f"{loc}: {val!r} is not an autonomy level")
            elif typ == "date" and not _valid_date(val):
                add("E005", f"{loc}: {val!r} is not a YYYY-MM-DD date")
        elif typ == "int":
            if isinstance(val, bool) or not isinstance(val, int):
                add("E004", f"{loc}: expected an integer, got {val!r}")
        elif typ == "bool":
            if not isinstance(val, bool):
                add("E004", f"{loc}: expected a boolean, got {val!r}")
        elif typ == "askers":
            if val == "members":
                return
            if not isinstance(val, list):
                add("E004", f"{loc}: expected 'members' or a list of ids")
                return
            for i, item in enumerate(val):
                _check_value(add, item, "id", f"{loc}[{i}]")
        return
    kind = typ[0]
    if kind == "enum":
        if not isinstance(val, str):
            add("E005", f"{loc}: expected a string, got {val!r}")
        elif val not in typ[1]:
            add("E004", f"{loc}: {val!r} not in {'|'.join(typ[1])}")
    elif kind == "list":
        if not isinstance(val, list):
            add("E004", f"{loc}: expected a list, got {type(val).__name__}")
            return
        for i, item in enumerate(val):
            _check_value(add, item, typ[1], f"{loc}[{i}]", unknown_code)
    elif kind == "map":
        if not isinstance(val, dict):
            add("E004", f"{loc}: expected a mapping, got {type(val).__name__}")
            return
        _check_map(add, val, typ[1], loc, unknown_code)


def _check_map(add, obj, schema, loc, unknown_code="E002", twin_top=False):
    for k in obj:
        ks = str(k)
        if _norm_key(ks) in IDENTITY_KEYS:
            continue  # reported once by _scan_forbidden (E011)
        if twin_top and (ks.startswith("extends") or ks.endswith("-replace")
                         or ks in ("model", "tools")):
            add("E022", f"{loc}: forbidden key {ks!r} in a twin file")
            continue
        if ks not in schema:
            add(unknown_code, f"{loc}: unknown key {ks!r}")
    for key, (typ, req) in schema.items():
        if key not in obj:
            if req:
                add(req if isinstance(req, str) else "E003",
                    f"{loc}.{key} is required")
            continue
        val = obj[key]
        if req and typ == "str" and isinstance(val, str) and not val.strip():
            add(req if isinstance(req, str) else "E003",
                f"{loc}.{key} must not be empty")
            continue
        _check_value(add, val, typ, f"{loc}.{key}", unknown_code)


def _scan_forbidden(add, obj, loc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _norm_key(str(k)) in IDENTITY_KEYS:
                add("E011", f"{loc}: personal-identity key {str(k)!r} is not "
                    "allowed in tracked files")
            _scan_forbidden(add, v, f"{loc}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scan_forbidden(add, v, f"{loc}[{i}]")


_ORG = {"id": ("id", True), "displayName": ("str", True),
        "timezone": ("str", True)}
_POLICY = {"saasTierCeiling": ("tier", True), "cloudTierCeiling": ("tier", True),
           "autonomyCeiling": ("autonomy", True), "channelWindow": ("int", False)}
_DEPT = {"id": ("id", True), "title": ("str", True), "head": ("id", True),
         "escalation": (("list", "id"), True)}
_GATE = {"result": (("enum", GATE_RESULTS), True), "rationale": ("str", True),
         "reviewedOn": ("date", True)}
_OUTSOURCE = {"capability": ("capid", "E032"), "approvedBy": ("id", "E032"),
              "reason": ("str", "E032"), "reviewBy": ("date", "E032"),
              "manualRepsPerMonth": ("int", "E032")}
_TWIN_REF = {"enabled": ("bool", True), "file": ("id", True),
             "autonomyCeiling": ("autonomy", True),
             "needsTwinGate": (("map", _GATE), True),
             "disable": (("list", "capid"), False),
             "enableOutsource": (("list", ("map", _OUTSOURCE)), False)}
_POSITION = {"id": ("id", True), "department": ("id", True),
             "title": ("str", True), "incumbent": ("any", True),
             "twin": (("map", _TWIN_REF), False)}
_CHANNEL = {"id": ("id", True), "department": ("id", True),
            "tier": ("tier", True), "adapter": (("enum", ADAPTERS), True),
            "twins": (("list", "id"), True), "defaultTwin": ("id", True),
            "autonomyCeiling": ("autonomy", True), "askers": ("askers", True),
            "requesters": (("list", "id"), False),
            "approvers": (("list", "id"), False)}


def _roster_schema(example: bool) -> dict:
    return {"schema": ("int", True), "synthetic": ("bool", example),
            "org": (("map", _ORG), True), "profiles": (("list", "id"), True),
            "policy": (("map", _POLICY), True),
            "departments": (("list", ("map", _DEPT)), True),
            "positions": (("list", ("map", _POSITION)), True),
            "channels": (("list", ("map", _CHANNEL)), True)}


_CAP = {"id": ("capid", True), "summary": ("str", True),
        "category": ("any", False),  # checked by check_caps (E030)
        "autonomy": ("autonomy", True), "today": ("str", "E037"),
        "humanStillDoes": ("str", "E037"),
        "decisionPoints": (("list", "str"), False),
        "predictFirstEligible": ("bool", False), "dormant": ("bool", False)}
_COMPOSE = {"agent": ("str", False), "skills": (("list", "str"), True),
            "knowHow": (("list", "str"), True), "hooks": (("list", "str"), True),
            "optional": (("list", "str"), False)}
_SCHEDULE = {"capability": ("capid", True), "cron": ("str", True),
             "channel": ("id", True)}
_TWIN = {"kind": (("enum", ("twin",)), True), "schemaVersion": ("int", True),
         "id": ("id", True), "title": ("str", True),
         "description": ("str", True), "department": ("id", True),
         "aliases": (("list", "str"), False), "tierCeiling": ("tier", True),
         "autonomyCeiling": ("autonomy", True),
         "decisionRights": (("list", "str"), True),
         "compose": (("map", _COMPOSE), True),
         "capabilities": (("list", ("map", _CAP)), True),
         "schedule": (("list", ("map", _SCHEDULE)), False)}

_PERSONAL = {"tone": (("enum", ("formal", "concise")), False),
             "digestFormat": (("enum", ("bullets", "table")), False),
             "aliases": (("list", "str"), False),
             "retention": (("map", {"predictFirst": ("bool", False),
                                    "teachBack": ("bool", False)}), False)}
_IDENTITY_FILE = {"schema": ("int", False), "users": (("list", ("map", {
    "platform": (("enum", ("slack", "discord", "mock")), True),
    "userId": ("str", True), "positions": (("list", "id"), True),
    "actingFor": (("list", ("map", {"role": ("id", True),
                                    "until": ("date", True),
                                    "grantedBy": ("id", True)})), False)})), True)}

# --------------------------------------------------------------------------
# Heuristic scanners (spec 11.4)
# --------------------------------------------------------------------------
# Every regex lives in infra/chat-gateway/chat_gateway/patterns.py (stdlib `re`
# only); it is loaded from this tool's own repository by file path, so mini repos
# in tests and repos without the gateway package on sys.path work the same.

_PATTERNS_FILE = TOOL_REPO / "infra" / "chat-gateway" / "chat_gateway" / "patterns.py"


def _load_patterns():
    try:
        spec = importlib.util.spec_from_file_location("_gw_patterns_for_teamlib",
                                                      _PATTERNS_FILE)
        if spec is None or spec.loader is None:
            raise ImportError(str(_PATTERNS_FILE))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # pure regex module
        return mod
    except (ImportError, OSError) as e:
        raise ImportError(
            "team tools need infra/chat-gateway/chat_gateway/patterns.py (the single "
            f"source of the secret/name/DLP regexes); not found or unreadable: {e}") from None


_PAT = _load_patterns()
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = list(_PAT.SECRET_PATTERNS)
_GENERIC_SECRET = _PAT.REPO_GENERIC_SECRET[1]
NAME_ZH = _PAT.NAME_ZH
NAME_OTHER: list[tuple[str, re.Pattern]] = list(_PAT.NAME_OTHER)
_EMAIL, _EMAIL_OK = _PAT.EMAIL, _PAT.EMAIL_OK
PII_PATTERNS: list[tuple[str, re.Pattern]] = list(_PAT.PII_PATTERNS)
_tw_business_id_ok = _PAT.valid_ubn


def dlp_scan(text: str) -> list[str]:
    """DLP classes (patterns.DLP_PATTERNS names) that match `text`; never the values."""
    hits = []
    for name, pat in _PAT.DLP_PATTERNS:
        for m in pat.finditer(text):
            if name != "tw-ubn" or _PAT.valid_ubn(m.group(0)):
                hits.append(name)
                break
    return hits


def shared_secret_patterns(root: Path) -> list[tuple[str, re.Pattern]]:
    """Kept for callers; the patterns no longer depend on the scanned repo."""
    return SECRET_PATTERNS


def load_lint_allow(root: Path) -> tuple[list[re.Pattern], list[str]]:
    """lint-allow.txt: one regex per line with a mandatory `# reason`."""
    p = root / "team" / "tools" / "lint-allow.txt"
    pats, problems = [], []
    if not p.is_file():
        return pats, problems
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        rx, sep, reason = s.rpartition(" # ")
        if not sep or not reason.strip() or not rx.strip():
            problems.append(f"line {n}: missing '# reason'")
            continue
        try:
            pats.append(re.compile(rx.strip()))
        except re.error as e:
            problems.append(f"line {n}: bad regex ({e})")
    return pats, problems


# --------------------------------------------------------------------------
# Effective autonomy (spec 6)
# --------------------------------------------------------------------------

def effective_autonomy(cap: dict, twin: dict, position: dict, policy: dict,
                       channel: dict) -> str:
    """min(capability, twin file, roster twin, policy, channel, tier cap),
    then outsource <= draft and VACANT -> observe.

    requesterCap (askers -> draft) and the per-turn `tainted` clamp are
    applied by the gateway at runtime; they depend on the live event.
    """
    levels = [cap.get("autonomy", "observe")]
    for v in (twin.get("autonomyCeiling"),
              (position.get("twin") or {}).get("autonomyCeiling"),
              policy.get("autonomyCeiling"), channel.get("autonomyCeiling")):
        if v in AUTONOMY:
            levels.append(v)
    levels.append(TIER_CAP.get(channel.get("tier", "T1"), "draft"))
    if cap.get("category") == "outsource":
        levels.append("draft")
    if position.get("incumbent") == "VACANT":
        levels.append("observe")
    return _min_level([lv for lv in levels if lv in AUTONOMY])


# --------------------------------------------------------------------------
# Validator
# --------------------------------------------------------------------------

_REVIEW_WORDS = ("審閱", "確認", "核准", "蓋章", "審核", "簽核", "最終")
_FILLER_RE = re.compile(r"[\s、，,。;；/及與和或並後再\-—]+")


def _only_review(text: str) -> bool:
    rest = text
    hit = False
    for w in _REVIEW_WORDS:
        if w in rest:
            hit = True
            rest = rest.replace(w, "")
    rest = _FILLER_RE.sub("", rest)
    return hit and len(rest) <= 2


class _Validator:
    def __init__(self, root: Path, roster_path, mode: str, today: str):
        if mode not in ("ci", "local", "strict"):
            raise ValueError(f"unknown mode {mode!r}")
        self.root = Path(root).resolve()
        self.roster_path = Path(roster_path).resolve()
        self.mode = mode
        self.today = _date(today)
        self.findings: list[Finding] = []
        self.seen: set = set()
        self.roster: dict | None = None
        self.twins: dict[str, dict] = {}
        self.profiles_active: list[str] = []
        self.is_example = ".example." in self.roster_path.name
        self.plugin_profiles: list[str] = []
        self.stats: dict = {"outsource_enabled": 0, "outsource_dormant": 0,
                            "budget_rows": [], "twins_enabled": 0}
        self.declared_enabled: set[str] = set()
        self.files: list[str] = []
        self.tracked: set[str] | None = None

    # -- plumbing ---------------------------------------------------------
    def rel(self, p) -> str:
        return _posix_rel(self.root, Path(p)) if not isinstance(p, str) else p

    def add(self, code, path, msg, severity="error"):
        key = (code, self.rel(path), msg)
        if key in self.seen:
            return
        self.seen.add(key)
        self.findings.append(Finding(code, severity, self.rel(path), msg))

    def adder(self, path):
        return lambda code, msg, severity="error": self.add(
            code, path, msg, severity)

    def n_errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    # -- main -------------------------------------------------------------
    def run(self):
        self.load_plugin()
        self.check_required_files()
        self.load_roster_file()
        if self.roster is not None:
            self.check_roster_struct()
        self.load_twin_files()
        if self.roster is not None:
            self.check_roster_xrefs()
        if self.mode != "ci" and self.roster is not None:
            self.check_overlays()
        self.check_hygiene()
        self.check_budgets()
        return self.findings, self.stats

    # -- inputs -----------------------------------------------------------
    def load_plugin(self):
        p = self.root / "plugin.json"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            self.plugin_profiles = _strs(data["profiles"]["available"])
        except (OSError, ValueError, KeyError, TypeError):
            self.add("E003", p, "plugin.json missing or has no "
                     "profiles.available list")

    def check_required_files(self):
        for rel in ("TEAM.md", "team/policies/core-rules.md",
                    "team/policies/restricted.md", "team/gate/need-a-twin.md",
                    "team/twins/_template.md"):
            if not (self.root / rel).is_file():
                self.add("E003", rel, "required team file is missing")

    def load_roster_file(self):
        try:
            self.roster = load_roster(self.roster_path)
        except LoadError as e:
            self.add(e.code, self.roster_path, e.message)
            self.roster = None
            self.profiles_active = list(self.plugin_profiles)
            return
        self.profiles_active = _strs(self.roster.get("profiles"))

    # -- roster structure -------------------------------------------------
    def check_roster_struct(self):
        r, path = self.roster, self.roster_path
        add = self.adder(path)
        _scan_forbidden(add, r, "roster")
        _check_map(add, r, _roster_schema(self.is_example), "roster")
        if r.get("schema") != 1 and isinstance(r.get("schema"), int):
            add("E004", "roster.schema must be 1")
        if self.is_example and r.get("synthetic") is False:
            add("E004", "roster.synthetic must be true in an example roster")
        for p in _strs(r.get("profiles")):
            if self.plugin_profiles and p not in self.plugin_profiles:
                add("E004", f"roster.profiles: {p!r} is not in plugin.json "
                    "profiles.available")
        cw = (r.get("policy") or {}).get("channelWindow") if isinstance(
            r.get("policy"), dict) else None
        if isinstance(cw, int) and not isinstance(cw, bool) and not 1 <= cw <= 20:
            add("E004", "roster.policy.channelWindow must be within 1..20")
        for i, pos in enumerate(_dicts(r.get("positions"))):
            if "incumbent" in pos and pos["incumbent"] not in ("LOCAL", "VACANT"):
                add("E010", f"positions[{i}].incumbent must be LOCAL or "
                    f"VACANT, got {pos['incumbent']!r}")
        for coll in ("departments", "positions", "channels"):
            seen = set()
            for i, item in enumerate(_dicts(r.get(coll))):
                ident = item.get("id")
                if isinstance(ident, str):
                    if ident in seen:
                        add("E004", f"{coll}[{i}].id {ident!r} is duplicated")
                    seen.add(ident)

    # -- twin files -------------------------------------------------------
    def agent_basenames(self) -> set[str]:
        names = set()
        for d in [self.root / "core" / "agents"] + sorted(
                (self.root / "profiles").glob("*/agents")):
            if d.is_dir():
                names |= {f.stem for f in d.glob("*.md")
                          if not f.name.startswith("_")}
        return names

    def resolve_id(self, kind_dir: str, ident: str) -> Path | None:
        return find_ref(self.root, kind_dir, ident, self.profiles_active)

    def load_twin_files(self):
        tdir = self.root / "team" / "twins"
        if not tdir.is_dir():
            return
        agents = self.agent_basenames()
        for p in sorted(tdir.glob("*.md")):
            template = p.name.startswith("_")
            try:
                fm, body = load_twin(p)
            except LoadError as e:
                self.add(e.code, p, e.message)
                continue
            self.check_twin_file(p, fm, body, template, agents)
            if not template and isinstance(fm.get("id"), str):
                self.twins[p.stem] = {"fm": fm, "body": body, "path": p}

    def check_twin_file(self, p, fm, body, template, agents):
        add = self.adder(p)
        _scan_forbidden(add, fm, "twin")
        _check_map(add, fm, _TWIN, "twin", twin_top=True)
        stem = p.stem
        tid = fm.get("id")
        if not template and isinstance(tid, str) and tid != stem:
            add("E020", f"twin id {tid!r} does not match file name {stem!r}")
        if not template and isinstance(tid, str) and tid in agents:
            add("E021", f"twin id {tid!r} collides with an agent basename")
        if isinstance(fm.get("schemaVersion"), int) and fm["schemaVersion"] != 1:
            add("E004", "twin.schemaVersion must be 1")
        if isinstance(fm.get("decisionRights"), list) and not fm["decisionRights"]:
            add("E003", "twin.decisionRights needs at least one entry")
        if (self.roster is not None and not template
                and isinstance(fm.get("department"), str)):
            depts = {d.get("id") for d in _dicts(self.roster.get("departments"))}
            if depts and fm["department"] not in depts:
                add("E004", f"twin.department {fm['department']!r} is not a "
                    "roster department")
        self.check_compose(add, fm)
        self.check_caps(add, fm)
        self.check_schedule(add, fm, template)
        self.check_body(add, body)
        if fm.get("tierCeiling") in TIERS and fm["tierCeiling"] == "T3":
            self.check_t3_twin(add, fm, template)
        if fm.get("autonomyCeiling") in ("act-with-approval", "act"):
            add("W001", f"twin.autonomyCeiling is {fm['autonomyCeiling']!r}: "
                "accepted by lint, refused by the gateway", "warning")

    def check_compose(self, add, fm):
        comp = fm.get("compose")
        if not isinstance(comp, dict):
            return
        agent = comp.get("agent")
        if isinstance(agent, str) and not self.resolve_id("agents", agent):
            add("E023", f"compose.agent {agent!r} not found in core/profiles")
        for key, kdir in (("skills", "skills"), ("knowHow", "know-how"),
                          ("hooks", "hooks")):
            for ident in _strs(comp.get(key)):
                if not self.resolve_id(kdir, ident):
                    add("E023", f"compose.{key} {ident!r} not found in "
                        "core/profiles")
        for ent in _strs(comp.get("optional")):
            prof, sep, ident = ent.partition(":")
            if not sep or not prof or not ident:
                add("E004", f"compose.optional {ent!r} must look like "
                    "'profile:id'")
                continue
            if prof not in self.profiles_active:
                add("W005", f"compose.optional {ent!r}: profile {prof!r} is "
                    "not active, skipped", "warning")
                continue
            if not any(find_ref(self.root, k, ident, [prof])
                       for k in ("agents", "skills", "know-how", "hooks")):
                add("E023", f"compose.optional {ent!r} not found in profile")

    def check_caps(self, add, fm):
        caps = fm.get("capabilities")
        if not isinstance(caps, list):
            return
        if not caps:
            add("E003", "twin.capabilities needs at least one entry")
        seen, cats = set(), []
        for i, cap in enumerate(caps):
            if not isinstance(cap, dict):
                continue
            loc = f"capabilities[{i}]({cap.get('id')})"
            cat = cap.get("category")
            if not isinstance(cat, str) or cat not in CATEGORY_VALUES:
                add("E030", f"{loc}.category must be one of "
                    f"{'|'.join(CATEGORY_VALUES)}, got {cat!r}")
            else:
                cats.append(cat)
            cid = cap.get("id")
            if isinstance(cid, str):
                if cid in seen:
                    add("E004", f"{loc}: duplicate capability id")
                seen.add(cid)
            aut = cap.get("autonomy")
            if aut in ("act-with-approval", "act"):
                add("W001", f"{loc}.autonomy {aut!r}: accepted by lint, "
                    "refused by the gateway", "warning")
            if aut in AUTONOMY and AUTONOMY.index(aut) >= 1:
                dp = cap.get("decisionPoints")
                if not (isinstance(dp, list) and dp):
                    add("E039", f"{loc}: autonomy {aut!r} needs at least one "
                        "decisionPoint")
            if cat == "outsource":
                if cap.get("dormant") is not True:
                    add("E031", f"{loc}: outsource must be dormant: true in "
                        "a twin file (only the roster may wake it)")
                if aut in AUTONOMY and AUTONOMY.index(aut) > AUTONOMY.index("draft"):
                    add("E036", f"{loc}: outsource autonomy {aut!r} exceeds "
                        "draft")
            elif "dormant" in cap:
                add("E004", f"{loc}.dormant is only valid on outsource "
                    "capabilities")
            if cat == "strengthen" and isinstance(cap.get("humanStillDoes"), str):
                if cap["humanStillDoes"].strip() and _only_review(
                        cap["humanStillDoes"]):
                    add("E038", f"{loc}.humanStillDoes only says "
                        "review/confirm/approve/stamp; state what the human "
                        "still does by hand")
        if cats and not any(c in ("strengthen", "create") for c in cats):
            add("E035", "twin has no strengthen or create capability")

    def check_schedule(self, add, fm, template):
        caps = {c.get("id") for c in _dicts(fm.get("capabilities"))}
        for i, s in enumerate(_dicts(fm.get("schedule"))):
            if isinstance(s.get("capability"), str) and s["capability"] not in caps:
                add("E004", f"schedule[{i}].capability {s['capability']!r} is "
                    "not a capability of this twin")
            cron = s.get("cron")
            if isinstance(cron, str) and len(cron.split()) != 5:
                add("E004", f"schedule[{i}].cron must have 5 fields")
            if self.roster is not None and not template and isinstance(
                    s.get("channel"), str):
                chans = {c.get("id") for c in _dicts(self.roster.get("channels"))}
                if s["channel"] not in chans:
                    add("E004", f"schedule[{i}].channel {s['channel']!r} is "
                        "not a roster channel")

    def check_body(self, add, body):
        for sec in REQUIRED_SECTIONS:
            if not re.search(rf"^{re.escape(sec)}\s*$", body, re.M):
                add("E024", f"missing required section {sec!r}")
        m = re.search(r"^## 安全規則\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
        if m:
            seg = m.group(1)
            for kw in SAFETY_KEYWORDS:
                if kw.lower() not in seg.lower():
                    add("E024", f"安全規則 lacks fixed-sentence keyword {kw!r}")

    def check_t3_twin(self, add, fm, template):
        if self.mode in ("ci", "strict"):
            add("E043", "tierCeiling T3: T3 twins are refused in tracked "
                "manifests (alpha refuses T3; see team/policies/restricted.md)")
        elif fm.get("autonomyCeiling") in AUTONOMY and AUTONOMY.index(
                fm["autonomyCeiling"]) > AUTONOMY.index("draft"):
            add("E043", "T3 twin autonomyCeiling must be <= draft")

    # -- roster cross references ------------------------------------------
    def check_roster_xrefs(self):
        r, path = self.roster, self.roster_path
        add = self.adder(path)
        depts = {d["id"]: d for d in _dicts(r.get("departments"))
                 if isinstance(d.get("id"), str)}
        positions = {p["id"]: p for p in _dicts(r.get("positions"))
                     if isinstance(p.get("id"), str)}
        policy = r.get("policy") if isinstance(r.get("policy"), dict) else {}

        for d in depts.values():
            if isinstance(d.get("head"), str) and d["head"] not in positions:
                add("E004", f"department {d['id']!r}: head {d['head']!r} is "
                    "not a position")
            for e in _strs(d.get("escalation")):
                if e not in positions:
                    add("E004", f"department {d['id']!r}: escalation id "
                        f"{e!r} is not a position")
        for p in positions.values():
            if isinstance(p.get("department"), str) and p["department"] not in depts:
                add("E004", f"position {p['id']!r}: department "
                    f"{p['department']!r} not defined")

        # policy
        for key in ("autonomyCeiling",):
            if policy.get(key) in ("act-with-approval", "act"):
                add("W001", f"policy.{key} is {policy[key]!r}: accepted by "
                    "lint, refused by the gateway", "warning")
        if policy.get("cloudTierCeiling") == "T3":
            add("E043", "policy.cloudTierCeiling must not be T3")
        if policy.get("saasTierCeiling") == "T3" and self.mode in ("ci", "strict"):
            add("E043", "policy.saasTierCeiling must not be T3")
        for key in ("cloudTierCeiling", "saasTierCeiling"):
            val = policy.get(key)
            t3_flagged = val == "T3" and (key == "cloudTierCeiling" or self.mode in ("ci", "strict"))
            if val in TIERS and _rank(val, TIERS) > _rank("T1", TIERS) and not t3_flagged:
                add("E047", f"policy.{key} is {val}: alpha caps cloud models and SaaS chat at T1 "
                    "(no waiver; T2 off-premises is deferred, spec 14)")

        # twins attached to positions
        enabled_twins: dict[str, dict] = {}
        used_files: dict[str, str] = {}
        aliases: dict[str, str] = {}
        for pos in positions.values():
            tw = pos.get("twin")
            if not isinstance(tw, dict):
                continue
            self.check_position_twin(add, pos, tw, depts, used_files,
                                     enabled_twins, policy)
        for tid, t in enabled_twins.items():
            for al in _strs(t["fm"].get("aliases")):
                if al in aliases and aliases[al] != tid or al in self.twins:
                    add("E004", f"alias {al!r} of twin {tid!r} collides with "
                        "another twin id/alias")
                aliases[al] = tid
        self.stats["twins_enabled"] = len(enabled_twins)

        # channels
        for i, ch in enumerate(_dicts(r.get("channels"))):
            self.check_channel(add, i, ch, depts, positions, enabled_twins,
                               policy)

    def check_position_twin(self, add, pos, tw, depts, used_files,
                            enabled_twins, policy):
        pid = pos.get("id")
        loc = f"positions[{pid}].twin"
        fid = tw.get("file")
        tf = self.twins.get(fid) if isinstance(fid, str) else None
        if isinstance(fid, str):
            if tf is None:
                add("E020", f"{loc}.file: team/twins/{fid}.md does not exist "
                    "or is not a valid twin file")
            else:
                if fid in used_files:
                    add("E004", f"{loc}.file {fid!r} is already used by "
                        f"position {used_files[fid]!r}")
                used_files[fid] = pid
                if tf["fm"].get("department") != pos.get("department"):
                    add("E004", f"{loc}: twin department "
                        f"{tf['fm'].get('department')!r} != position "
                        f"department {pos.get('department')!r}")
        # ceilings
        mine, theirs = tw.get("autonomyCeiling"), (tf or {}).get(
            "fm", {}).get("autonomyCeiling")
        if mine in AUTONOMY and theirs in AUTONOMY and AUTONOMY.index(
                mine) > AUTONOMY.index(theirs):
            add("E044", f"{loc}.autonomyCeiling {mine!r} exceeds the twin "
                f"file's autonomyCeiling {theirs!r}")
        if mine in ("act-with-approval", "act"):
            add("W001", f"{loc}.autonomyCeiling is {mine!r}: accepted by "
                "lint, refused by the gateway", "warning")
        # gate
        gate = tw.get("needsTwinGate")
        if isinstance(gate, dict):
            if tw.get("enabled") is True and gate.get("result") in GATE_RESULTS \
                    and gate["result"] != "twin":
                add("E040", f"{loc}: enabled twin needs needsTwinGate.result "
                    f"'twin', got {gate['result']!r}")
            ro = gate.get("reviewedOn")
            if _valid_date(ro) and (self.today - _date(ro)).days > GATE_STALE_DAYS:
                add("W004", f"{loc}.needsTwinGate.reviewedOn {ro} is more "
                    f"than {GATE_STALE_DAYS} days old", "warning")
        if tw.get("enabled") is True and isinstance(fid, str):
            self.declared_enabled.add(fid)
            if tf is not None:
                enabled_twins[fid] = tf
        # disable / outsource
        caps = {c.get("id"): c for c in _dicts((tf or {}).get(
            "fm", {}).get("capabilities"))}
        for cid in _strs(tw.get("disable")):
            if tf is not None and cid not in caps:
                add("E004", f"{loc}.disable: {cid!r} is not a capability of "
                    f"twin {fid!r}")
        self.check_outsource(add, pos, tw, tf, caps, loc, depts)

    def check_outsource(self, add, pos, tw, tf, caps, loc, depts):
        entries = _dicts(tw.get("enableOutsource"))
        if isinstance(tw.get("enableOutsource"), list) and len(
                tw["enableOutsource"]) > 1:
            add("E034", f"{loc}: at most one enableOutsource entry per twin, "
                f"got {len(tw['enableOutsource'])}")
        esc = _strs((depts.get(pos.get("department")) or {}).get("escalation"))
        enabled_here = 0
        for i, e in enumerate(entries):
            eloc = f"{loc}.enableOutsource[{i}]"
            cid = e.get("capability")
            if isinstance(cid, str) and tf is not None:
                cap = caps.get(cid)
                if cap is None or cap.get("category") != "outsource":
                    add("E032", f"{eloc}.capability {cid!r} is not an "
                        "outsource capability of this twin")
                else:
                    enabled_here += 1
            ab = e.get("approvedBy")
            if isinstance(ab, str):
                if ab not in esc:
                    add("E032", f"{eloc}.approvedBy {ab!r} is not in the "
                        "department escalation ladder")
                if ab == pos.get("id"):
                    add("E032", f"{eloc}.approvedBy must not be the twin's "
                        "own position")
            mr = e.get("manualRepsPerMonth")
            if isinstance(mr, int) and not isinstance(mr, bool) and mr < 1:
                add("E032", f"{eloc}.manualRepsPerMonth must be >= 1")
            rb = e.get("reviewBy")
            if _valid_date(rb):
                delta = (_date(rb) - self.today).days
                if delta > OUTSOURCE_MAX_DAYS:
                    add("E033", f"{eloc}.reviewBy {rb} is {delta} days away "
                        f"(max {OUTSOURCE_MAX_DAYS})")
                elif delta < 0:
                    add("E033", f"{eloc}.reviewBy {rb} has expired",
                        "warning" if self.mode == "ci" else "error")
                elif delta <= OUTSOURCE_WARN_DAYS:
                    add("W002", f"{eloc}.reviewBy {rb} is due in {delta} "
                        "days", "warning")
            add("W003", f"outsource enabled: twin {tw.get('file')!r} "
                f"capability {cid!r} (manual practice and teach-back "
                "are mandatory)", "warning")
        if tw.get("enabled") is True and tf is not None:
            outs = [c for c in caps.values() if c.get("category") == "outsource"]
            en = enabled_here
            self.stats["outsource_enabled"] += en
            self.stats["outsource_dormant"] += max(len(outs) - en, 0)

    def check_channel(self, add, i, ch, depts, positions, enabled_twins, policy):
        cid = ch.get("id")
        loc = f"channels[{cid or i}]"
        tier, adapter = ch.get("tier"), ch.get("adapter")
        if isinstance(ch.get("department"), str) and ch["department"] not in depts:
            add("E004", f"{loc}.department {ch['department']!r} not defined")
        # T3 is governed by E043 below (mock max_tier is T2, yet lint allows a
        # local T3-on-mock manifest), so E041 only covers T0..T2 channels.
        if tier in TIERS and tier != "T3" and adapter in ADAPTER_MAX_TIER:
            if TIERS.index(tier) > TIERS.index(ADAPTER_MAX_TIER[adapter]):
                add("E041", f"{loc}: tier {tier} exceeds the {adapter} "
                    f"adapter maximum {ADAPTER_MAX_TIER[adapter]}")
            elif adapter != "mock" and policy.get("saasTierCeiling") in TIERS \
                    and TIERS.index(tier) > TIERS.index(policy["saasTierCeiling"]):
                add("E041", f"{loc}: tier {tier} exceeds policy."
                    f"saasTierCeiling {policy['saasTierCeiling']}")
        twins = _strs(ch.get("twins"))
        for t in twins:
            if t not in enabled_twins:
                if t not in self.declared_enabled:  # else E020 already raised
                    add("E004", f"{loc}.twins: {t!r} is not an enabled twin")
                continue
            tc = enabled_twins[t]["fm"].get("tierCeiling")
            if tier in TIERS and tc in TIERS and TIERS.index(tier) > TIERS.index(tc):
                add("E042", f"{loc}: tier {tier} exceeds twin {t!r} "
                    f"tierCeiling {tc}")
        dt = ch.get("defaultTwin")
        if isinstance(dt, str) and dt not in twins:
            add("E004", f"{loc}.defaultTwin {dt!r} is not in channel twins")
        askers = ch.get("askers")
        for key, vals in (("askers", askers if isinstance(askers, list) else []),
                          ("requesters", ch.get("requesters")),
                          ("approvers", ch.get("approvers"))):
            for v in _strs(vals):
                if v not in positions:
                    add("E004", f"{loc}.{key}: {v!r} is not a position")
        aut = ch.get("autonomyCeiling")
        if aut in ("act-with-approval", "act"):
            add("W001", f"{loc}.autonomyCeiling is {aut!r}: accepted by "
                "lint, refused by the gateway", "warning")
        if tier == "T3":
            if self.mode in ("ci", "strict"):
                add("E043", f"{loc}: tier T3 is refused in tracked manifests "
                    "(alpha refuses T3; see team/policies/restricted.md)")
            else:
                if adapter != "mock":
                    add("E043", f"{loc}: a T3 channel may only bind the "
                        "mock adapter")
                if aut in AUTONOMY and AUTONOMY.index(aut) > AUTONOMY.index("draft"):
                    add("E043", f"{loc}: a T3 channel autonomyCeiling must "
                        "be <= draft")

    # -- local overlays ---------------------------------------------------
    def check_overlays(self):
        r = self.roster
        local = self.root / "team" / "local"
        positions = {p.get("id") for p in _dicts(r.get("positions"))}
        channels = {c.get("id") for c in _dicts(r.get("channels"))}
        idp = local / "identities.local.yaml"
        if idp.is_file():
            self.check_identities(idp, positions)
        bp = local / "bindings.local.yaml"
        if bp.is_file():
            self.check_bindings(bp, channels)
        pdir = local / "personal"
        if pdir.is_dir():
            for p in sorted(pdir.glob("*.local.md")):
                self.check_personal(p)

    def check_identities(self, path, positions):
        add = self.adder(path)
        try:
            data = load_roster(path)
        except LoadError as e:
            add(e.code, e.message)
            return
        _check_map(add, data, _IDENTITY_FILE, "identities")
        for i, u in enumerate(_dicts(data.get("users"))):
            pos, acts = _strs(u.get("positions")), _dicts(u.get("actingFor"))
            loc = f"users[{i}]"
            if len(pos) + len(acts) > 2:
                add("E045", f"{loc}: positions ({len(pos)}) + actingFor "
                    f"({len(acts)}) exceeds 2")
            for pid in pos:
                if pid not in positions:
                    add("E004", f"{loc}.positions: {pid!r} is not a position")
            for j, a in enumerate(acts):
                for key in ("role", "grantedBy"):
                    if isinstance(a.get(key), str) and a[key] not in positions:
                        add("E004", f"{loc}.actingFor[{j}].{key}: "
                            f"{a[key]!r} is not a position")
                u_ = a.get("until")
                if _valid_date(u_) and (_date(u_) - self.today).days > ACTING_MAX_DAYS:
                    add("E004", f"{loc}.actingFor[{j}].until {u_} is more "
                        f"than {ACTING_MAX_DAYS} days away")

    def check_bindings(self, path, channels):
        add = self.adder(path)
        try:
            data = load_roster(path)
        except LoadError as e:
            add(e.code, e.message)
            return
        _check_map(add, data, {"schema": ("int", False),
                               "channels": ("any", True)}, "bindings")
        chs = data.get("channels")
        if not isinstance(chs, dict):
            if "channels" in data:
                add("E004", "bindings.channels must be a mapping")
            return
        for cid, b in chs.items():
            if cid not in channels:
                add("E004", f"bindings.channels.{cid}: not a roster channel")
            if not isinstance(b, dict):
                add("E004", f"bindings.channels.{cid}: expected a mapping")
                continue
            _check_map(add, b, {"platform": ("str", True),
                                "ref": ("str", True)},
                       f"bindings.channels.{cid}")

    def check_personal(self, path):
        add = self.adder(path)
        tid = path.name[: -len(".local.md")]
        if self.roster is not None and tid not in self.twins:
            add("E004", f"personal overlay for unknown twin {tid!r}")
        text = path.read_text(encoding="utf-8")
        fm, body = {}, text
        if text.startswith("---"):
            try:
                fm, body = split_frontmatter(text)
            except LoadError as e:
                add(e.code, e.message)
                return
        _check_map(add, fm, _PERSONAL, "personal", unknown_code="E046")
        n = len(body.encode("utf-8"))
        if n > BUDGETS["personal-body"]:
            add("E050", f"personal overlay body is {n} B "
                f"(max {BUDGETS['personal-body']} B)")

    # -- repo hygiene -----------------------------------------------------
    def list_files(self):
        root = self.root
        if (root / ".git").exists():
            try:
                run = lambda *a: subprocess.run(  # noqa: E731
                    ["git", "-C", str(root), *a], capture_output=True,
                    check=True).stdout.decode("utf-8")
                tracked = {f for f in run("ls-files", "-z").split("\0") if f}
                everything = tracked | {f for f in run(
                    "ls-files", "-z", "--cached", "--others",
                    "--exclude-standard").split("\0") if f}
                self.tracked = tracked
                self.files = sorted(f for f in everything
                                    if (root / f).is_file())
                return
            except (OSError, subprocess.CalledProcessError):
                pass
        self.tracked = None
        files = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            parts = rel.split("/")
            if parts[0] in (".git", "node_modules") or "__pycache__" in parts:
                continue
            if rel.startswith("team/.build/"):
                continue
            if rel.startswith("team/local/") and rel not in (
                    "team/local/README.md", "team/local/.gitkeep"):
                continue
            if fnmatch.fnmatch(parts[-1], "*.local.*"):
                continue
            files.append(rel)
        self.files = sorted(files)

    def check_hygiene(self):
        self.list_files()
        allow, problems = load_lint_allow(self.root)
        for pr in problems:
            self.add("E003", "team/tools/lint-allow.txt", pr)
        secrets = shared_secret_patterns(self.root)
        for rel in self.files:
            p = self.root / rel
            try:
                if p.stat().st_size > 2_000_000:
                    continue
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            self.scan_secrets(rel, text, secrets)
            if rel == "TEAM.md" or rel.startswith(("team/", "examples/")):
                self.scan_names(rel, text, allow)
        self.check_gitignore()

    def scan_secrets(self, rel, text, secrets):
        for name, rx in secrets:
            m = rx.search(text)
            if m:
                self.add("E013", rel, f"line {text.count(chr(10), 0, m.start()) + 1}"
                         f": matches secret pattern {name!r}")
        if rel.startswith(("team/", "infra/chat-gateway/")):
            m = _GENERIC_SECRET.search(text)
            if m:
                self.add("E013", rel, f"line {text.count(chr(10), 0, m.start()) + 1}"
                         ": looks like a hard-coded secret assignment")

    def scan_names(self, rel, text, allow):
        def allowed(s):
            return any(a.search(s) for a in allow)

        for m in NAME_ZH.finditer(text):
            if not allowed(m.group(0)):
                self.add("E012", rel, f"line {text.count(chr(10), 0, m.start()) + 1}"
                         ": surname + job title looks like a real name")
                break
        for name, rx in NAME_OTHER:
            for m in rx.finditer(text):
                if not allowed(m.group(0)):
                    self.add("E014", rel, f"line "
                             f"{text.count(chr(10), 0, m.start()) + 1}: "
                             f"matches personal-data heuristic {name!r}")
                    break
        for m in _EMAIL.finditer(text):
            if not _EMAIL_OK.search(m.group(1)) and not allowed(m.group(0)):
                self.add("E014", rel, f"line {text.count(chr(10), 0, m.start()) + 1}"
                         ": email address outside example.(com|org|test)")
                break

    def check_gitignore(self):
        gi = self.root / ".gitignore"
        lines = []
        try:
            lines = [ln.strip() for ln in gi.read_text(
                encoding="utf-8").splitlines()]
        except OSError:
            self.add("E060", ".gitignore", ".gitignore is missing")
        else:
            for need in REQUIRED_GITIGNORE:
                if need not in lines:
                    self.add("E060", ".gitignore", f"missing entry {need!r}")
            if "team/local/" in lines:
                self.add("E060", ".gitignore", "use 'team/local/*', not "
                         "'team/local/' (negations would not work)")
        if self.tracked is not None:
            for f in sorted(self.tracked):
                base = f.rsplit("/", 1)[-1]
                if not (self.root / f).is_file():
                    continue
                bad = (fnmatch.fnmatch(base, "*.local.*")
                       or f.startswith("team/.build/")
                       or (f.startswith("team/local/") and f not in (
                           "team/local/README.md", "team/local/.gitkeep")))
                if bad:
                    self.add("E060", f, "tracked file must not exist "
                             "(local/build artifact)")

    # -- budgets, build, determinism --------------------------------------
    def size_row(self, label, rel, limit, code_path=None):
        p = self.root / rel
        if not p.is_file():
            return
        data = p.read_bytes()
        n = len(data)
        self.stats["budget_rows"].append(
            (label, n, limit, est_tokens(data.decode("utf-8", "replace"))))
        if limit is not None and n > limit:
            self.add("E050", code_path or rel, f"{label} is {n} B "
                     f"(max {limit} B)")
        return n

    def check_budgets(self):
        self.size_row("TEAM.md", "TEAM.md", BUDGETS["TEAM.md"])
        self.size_row("team/policies/core-rules.md",
                      "team/policies/core-rules.md", BUDGETS["core-rules.md"])
        ex = "team/roster.example.yaml"
        if (self.root / ex).is_file():
            self.size_row(ex, ex, BUDGETS["roster.example.yaml"])
        for p in sorted((self.root / "team" / "twins").glob("*.md")):
            rel = p.relative_to(self.root).as_posix()
            self.size_row(rel, rel, BUDGETS["twin-file"])
        if self.n_errors():
            return  # compile-based checks need a structurally valid input
        try:
            c1 = compile_all(self.root, self.roster_path)
            c2 = compile_all(self.root, self.roster_path)
        except (BuildError, LoadError, OSError, KeyError, ValueError) as e:
            self.add("E001", self.roster_path, f"cannot compile: {e}")
            return
        for f in c1.findings:
            self.add(f.code, f.path, f.message, f.severity)
        if c1.source_hash != c2.source_hash or c1.files != c2.files:
            self.add("E051", self.roster_path, "build is not deterministic: "
                     "two builds produced different output")
        rj = c1.files["roster.json"]
        self.stats["budget_rows"].append(
            ("roster.json", len(rj), BUDGETS["roster.json"],
             est_tokens(rj.decode("utf-8"))))
        if len(rj) > BUDGETS["roster.json"]:
            if self.is_example:
                self.add("E050", self.roster_path, f"roster.json is "
                         f"{len(rj)} B (max {BUDGETS['roster.json']} B)")
            else:
                self.add("W007", self.roster_path, f"roster.json is "
                         f"{len(rj)} B (> {BUDGETS['roster.json']} B total)",
                         "warning")
        for t in json.loads(rj)["twins"]:
            n = len(canon(t))
            if n > BUDGETS["roster.json-twin"]:
                msg = (f"roster.json entry for twin {t['id']!r} is {n} B "
                       f"(max {BUDGETS['roster.json-twin']} B)")
                if self.is_example and self.mode == "ci":
                    self.add("E050", self.roster_path, msg)
                else:
                    self.add("W008", self.roster_path, msg, "warning")
        for name, data in sorted(c1.files.items()):
            if name.startswith("twins/"):
                self.stats["budget_rows"].append(
                    (f".build/{name}", len(data), BUDGETS["prompt"],
                     est_tokens(data.decode("utf-8"))))
        sb = len(c1.summary.encode("utf-8"))
        self.stats["budget_rows"].append(
            ("build --summary", sb, BUDGETS["summary"], est_tokens(c1.summary)))
        if sb > BUDGETS["summary"]:
            self.add("E050", self.roster_path,
                     f"build --summary is {sb} B (max {BUDGETS['summary']} B)")
        parts = [self.root / "TEAM.md", self.root / ex,
                 self.root / "team/policies/core-rules.md"]
        if all(p.is_file() for p in parts):
            cold = sum(p.stat().st_size for p in parts) + sb
            self.stats["budget_rows"].append(
                ("cold start (TEAM+roster.example+core-rules+summary)", cold,
                 BUDGETS["cold-start"], None))
            if cold > BUDGETS["cold-start"]:
                self.add("E050", "TEAM.md", f"cold start is {cold} B "
                         f"(max {BUDGETS['cold-start']} B)")


def validate_ex(repo_root, roster_path, *, mode: str = "local",
                today: str | None = None) -> tuple[list[Finding], dict]:
    today = today or _dt.date.today().isoformat()
    return _Validator(Path(repo_root), roster_path, mode, today).run()


def validate(repo_root, roster_path, *, mode: str = "local",
             today: str | None = None) -> list[Finding]:
    return validate_ex(repo_root, roster_path, mode=mode, today=today)[0]


# --------------------------------------------------------------------------
# Reference resolution + compiler
# --------------------------------------------------------------------------

def find_ref(root: Path, kind_dir: str, ident: str,
             profiles: list[str]) -> Path | None:
    if not ident or "/" in ident or "\\" in ident or ".." in ident:
        return None
    cands = [root / "profiles" / p / kind_dir / f"{ident}.md"
             for p in profiles]
    cands.append(root / "core" / kind_dir / f"{ident}.md")
    for c in cands:
        if c.is_file():
            return c
    return None


def _resolver():
    d = str(TOOL_REPO / "adapters" / "claude-code")
    if d not in sys.path:
        sys.path.insert(0, d)
    import _resolve_extends  # noqa: PLC0415
    return _resolve_extends


def resolved_text(root: Path, path: Path) -> str:
    """Resolved agent/skill text: profile files with `extends:` go through
    `_resolve_extends.resolve_profile_file`; everything else is verbatim."""
    text = path.read_text(encoding="utf-8")
    rel = path.resolve().relative_to(root)
    m = _FM_RE.match(text)
    if (rel.parts[0] == "profiles" and m
            and re.search(r"^extends:", m.group(1), re.M)):
        return _resolver().resolve_profile_file(path, root).text
    return text


def _desc(text: str, fallback: str) -> str:
    try:
        fm, _ = split_frontmatter(text)
    except LoadError:
        fm = {}
    for k in ("description", "title", "displayName", "summary"):
        v = fm.get(k)
        if isinstance(v, str) and v.strip():
            v = " ".join(v.split())
            return v if len(v) <= 70 else v[:69] + "…"
    return fallback


def _body_of(text: str) -> str:
    m = _FM_RE.match(text)
    return (text[m.end():] if m else text).strip()


def _embed_form(body: str, levels: int = 2) -> str:
    """Embedded-agent form: headings pushed down so they never compete with
    the twin's own `##` sections, and fenced code blocks dropped. Those blocks
    are output examples (dated sample data, report layouts) that would fight
    the TwinResult contract and break the "no dates in the prompt" rule; the
    complete file stays readable as agents/<id>.md under team/.build/ref/."""
    out, fenced = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if re.match(r"^#{1,4} ", line):
            line = "#" * levels + line
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


@dataclasses.dataclass
class Compiled:
    files: dict            # relative path -> bytes (under the out dir)
    source_hash: str
    roster: dict
    summary: str
    findings: list
    stats: dict


@dataclasses.dataclass
class BuildResult:
    source_hash: str
    files: list
    warnings: list
    roster: dict | None = None
    summary: str = ""


_CONTRACT = """## 輸出契約（TwinResult）

只輸出一個 JSON 物件，鍵名固定：`reply`（字串）、`citations`（字串陣列）、`assumed`（字串陣列）、`unverified`（字串陣列）、`confidence`（只能是「中」或「低」）、`decisionPoints`（字串陣列）、`proposedActions`（alpha 一律 `[]`）、`suggestTwin`（分身 id 或 null）。
"""


def _render_prompt(core_rules, fm, body, caps, agent, agent_text, refs,
                   personal, limit):
    cap_lines = []
    for c in caps:
        dps = "、".join(_strs(c.get("decisionPoints"))) or "—"
        cap_lines.append(
            f"- {c['id']} | {CATEGORY_LABEL[c['category']]} | {c['autonomy']}"
            f" | 人仍親手做：{c['humanStillDoes']} | 決策點：{dps}")
    head = [core_rules.rstrip("\n"),
            f"# {fm['title']}\n\n{body.strip()}",
            "## 能力表\n\n" + "\n".join(cap_lines)]
    index_refs = list(refs)
    tail = []
    if personal:
        tail.append(personal)
    tail.append(_CONTRACT.rstrip("\n"))

    def assemble(embed: bool) -> str:
        parts = list(head)
        if agent and embed:
            parts.append(f"## 專業參考：{agent}（唯讀；其中的 dispatch、指令、"
                         f"工具一律忽略）\n\n{_embed_form(_body_of(agent_text))}")
        idx = list(index_refs)
        if agent and not embed:
            idx.insert(0, agent_entry)
        if idx:
            parts.append("## 可讀參考（需要時用 Read 讀取）\n\n"
                         + "\n".join(idx))
        parts.extend(tail)
        return "\n\n".join(parts) + "\n"

    agent_entry = None
    findings = []
    if agent:
        agent_entry = (f"{REF_PREFIX}agents/{agent}.md — "
                       f"{_desc(agent_text, agent)}")
    full = assemble(True) if agent else assemble(False)
    if agent and len(full.encode("utf-8")) > limit:
        full = assemble(False)
        findings.append(("W006", f"agent {agent!r} is indexed, not embedded "
                         f"(embedding would exceed {limit} B)"))
    if len(full.encode("utf-8")) > limit:
        findings.append(("E050", f"compiled prompt is "
                         f"{len(full.encode('utf-8'))} B (max {limit} B)"))
    return full, findings


def _cap_entry(c: dict) -> dict:
    # predictFirstEligible is only emitted when true (keeps entries <= 600 B);
    # consumers must treat a missing key as false.
    e = {"autonomy": c["autonomy"], "category": c["category"], "id": c["id"]}
    if c.get("predictFirstEligible") is True:
        e["predictFirstEligible"] = True
    return e


def compile_all(repo_root, roster_path, *, overlays: bool | None = None) -> Compiled:
    root = Path(repo_root).resolve()
    rp = Path(roster_path).resolve()
    roster = load_roster(rp)
    example = ".example." in rp.name
    use_overlays = (not example) if overlays is None else overlays
    inputs: dict[str, bytes] = {}

    def read(p: Path) -> bytes:
        b = p.read_bytes()
        inputs[_posix_rel(root, p)] = b
        return b

    read(rp)
    for p in sorted((root / "team" / "policies").glob("*.md")):
        read(p)
    core_rules = read(root / "team/policies/core-rules.md").decode("utf-8")
    profiles = _strs(roster.get("profiles"))
    policy = roster["policy"]
    positions = _dicts(roster.get("positions"))
    local = root / "team" / "local"
    findings: list[Finding] = []
    ref_files: dict[str, bytes] = {}
    twin_entries: list[dict] = []
    prompts: dict[str, bytes] = {}
    enabled_ids: list[str] = []
    stats = {"outsource_enabled": 0, "outsource_dormant": 0}

    for pos in positions:
        tw = pos.get("twin")
        if not (isinstance(tw, dict) and tw.get("enabled") is True):
            continue
        tid = tw["file"]
        tpath = root / "team" / "twins" / f"{tid}.md"
        fm, body = split_frontmatter(read(tpath).decode("utf-8"))
        enabled_ids.append(tid)
        disabled = set(_strs(tw.get("disable")))
        wake = {e.get("capability") for e in _dicts(tw.get("enableOutsource"))}
        active, dormant, enabled_out = [], 0, 0
        for cap in _dicts(fm["capabilities"]):
            if cap["id"] in disabled:
                continue
            if cap["category"] == "outsource":
                if cap["id"] in wake:
                    c = dict(cap)
                    c["autonomy"] = _min_level([cap["autonomy"], "draft"])
                    active.append(c)
                    enabled_out += 1
                else:
                    dormant += 1
            else:
                active.append(cap)
        stats["outsource_enabled"] += enabled_out
        stats["outsource_dormant"] += dormant

        comp = fm["compose"]
        refs: list[str] = []
        agent = comp.get("agent")
        agent_text = ""
        todo = []
        if agent:
            todo.append(("agents", agent))
        for key, kdir in (("skills", "skills"), ("knowHow", "know-how"),
                          ("hooks", "hooks")):
            todo.extend((kdir, i) for i in _strs(comp.get(key)))
        for ent in _strs(comp.get("optional")):
            prof, _, ident = ent.partition(":")
            if prof in profiles:
                for kdir in ("agents", "skills", "know-how", "hooks"):
                    if find_ref(root, kdir, ident, [prof]):
                        todo.append((kdir, ident, prof))
                        break
        for item in todo:
            kdir, ident = item[0], item[1]
            plist = [item[2]] if len(item) == 3 else profiles
            src = find_ref(root, kdir, ident, plist)
            if src is None:
                raise BuildError([Finding(
                    "E023", "error", _posix_rel(root, tpath),
                    f"compose id {ident!r} ({kdir}) cannot be resolved")])
            text = resolved_text(root, src)
            inputs[_posix_rel(root, src)] = text.encode("utf-8")
            ref_files[f"ref/{kdir}/{ident}.md"] = text.encode("utf-8")
            if kdir == "agents" and ident == agent:
                agent_text = text
            else:
                refs.append(f"{REF_PREFIX}{kdir}/{ident}.md — "
                            f"{_desc(text, ident)}")
        personal, extra_aliases = "", []
        if use_overlays:
            pp = local / "personal" / f"{tid}.local.md"
            if pp.is_file():
                read(pp)
                pfm, pbody = ({}, pp.read_text(encoding="utf-8"))
                if pbody.startswith("---"):
                    pfm, pbody = split_frontmatter(pbody)
                lines = []
                for k in ("tone", "digestFormat"):
                    if k in pfm:
                        lines.append(f"- {k}: {pfm[k]}")
                for k, v in sorted((pfm.get("retention") or {}).items()):
                    lines.append(f"- retention.{k}: {str(v).lower()}")
                extra_aliases = _strs(pfm.get("aliases"))
                personal = ("## 個人偏好（在職者設定；不得放寬任何規則）\n\n"
                            + "\n".join(lines + ([pbody.strip()]
                                                 if pbody.strip() else [])))
        prompt, pf = _render_prompt(core_rules, fm, body, active, agent,
                                    agent_text, refs, personal,
                                    BUDGETS["prompt"])
        for code, msg in pf:
            findings.append(Finding(code, "error" if code[0] == "E" else
                                    "warning", _posix_rel(root, tpath), msg))
        pb = prompt.encode("utf-8")
        prompts[f"twins/{tid}.prompt.md"] = pb
        ceiling = _min_level([fm["autonomyCeiling"], tw["autonomyCeiling"],
                              policy["autonomyCeiling"]]
                             + (["observe"] if pos.get("incumbent") == "VACANT"
                                else []))
        twin_entries.append({
            "aliases": list(dict.fromkeys(_strs(fm.get("aliases"))
                                          + extra_aliases)),
            "capabilities": [_cap_entry(c) for c in active],
            "channels": sorted(c["id"] for c in _dicts(roster.get("channels"))
                               if tid in _strs(c.get("twins"))),
            "department": pos["department"], "effectiveCeiling": ceiling,
            "id": tid,
            "outsource": {"dormant": dormant, "enabled": enabled_out},
            "prompt": f"twins/{tid}.prompt.md", "promptSha": _sha(pb),
            "tierCeiling": fm["tierCeiling"], "title": fm["title"],
            "vacant": pos.get("incumbent") == "VACANT"})

    channels = []
    for c in sorted(_dicts(roster.get("channels")), key=lambda x: x["id"]):
        e = {"adapter": c["adapter"], "askers": c["askers"],
             "autonomyCeiling": c["autonomyCeiling"],
             "defaultTwin": c["defaultTwin"], "department": c["department"],
             "id": c["id"], "tier": c["tier"],
             "twins": [t for t in c["twins"] if t in enabled_ids]}
        for k in ("requesters", "approvers"):
            if c.get(k):
                e[k] = list(c[k])
        channels.append(e)

    identities = bindings = None
    if use_overlays:
        for name, key in (("identities", "users"), ("bindings", "channels")):
            lp = local / f"{name}.local.yaml"
            if lp.is_file():
                read(lp)
                data = load_roster(lp)
                out = {"schema": 1, key: data.get(key, [] if key == "users"
                                                  else {})}
                if name == "identities":
                    identities = out
                else:
                    bindings = out

    h = hashlib.sha256()
    for path in sorted(inputs):
        h.update(path.encode("utf-8") + b"\0" + inputs[path] + b"\0")
    source_hash = "sha256:" + h.hexdigest()

    out_roster = {
        "builtBy": BUILT_BY, "channels": channels, "org": roster["org"]["id"],
        "policy": {"autonomyCeiling": policy["autonomyCeiling"],
                   "channelWindow": policy.get("channelWindow", 10),
                   "cloudTierCeiling": policy["cloudTierCeiling"],
                   "saasTierCeiling": policy["saasTierCeiling"]},
        "schema": 1, "sourceHash": source_hash,
        "twins": sorted(twin_entries, key=lambda t: t["id"])}
    files: dict[str, bytes] = {"roster.json": canon(out_roster)}
    files.update(prompts)
    files.update(ref_files)
    if identities is not None:
        files["identities.json"] = canon(identities)
    if bindings is not None:
        files["bindings.json"] = canon(bindings)
    summary = render_summary(out_roster, example, rp.name, findings)
    return Compiled(files, source_hash, out_roster, summary, findings, stats)


def render_summary(roster: dict, example: bool, roster_name: str,
                   findings: list) -> str:
    warns = sum(1 for f in findings if f.severity == "warning")
    lines = [f"{BUILT_BY} | org {roster['org']} | roster {roster_name}"
             + (" | DEMO (example roster, mock only)" if example else ""),
             f"sourceHash {roster['sourceHash'][:19]}",
             "policy: saas<={saasTierCeiling} cloud<={cloudTierCeiling} "
             "autonomy<={autonomyCeiling} window={channelWindow}".format(
                 **roster["policy"]),
             f"twins ({len(roster['twins'])}):"]
    for t in roster["twins"]:
        o = t["outsource"]
        lines.append(f" - {t['id']} {t['tierCeiling']}/{t['effectiveCeiling']}"
                     f" caps={len(t['capabilities'])}"
                     f" outsource={o['enabled']}/{o['dormant']}"
                     f" ch={','.join(t['channels']) or '-'}")
    lines.append(f"channels ({len(roster['channels'])}):")
    for c in roster["channels"]:
        lines.append(f" - {c['id']} {c['tier']}/{c['adapter']} "
                     f"default={c['defaultTwin']}")
    lines.append(f"warnings: {warns}")
    lines.append("next: /team status | python3 infra/chat-gateway/demo.py")
    out, size = [], 0
    for ln in lines:
        b = len(ln.encode("utf-8")) + 1
        if size + b > BUDGETS["summary"] - 8:
            out.append("…")
            break
        out.append(ln)
        size += b
    return "\n".join(out) + "\n"


_OUT_ITEMS = ("roster.json", "identities.json", "bindings.json", "twins", "ref")


def build(repo_root, roster_path, out_dir) -> BuildResult:
    """Compile and write `out_dir`. Raises BuildError on error findings."""
    c = compile_all(repo_root, roster_path)
    errors = [f for f in c.findings if f.severity == "error"]
    if errors:
        raise BuildError(errors)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for item in _OUT_ITEMS:  # only ever remove what a build creates
        p = out / item
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    for rel, data in c.files.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return BuildResult(c.source_hash, sorted(c.files), list(c.findings),
                       c.roster, c.summary)


def check_deterministic(repo_root, roster_path) -> list[Finding]:
    a = compile_all(repo_root, roster_path)
    b = compile_all(repo_root, roster_path)
    if a.source_hash != b.source_hash or a.files != b.files:
        return [Finding("E051", "error", str(roster_path),
                        "build is not deterministic: two builds differ")]
    return []


def default_roster(root: Path, *, prefer_example: bool = False) -> Path:
    local = Path(root) / "team" / "local" / "roster.local.yaml"
    if not prefer_example and local.is_file():
        return local
    return Path(root) / "team" / "roster.example.yaml"
