#!/usr/bin/env python3
"""
本地 Trailing-Stop 管理器（单合约单方向）

• start(side, entry, pct)  创建/覆盖
• update(price)            推入最新价，若触发回撤返回 True
"""
import logging
from typing import Literal, Optional

Side = Literal["BUY", "SELL"]


class TrailingStop:
    def __init__(self) -> None:
        self.side:   Optional[Side] = None     # 当前方向
        self.best:   float | None    = None    # BUY→最高价；SELL→最低价
        self.pct:    float           = 0.0     # 回撤百分比 (0-1)
        self.active: bool            = False
        self.log = logging.getLogger("TrailingSL")

    # ────────────────────────── API ──────────────────────────
    def start(self, side: Side, entry: float, pct: float) -> None:
        """开启 / 覆盖"""
        self.side, self.best, self.pct, self.active = side, entry, pct, True
        self.log.info("⛓️  Trailing-SL start %s entry=%.4f pct=%.2f%%",
                      side, entry, pct * 100)

    def cancel(self) -> None:
        if self.active:
            self.log.info("✂️  Trailing-SL cancel")
        self.active = False

    def update(self, price: float) -> bool:
        """推入最新价；触发回撤则返回 True"""
        if not self.active:
            return False

        # 1) 刷新极值
        if self.side == "BUY":
            if price > self.best:
                self.best = price
        else:                                # SELL
            if price < self.best:
                self.best = price

        # 2) 计算回撤百分比
        drawdown = ((self.best - price) / self.best
                    if self.side == "BUY"
                    else (price - self.best) / self.best)

        if drawdown >= self.pct:
            self.log.info("🚨 Trailing-SL hit! best=%.4f now=%.4f dd=%.2f%%",
                          self.best, price, drawdown * 100)
            self.active = False
            return True
        return False


# ——— 全局单例 ———
_trailing = TrailingStop()
def trailing_mgr() -> TrailingStop:
    return _trailing
