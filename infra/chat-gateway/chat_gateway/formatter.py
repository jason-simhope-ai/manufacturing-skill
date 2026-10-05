"""Reply formatting (§8, §9.4): 【title】 prefix, show-your-work, 🧭 block, footer.

The formatter only lays out gateway-validated fields; `sanitize.filter_output`
runs on the result afterwards.
"""
from __future__ import annotations

from .drivers.base import TwinResult

CATEGORY_LABEL = {"strengthen": "強化既有優勢", "create": "創造新能力", "outsource": "外包既有工作"}
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
GENERIC_DECISION = "最終決定由你做（分身未列出決策點，已由 gateway 補上）"


def prefix(title: str) -> str:
    return f"【{title}】"


def format_reply(title: str, autonomy: str, result: TwinResult, *, category: str | None,
                 seq: int, tainted: bool = False, add_generic_decision: bool = False,
                 suggest_title: str | None = None) -> str:
    lines = [f"{prefix(title)}· {autonomy}"]
    if tainted:
        lines.append("⚠️ 本回合含未信任內容：連結已剝除、不發核准卡、權限上限 suggest")
    body = result.reply.strip()
    if autonomy == "draft" and not body.startswith("DRAFT"):
        body = "DRAFT " + body              # draft output is always labelled (§6)
    lines.append(f"結論：{body}")
    if result.citations:
        lines.append("依據：" + "；".join(result.citations))
    show = [f"[ASSUMED] {a}" for a in result.assumed]
    if result.unverified:
        show.append("未查證：" + "、".join(result.unverified))
    if show:
        lines.append("；".join(show))
    dps = list(result.decision_points) or ([GENERIC_DECISION] if add_generic_decision else [])
    if dps:
        lines.append("🧭 需要你判斷：" + " ".join(f"{CIRCLED[i % 10]} {d}" for i, d in enumerate(dps)))
    if suggest_title:
        lines.append(f"建議詢問 {prefix(suggest_title)}（請自行 @，分身不代為轉交）")
    footer = [f"信心：{result.confidence}"]
    if category:
        footer.append(f"分類：{CATEGORY_LABEL.get(category, category)}")
    footer.append(f"稽核 #{seq}")
    lines.append(" · ".join(footer))
    return "\n".join(lines)


def notice(title: str | None, text: str, seq: int) -> str:
    """Gateway-authored notice (refusals, rate limits, failures)."""
    head = f"{prefix(title)}" if title else "【gateway】"
    return f"{head}{text}（#{seq}）"
