"""
动态风控工具 – Trailing Stop-Loss（A-lite）
"""
from typing import Literal

Signal = Literal["BUY", "SELL"]

def build_trailing_sl_params(
    side: Signal,
    entry_price: float,
    trail_sl_pct: float,
) -> dict:
    """
    返回 OKX 原生 trailing-stop 所需字段：
      - triggerPx    : 开仓价
      - callbackRate : 百分比 (例 0.5% → "0.5")
    """
    return {
        "triggerPx"   : str(entry_price),
        "callbackRate": f"{trail_sl_pct*100:.3f}",   # OKX 需字符串 %
        "algoOrdType" : "trailing_stop",
        "side"        : side.lower(),
        "tpTriggerPx" : "",
        "slTriggerPx" : "",
    }
