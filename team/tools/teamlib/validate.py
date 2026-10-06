"""Hand-written validator: schema walker, effective autonomy, `_Validator`, `validate(_ex)`."""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import re
import subprocess
from pathlib import Path

from .schema import (ACTING_MAX_DAYS, ADAPTER_MAX_TIER, AUTONOMY, BUDGETS, _CAPID_RE, CATEGORY_VALUES,
                     DOER_HINT_WORDS, _EMAIL, _EMAIL_OK, GATE_RESULTS, NOBODY_TODAY_RE, REVIEW_FILLER_WORDS,
                     REVIEW_ONLY_WORDS, GATE_STALE_DAYS, _GENERIC_SECRET, _ID_RE, _IDENTITY_FILE,
                     IDENTITY_KEYS, NAME_OTHER, NAME_ZH, OUTSOURCE_MAX_DAYS, OUTSOURCE_WARN_DAYS, _PERSONAL,
                     REQUIRED_GITIGNORE, REQUIRED_SECTIONS, SAFETY_KEYWORDS, TIER_CAP, TIERS, _TWIN,
                     BuildError, Finding, LoadError, load_lint_allow, _roster_schema, shared_secret_patterns)
from .io import (canon, _date, _dicts, est_tokens, load_roster, load_twin, _min_level, _norm_key, _posix_rel,
                 _rank, split_frontmatter, _strs, _valid_date)
from .compile import compile_all, find_ref


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

_FILLER_RE = re.compile(r"[\s、，,。;；/:：()（）「」『』\-—]+")
_ROLE_PREFIX_RE = re.compile(r"^\s*([^\s：:，,；;。]{1,12})[：:]")
_STRIP_WORDS = tuple(sorted(set(REVIEW_ONLY_WORDS) | set(REVIEW_FILLER_WORDS), key=len, reverse=True))


def _role_lines(text: str) -> list[str]:
    """Split `humanStillDoes` into one text per role: "主管：A；B；品保工程師：C" -> ["A；B", "C"].
    Text without a `role：` prefix is a single line."""
    lines: list[str] = []
    for part in re.split(r"[；;\n]", text):
        m = _ROLE_PREFIX_RE.match(part)
        if m or not lines:
            lines.append(part[m.end():] if m else part)
        else:
            lines[-1] += "；" + part
    return lines


def _review_only_line(line: str) -> bool:
    rest = line
    for w in _STRIP_WORDS:
        rest = rest.replace(w, "")
    return len(_FILLER_RE.sub("", rest)) <= 2


def _only_review(text: str) -> bool:
    """True when some role's line in `humanStillDoes` names no act of its own: after removing
    REVIEW_ONLY_WORDS, REVIEW_FILLER_WORDS and punctuation, <= 2 characters are left (E038).
    Lines that never used a review word are not judged (an empty line is E037's job)."""
    return any(any(w in line for w in REVIEW_ONLY_WORDS) and _review_only_line(line)
               for line in _role_lines(text) if line.strip())


def _nobody_today(text) -> bool:
    return isinstance(text, str) and bool(NOBODY_TODAY_RE.match(text))


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
        self.check_caps(add, fm, self.own_roles(stem, tid))
        self.check_schedule(add, fm, template)
        self.check_body(add, body)
        if fm.get("tierCeiling") in TIERS and fm["tierCeiling"] == "T3":
            self.check_t3_twin(add, fm, template)
        if fm.get("autonomyCeiling") in ("act-with-approval", "act"):
            add("W001", f"twin.autonomyCeiling is {fm['autonomyCeiling']!r}: "
                "accepted by lint, refused by the gateway", "warning")

    def own_roles(self, stem, tid) -> set:
        """Ids and titles that count as "the twin's own position" for E063 / W009: the twin id,
        and every roster position (id and title) whose twin.file is this twin."""
        own = {stem} | ({tid} if isinstance(tid, str) else set())
        for pos in _dicts((self.roster or {}).get("positions")):
            tw = pos.get("twin")
            if isinstance(tw, dict) and tw.get("file") in own:
                own |= {v for v in (pos.get("id"), pos.get("title")) if isinstance(v, str)}
        return own

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

    def check_caps(self, add, fm, own=frozenset()):
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
            if cat in ("strengthen", "create") and isinstance(cap.get("humanStillDoes"), str):
                if cap["humanStillDoes"].strip() and _only_review(
                        cap["humanStillDoes"]):
                    add("E038", f"{loc}.humanStillDoes only says review/look/approve/"
                        "send (REVIEW_ONLY_WORDS) for at least one role; state what "
                        "the person still does by hand")
            self.check_doer(add, cap, cat, loc, own)
        if cats and not any(c in ("strengthen", "create") for c in cats):
            add("E035", "twin has no strengthen or create capability")

    def check_doer(self, add, cap, cat, loc, own):
        """E061-E063, W009: who does the task today, and did they agree (spec 5.3)."""
        today = cap.get("today")
        if not isinstance(today, str) or not today.strip():
            return  # E037
        roles = [r for r in _strs(cap.get("affectedRoles")) if r.strip()]
        nobody = _nobody_today(today)
        if nobody and cat in ("strengthen", "outsource"):
            add("E062", f"{loc}.today says nobody does this today ({today!r}); only a "
                "`create` capability may say so. If someone does it, name them in "
                "today and affectedRoles")
        if not nobody and not roles:
            add("E061", f"{loc}: today ({today!r}) has someone doing the task, but "
                "affectedRoles is missing; list the positions or job labels that do it today")
        others = [r for r in roles if r not in own]
        ack = cap.get("doerAckedOn")
        if others and cat in ("strengthen", "create"):
            self.check_ack(add, loc, others, ack)
        if roles and not others and any(w in today for w in DOER_HINT_WORDS):
            add("W009", f"{loc}.today mentions another job ({today!r}) but affectedRoles "
                f"only lists this twin's own position {roles}; check whether the people "
                "who do it today are missing", "warning")

    def check_ack(self, add, loc, others, ack):
        if not _valid_date(ack):
            add("E063", f"{loc}: affectedRoles {others} are not this twin's own position; "
                "doerAckedOn (YYYY-MM-DD, the day they read `today`/`humanStillDoes` and "
                "agreed) is required")
        elif _date(ack) > self.today:
            add("E063", f"{loc}.doerAckedOn {ack} is in the future")

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
        self.check_vacancy(add, pos, tw, depts, loc)
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

    def check_vacancy(self, add, pos, tw, depts, loc):
        """E064: a twin is not a stand-in for an unfilled position (spec 7.3)."""
        if not (pos.get("incumbent") == "VACANT" and tw.get("enabled") is True):
            return
        by, on = tw.get("vacancyApprovedBy"), tw.get("vacancyApprovedOn")
        if not isinstance(by, str) or not _valid_date(on):
            add("E064", f"{loc}: position is VACANT and the twin is enabled; "
                "vacancyApprovedBy (a position on the escalation ladder) and "
                "vacancyApprovedOn (YYYY-MM-DD) are required")
            return
        esc = _strs((depts.get(pos.get("department")) or {}).get("escalation"))
        if by not in esc or by == pos.get("id"):
            add("E064", f"{loc}.vacancyApprovedBy {by!r} must be on the department "
                "escalation ladder and not the vacant position itself")

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
                    own = self.own_roles(tw.get("file"), tw.get("file"))
                    others = [r for r in _strs(cap.get("affectedRoles")) if r.strip() and r not in own]
                    if others:  # waking it takes the task from them: they must have agreed
                        self.check_ack(add, eloc, others, cap.get("doerAckedOn"))
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
                "are expected; the tool only checks that manualRepsPerMonth is an integer >= 1, "
                "it cannot verify they happen)", "warning")
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
        learners = _strs(ch.get("learners"))
        for v in learners:
            if v not in positions:
                add("E004", f"{loc}.learners: {v!r} is not a position")
            elif isinstance(askers, list) and v in askers:
                add("E004", f"{loc}.learners: {v!r} is also an asker; a position is "
                    "either an asker or a learner in one channel")
        if ch.get("predictFirstDefault") is True and not learners:
            add("E004", f"{loc}.predictFirstDefault applies to learners; the channel has none")
        days = ch.get("twinFreeDays")
        if isinstance(days, list):
            ints = [d for d in days if isinstance(d, int) and not isinstance(d, bool)]
            if any(not 1 <= d <= 31 for d in ints) or len(set(ints)) != len(ints):
                add("E004", f"{loc}.twinFreeDays must be distinct days of the month 1..31")
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
        # Size only (cold start / per-turn cost). Not a classification check: see the
        # BUDGETS comment in schema.py and E038 / E061-E063 in check_caps.
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
