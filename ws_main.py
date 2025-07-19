#!/usr/bin/env python3
import warnings, asyncio, logging, os, time, json, signal

# ─── 全面屏蔽所有警告 ─────────────────────────────────────────────
warnings.simplefilter("ignore")

# ── Prometheus server ───────────────────────────────────────────
from prometheus_client import start_http_server
import os

try:
    port = int(os.getenv("METRICS_PORT", 8000))
    start_http_server(port, addr="0.0.0.0")
except OSError:
    pass

# ── 项目模块 ────────────────────────────────────────────────────
from src.utils.config_loader import load as load_cfg
from src.trade.market       import get_instrument_spec
from src.trade.order        import place_order
from src.agent.price_consumer import PriceConsumer
from src.agent.signal_filter  import SignalFilter
from src.agent.position_guard import PositionGuard
from src.agent.agent_decide_and_execute import agent_decide_and_execute
from src.trade.market_ws     import run_ws_main

# L1 本地推理 + 显著事件
from src.llm_local_client  import ask_local_llm
from src.event_classifier  import EventClassifier
from src.intent_cache      import hit_or_set

# Trailing-SL
from src.risk.trailing      import trailing_mgr
from src.monitor.metrics    import trailing_stop_hits_total
from src.storage.weaviate_client import get_client

# 监控指标
from src.monitor.metrics import (
    gpt_requests_total, gpt_latency_seconds,
    okx_fees_usdt_total, okx_orders_total,
    order_latency_seconds, equity_usdt
)

import openai, okx.Account as _acct

# ── 全局配置 / 对象 ─────────────────────────────────────────────
cfg        = load_cfg()
event_cls  = EventClassifier(**cfg["event_cls"])
openai.api_key = os.getenv("OPENAI_API_KEY")

_gpt_lock  = asyncio.Lock()
_BAL_CACHE = (0, 0.0)


# ───────────────────────────────────────────────────────────────
# 账户余额缓存
def _load_balance() -> float:
    global _BAL_CACHE
    ts, bal = _BAL_CACHE
    if time.time() - ts < 30:
        return bal
    cli = _acct.AccountAPI(
        api_key        = os.getenv("OKX_API_KEY", ""),
        api_secret_key = os.getenv("OKX_API_SECRET", ""),
        passphrase     = os.getenv("OKX_API_PASSPHRASE", ""),
        flag           = os.getenv("OKX_API_FLAG", "1"),
    )
    try:
        bal = float(cli.get_account_balance(ccy="USDT")["data"][0]["details"][0]["cashBal"])
    except Exception:
        bal = 0.0
    equity_usdt.set(bal)
    _BAL_CACHE = (time.time(), bal)
    return bal


# ───────────────────────────────────────────────────────────────
# GPT-4o 调用
async def llm_decide(price: float, pos: str | None, spec: dict):
    async with _gpt_lock:
        rh = spec.get("recent_high")   # 可能为 None
        rl = spec.get("recent_low")
        atr = float(rh.tail(14).mean() - rl.tail(14).mean()) if (rh is not None and rl is not None) else 0

        payload = {
            "price":    price,
            "position": pos or "FLAT",
            "balance":  _load_balance(),
            "atr":      atr
        }
        prompt = "策略输入: " + json.dumps(payload, ensure_ascii=False) + \
                 "\n输出 JSON: {\"side\":\"BUY|SELL|HOLD\",\"qty\":整数}"

        t0 = time.time()
        try:
            resp = await asyncio.to_thread(lambda: openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
                timeout=6
            ))
            gpt_latency_seconds.observe(time.time() - t0)
            gpt_requests_total.inc()
            data = json.loads(resp.choices[0].message.content)
            return data.get("side", "HOLD").upper(), prompt, data
        except Exception as e:
            logging.warning("GPT err %s", e)
            return "HOLD", prompt, {"err": str(e)}


# ───────────────────────────────────────────────────────────────
# Broker（极简版）
class RealBroker:
    def __init__(self):
        self.symbol = cfg["trade"]["symbol"]
        self.spec   = get_instrument_spec(self.symbol)
        self.min_sz = self.spec["min_sz"]
        self.lot_sz = self.spec["lot_sz"]

    async def open_long(self, qty=None, price=None):
        return await asyncio.to_thread(place_order,
            self.symbol, "BUY", max(qty or 1, self.min_sz),
            min_sz=self.min_sz, lot_sz=self.lot_sz)

    async def open_short(self, qty=None, price=None):
        return await asyncio.to_thread(place_order,
            self.symbol, "SELL", max(qty or 1, self.min_sz),
            min_sz=self.min_sz, lot_sz=self.lot_sz)

    async def close_all(self):
        pass


broker = RealBroker()


# ───────────────────────────────────────────────────────────────
async def price_feeder(q: asyncio.Queue[float]):
    async def on_tick(*a, **k):
        await q.put(float(a[0] if a else k["price"]))
    while True:
        try:
            await run_ws_main(on_tick)
        except Exception as e:
            logging.warning("WS crash %s – reconnecting in 5 s", e)
            await asyncio.sleep(5)


# ───────────────────────────────────────────────────────────────
async def main():
    q     = asyncio.Queue(maxsize=1000)
    last  = None

    asyncio.create_task(price_feeder(q))
    filt = SignalFilter(**cfg["signal"])

    signal.signal(signal.SIGHUP, lambda *_: cfg.update(load_cfg()))

    while True:
        price = await q.get()
        last  = last or price

        if trailing_mgr().update(price):
            trailing_stop_hits_total.inc()
            await broker.close_all()
            await PositionGuard().reset()

            try:
                cli = get_client()
                col = cli.collections.get("TradeLog")
                uuid = col.query.fetch_objects(limit=1)[0].uuid
                col.data.update(uuid, {"trail_sl_hit": "true"})
            except Exception:
                pass
            last = price
            continue

        direction = "BUY" if price > last else "SELL" if price < last else "HOLD"
        if filt.push(direction):
            pos = await PositionGuard().get()

            cache_key = {"sym": broker.symbol, "side": direction,
                         "zone": round(price * 500) / 500}
            significant = event_cls.push(price) and not hit_or_set(cache_key)

            if significant:
                sig, prompt, extra = await llm_decide(price, pos, broker.spec)
            else:
                raw, _ = await ask_local_llm(f"eth price {price:.2f}, answer BUY SELL HOLD")
                sig, prompt, extra = raw.strip().upper()[:4], "gemma quick", {"gemma_raw": raw}

            await agent_decide_and_execute(sig, price, broker,
                                           prompt=prompt, extra=extra)
        last = price


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(main())