import asyncio, time, logging
from typing import Callable, Awaitable

Number  = float | int
Logger  = logging.Logger

class PriceConsumer:
    """
    高频行情队列 -> 降频触发。聚合窗口内只取最后一价。
    """
    def __init__(
        self,
        queue: asyncio.Queue[Number],
        callback: Callable[[Number], Awaitable[None]],
        *,
        pct_trigger: float = 0.003,
        agg_window: float = 1.0,
        logger: Logger | None = None,
    ) -> None:
        self.q = queue
        self.cb = callback
        self.pct_trigger = pct_trigger
        self.agg_window = agg_window
        self._last_emit_price: Number | None = None
        self._last_emit_ts:  float = 0.0
        self.log = logger or logging.getLogger("PriceConsumer")

    async def run(self) -> None:
        window_prices: list[Number] = []
        next_tick = time.time() + self.agg_window

        while True:
            try:
                timeout = max(0.0, next_tick - time.time())
                price: Number = await asyncio.wait_for(self.q.get(), timeout=timeout)
                window_prices.append(price)
                # 价格突变立即 emit
                if self._should_emit(price):
                    await self._emit(price)
                    window_prices.clear()
                    next_tick = time.time() + self.agg_window
            except asyncio.TimeoutError:
                # 窗口到期 emit
                if window_prices:
                    await self._emit(window_prices[-1])
                    window_prices.clear()
                next_tick = time.time() + self.agg_window
            except Exception as e:
                self.log.exception("PriceConsumer error: %s", e)
                await asyncio.sleep(1)

    def _should_emit(self, price: Number) -> bool:
        if self._last_emit_price is None:
            return True
        return abs(price - self._last_emit_price) / self._last_emit_price >= self.pct_trigger

    async def _emit(self, price: Number) -> None:
        await self.cb(price)
        self._last_emit_price = price
        self._last_emit_ts   = time.time()
