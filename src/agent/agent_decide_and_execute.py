import json, time, logging
from typing import Literal, Protocol, Optional

from .position_guard import PositionGuard
from ..monitor.metrics import (
    okx_orders_total, order_latency_seconds, equity_usdt
)
from ..monitor.metrics  import trailing_stop_hits_total
from ..risk.trailing    import trailing_mgr
from ..storage.ensure_schema import ensure_schema
from ..storage.weaviate_client import get_client

Signal = Literal["BUY", "SELL", "HOLD"]


class BrokerAPI(Protocol):
    async def open_long (self, qty: Optional[float] = None, price: float | None = None): ...
    async def open_short(self, qty: Optional[float] = None, price: float | None = None): ...
    async def close_all (self): ...
    symbol: str


_client = None
ensure_schema()
def _weaviate():
    global _client
    if _client is None:
        _client = get_client()
    return _client


async def agent_decide_and_execute(
    signal: Signal, price: float, broker: BrokerAPI,
    *, qty: Optional[float] = None, prompt: str = "",
    extra: dict | None = None, logger: logging.Logger | None = None,
) -> None:
    log = logger or logging.getLogger("Agent")
    curr_dir = await PositionGuard().get()

    if signal == "HOLD" or curr_dir == signal:
        return

    if curr_dir and curr_dir != signal:
        await broker.close_all()
        trailing_mgr().cancel()
        await PositionGuard().reset()

    t0 = time.time()
    res = await (broker.open_long if signal == "BUY" else broker.open_short)(
        qty=qty, price=price
    )
    order_latency_seconds.observe(time.time() - t0)
    okx_orders_total.labels(signal).inc()

    from src.utils.config_loader import load as _load_cfg
    pct = _load_cfg().get("risk", {}).get("trail_sl_pct", 0.0)
    if pct > 0:
        trailing_mgr().start(signal, price, pct)

    await PositionGuard().update(signal)

    pnl    = float(extra.get("pnl", 0))    if extra else 0
    equity = float(extra.get("equity", 0)) if extra else 0
    if equity: equity_usdt.set(equity)

    try:
        _weaviate().collections.get("TradeLog").data.insert({
            "timestamp":            int(time.time() * 1000),
            "symbol":               broker.symbol,
            "signal":               signal,
            "price":                price,
            "size":                 qty,
            "leverage":             getattr(broker, "leverage", None),
            "order_id":             res.get("id", ""),
            "status":               res.get("status", ""),
            "prompt":               prompt,
            "extra":                json.dumps(extra or {}),
            "pnl_realized":         pnl,
            "equity":               equity,
            "trail_sl_pct":         pct,
            "trail_sl_hit":         "false",
        })
    except Exception as e:
        log.warning("Weaviate insert failed: %s", e)
