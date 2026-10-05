"""Team-tier schema: constants, error codes, field specs and the regex bridge.

`CODES` (E0xx / W0xx), byte `BUDGETS`, enum tuples, id/date regexes, `Finding` / `LoadError` /
`BuildError`, the `{key: (type, required)}` field specs walked by `validate`, and every
secret / name / PII / DLP regex, loaded from `infra/chat-gateway/chat_gateway/patterns.py`
(the single source; nothing is copied here).
"""
from __future__ import annotations

import dataclasses
import importlib.util
import re
from pathlib import Path

VERSION = "0.2.0-alpha"
BUILT_BY = f"teamctl {VERSION}"
TOOL_REPO = Path(__file__).resolve().parents[3]   # team/tools/teamlib/schema.py

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
            if name != "tw-ubn" or _PAT.ubn_hit(text, m):
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
