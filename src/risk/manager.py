"""
风险管理核心
- 按「风险单位 r = capital × risk_pct」反推张数
- 对齐 lot_size，若不足 min_sz 返回 0（放弃下单）
"""

import math
from typing import Literal, Tuple

# ----------------------------------------------------------------------
# 1. 仓位计算 — 风险单位法
# ----------------------------------------------------------------------
def calc_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
    *,
    ct_val: float,   # 1 张合约面值（ETH/USDT…）
    min_sz: float,   # 交易所最小张数（允许小数）
    lot_sz: float,   # 步进张数（允许小数）
) -> float:
    """
    根据风险单位 r 计算张数:
        r = capital × risk_pct
        contracts_raw = r / (|entry - stop| × ct_val)
    取 floor 对齐 lot_sz；若 < min_sz ⇒ 返回 0（不下单）
    """
    stop_dist = abs(entry_price - stop_price)
    if stop_dist == 0:
        return 0

    # 理论张数
    contracts = (capital * risk_pct) / (stop_dist * ct_val)

    # 步进向下取整
    contracts = math.floor(contracts / lot_sz) * lot_sz

    # 最终张数，若不够最小张数则为 0
    return contracts if contracts >= min_sz else 0

# ----------------------------------------------------------------------
# 2. 固定百分比 SL / TP（如需动态请用 risk.dynamic）
# ----------------------------------------------------------------------
def calc_sl_tp(
    entry_price: float,
    sl_pct: float,
    tp_pct: float,
    side: Literal["BUY", "SELL"] = "BUY",
) -> Tuple[float, float]:
    if side == "BUY":
        sl = entry_price * (1 - sl_pct)
        tp = entry_price * (1 + tp_pct)
    else:
        sl = entry_price * (1 + sl_pct)
        tp = entry_price * (1 - tp_pct)
    return round(sl, 8), round(tp, 8)
