"""Single source of truth for secret / name / PII / DLP regexes (§11.1, §11.4).

Used by the gateway (inbound DLP, outbound masking, config scanning) and by
`team/tools/_teamlib.py` (teamctl repo hygiene, deid residual scan), which loads
this file directly. Lists are `list[tuple[name, re.Pattern]]`. Stdlib `re` only.

Some literals are built by concatenation so this file never matches its own
patterns when a scanner reads it.
"""
from __future__ import annotations

import re

_P = re.compile

SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("slack-token", _P(r"xox[abprs]-[0-9A-Za-z-]{10,}")),
    ("slack-app-token", _P(r"xapp-\d-[A-Z0-9]+-\d+-[a-f0-9]{20,}")),
    ("slack-webhook", _P(r"https://hooks\.slack\.com/services/\S+")),
    ("discord-token", _P(r"[MNO][A-Za-z\d_-]{23,27}\.[\w-]{6}\.[\w-]{27,}")),
    ("discord-webhook", _P(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\S+")),
    ("anthropic-key", _P(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("github-token", _P(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("aws-key-id", _P(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private-key", _P("-----" + r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY" + "-----")),
]

# Generic `secret=...` assignment; teamctl applies it only to team/** and
# infra/chat-gateway/**, the gateway applies it to its own output.
GENERIC_SECRET: tuple[str, re.Pattern] = (
    "generic-assignment",
    _P(r"(?i)\b(?:secret|token|password|passwd|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+]{8,}"),
)

# Repo hygiene (teamctl E013) uses a stricter generic rule: 16+ chars, so YAML keys like
# `token: required` do not trip it. Applied only to team/** and infra/chat-gateway/**.
REPO_GENERIC_SECRET: tuple[str, re.Pattern] = (
    "generic-assignment",
    _P(r"(?i)\b(?:secret|passw(?:or)?d|token|api[_-]?key)\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-+/=]{16,}"),
)

# ── names / personal data (teamctl E012/E014, deid residual scan) ───
SURNAMES = ("陳林黃張李王吳劉蔡楊許鄭謝郭洪曾邱廖賴徐周葉蘇莊呂江何蕭羅高"
            "潘簡朱鍾彭游詹胡施沈余盧梁趙顏柯翁魏孫戴范方宋鄧杜傅侯曹薛丁"
            "卓阮馬董唐藍蔣石古紀姚連馮歐程湯田康姜白汪鄒尤巫黎涂龔嚴韓袁"
            "金童陸夏柳邵")
TITLES = ("廠長|總經理|副總經理|經理|副總|董事長|協理|襄理|副理|課長|組長|主任|"
          "處長|部長|科長|領班|老闆|先生|小姐|女士|工程師|技師|師傅|主管|會計")
_CJK = "\u3400-\u9fff"

# Surname immediately followed by a title ("X廠長"); previous char must not be CJK.
NAME_ZH = _P(rf"(?<![{_CJK}])[{SURNAMES}](?:{TITLES})")
NAME_OTHER: list[tuple[str, re.Pattern]] = [
    ("honorific-name", _P(r"\b(?:Mr|Ms|Mrs|Dr)\.\s+[A-Z][a-z]+")),
    ("tw-mobile", _P(r"(?<!\d)09\d{2}-?\d{3}-?\d{3}(?!\d)")),
    ("slack-id", _P(r"\b[UWCGT][A-Z0-9]{8,}\b")),
    ("discord-id", _P(r"\b\d{17,20}\b")),
]
EMAIL = _P(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
EMAIL_OK = _P(r"(?:^|\.)example\.(?:com|org|test)$", re.I)
# Spec §9.1 name: every repo-hygiene name/PII heuristic (email filtered by EMAIL_OK at use).
NAME_PATTERNS: list[tuple[str, re.Pattern]] = [("surname-title", NAME_ZH), *NAME_OTHER, ("email", EMAIL)]

# deid.py residual scan (fail closed): any email, Taiwan phone forms, and a CJK name of
# 1–4 chars starting with a common surname right before a title / honorific.
PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", _P(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")),
    ("tw-mobile", _P(r"(?<!\d)(?:\+?886[\s-]?|0)9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")),
    ("tw-landline", _P(r"(?<!\d)(?:\+?886[\s-]?\(?|\(?0)[2-8]\)?[\s-]?\d{3,4}[\s-]?\d{4}(?!\d)")),
    ("name-with-title", _P(rf"[{SURNAMES}][{_CJK}]{{0,3}}?(?:先生|小姐|經理|課長|主任|協理|副理|廠長|董事長)")),
]

# DLP tripwire (alert, not a defence). Tier of each pattern lives in DLP_TIERS.
DLP_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("confidential-zh", _P(r"機密")),
    ("confidential-en", _P(r"(?i)(?<![a-z])confidential(?![a-z])")),
    ("restricted-en", _P(r"(?i)(?<![a-z])restricted(?![a-z])")),
    # 受限 alone is also everyday speech (不受限制, 受限於預算); negated and "constrained by" forms are skipped.
    ("restricted-zh", _P(r"(?<![不未無沒没免])受限(?!於)")),
    ("defense-zh", _P(r"國防")),
    ("tw-ubn", _P(r"(?<!\d)\d{8}(?!\d)")),          # 統一編號; checksum + context cue in ubn_hit()
    ("tw-national-id", _P(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?!\d)")),
    ("amount-ntd", _P(r"NT\$\s?[\d,]{4,}")),
    # Other currency forms (T2): US$ / USD followed or preceded by digits, "125 萬元", "3千元".
    ("amount-usd", _P(r"(?i)(?:US\$|USD)\s?\d|\d\s?USD(?![A-Za-z])")),
    ("amount-zh", _P(r"[\d,.零〇一二三四五六七八九十百兩幾數]\s?(?:萬|千)元")),
    # Defence / aerospace / medical-device / export-control wording (T3 tripwire). A word match,
    # not understanding: it cannot know what a message is about, only that it contains the word.
    ("aerospace-zh", _P(r"航太")),
    # 軍規 / 軍工 also sit inside unrelated words (將軍規模, 行軍規律, 從軍工作): those are skipped.
    ("military-zh", _P(r"(?<![將行大三全])軍規(?![模律劃])|軍工(?!作)")),
    ("medical-device-zh", _P(r"醫材|醫療器材")),
    ("export-permit-zh", _P(r"外銷許可")),
    ("export-control-en", _P(r"(?<![A-Za-z])(?:(?i:itar)|EAR|CUI)(?![A-Za-z])")),
    # 管制 alone is also everyday QC / production vocabulary (管制圖, 文件管制, 製程管制 ...), so the
    # common compounds are excluded; export-control phrasing (出口管制, 管制品, 受管制) still hits.
    ("control-zh", _P(r"(?<!品質|製程|生產|物料|庫存|進度|文件|變更|溫度|標示|流程|成本|數量|校正|版本|資料|製造|現場|外觀|不良|異常|程序|作業|倉庫|設備)"
                      r"管制(?!度|定|訂|止|裁|約|圖|界限|上限|下限|線|計畫|計劃|點|特性|參數|項目|標準|程序|流程|表|卡|站|中心|人員|員|措施|方法|範圍|區)")),
]
DLP_TIERS: dict[str, str] = {
    "confidential-zh": "T2", "confidential-en": "T2", "tw-ubn": "T2",
    "tw-national-id": "T2", "amount-ntd": "T2", "amount-usd": "T2", "amount-zh": "T2",
    "restricted-en": "T3", "restricted-zh": "T3", "defense-zh": "T3",
    "aerospace-zh": "T3", "military-zh": "T3", "medical-device-zh": "T3",
    "export-permit-zh": "T3", "export-control-en": "T3", "control-zh": "T3",
}


def valid_ubn(digits: str) -> bool:
    """Taiwan unified business number checksum (weights 12121241, mod 5)."""
    if len(digits) != 8 or not digits.isdigit():
        return False
    weights = (1, 2, 1, 2, 1, 2, 4, 1)
    total = 0
    for d, w in zip(digits, weights):
        p = int(d) * w
        total += p // 10 + p % 10
    if total % 5 == 0:
        return True
    return digits[6] == "7" and (total + 1) % 5 == 0


# A bare 8-digit number is a UBN only with a context cue within UBN_CUE_WINDOW characters.
# Strong cues decide on their own; weak cues (公司, 股份, 發票 ...) also need the number not to be
# a plausible 19xx/20xx YYYYMMDD date. Without a cue nothing trips (work orders, dates, part numbers).
UBN_CUE_WINDOW = 12
_UBN_STRONG = _P(r"統編|統一編號|(?i:vat|tax\s*id)")
_UBN_WEAK = _P(r"公司|股份|發票")
_PLAUSIBLE_DATE = _P(r"(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])")


def ubn_hit(text: str, m: re.Match) -> bool:
    """True when the 8-digit match `m` in `text` is a checksum-valid UBN with a context cue nearby."""
    if not valid_ubn(m.group(0)):
        return False
    near = text[max(0, m.start() - UBN_CUE_WINDOW):m.start()] + " " + text[m.end():m.end() + UBN_CUE_WINDOW]
    if _UBN_STRONG.search(near):
        return True
    return bool(_UBN_WEAK.search(near)) and not _PLAUSIBLE_DATE.fullmatch(m.group(0))


def find_secrets(text: str) -> list[str]:
    """Names of SECRET_PATTERNS that match `text` (no generic rule)."""
    return [name for name, pat in SECRET_PATTERNS if pat.search(text)]
