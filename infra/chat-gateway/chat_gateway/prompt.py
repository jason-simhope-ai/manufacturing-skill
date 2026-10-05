"""Compiled twin prompt budget and token estimate (§5.5, §10.1).

`team/tools/build.py` (`teamlib/compile.py` `_render_prompt`) owns prompt assembly; the gateway
only enforces the byte budget at load (and re-checks `promptSha` per call).
"""
from __future__ import annotations

PROMPT_BUDGET_BYTES = 12_000


def estimate_tokens(text: str) -> int:
    """Byte-free token estimate used across the repo: CJK chars + other chars / 4."""
    cjk = sum(1 for ch in text if "　" <= ch <= "鿿" or "＀" <= ch <= "￯")
    return cjk + -(-(len(text) - cjk) // 4)
