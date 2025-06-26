from trade.market import get_latest_price
from trade.order import place_order, SIDE_BUY, SIDE_SELL
from risk.manager import calc_size, calc_sl_tp
from storage.weaviate_client import get_client
from datetime import datetime, timezone
import random

def generate_signal(params):
    # 如果传mode则按mode，否则随机
    mode = params.get("mode", "random")
    if mode == "stub":
        return "HOLD"  # 可以用来测试主流程
    if mode == "random":
        return random.choice(["BUY", "SELL", "HOLD"])
    # 预留更多AI/LLM/策略入口
    return "HOLD"

def execute_signal(symbol: str, signal: str, capital: float, risk_pct: float, sl_pct=0.01, tp_pct=0.02):
    price = get_latest_price(symbol)
    client = get_client()
    try:
        collection = client.collections.get("TradeLog")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        size = calc_size(capital, risk_pct, price)
        sl, tp = calc_sl_tp(price, sl_pct, tp_pct)
        order = {}
        order_status = "NOSIGNAL"
        if signal in ("BUY", "SELL"):
            order = place_order(symbol, signal, size, "MARKET")
            order_status = "FILLED"

        log = {
            "timestamp": ts,
            "symbol": symbol,
            "price": price,
            "signal": signal,
            "size": size,
            "sl": sl,
            "tp": tp,
            "strategy_name": "agent_stub",
            "strategy_params": str({"risk_pct": risk_pct, "sl_pct": sl_pct, "tp_pct": tp_pct}),
            "order_id": order.get("id",""),
            "order_status": order_status,
            "close_timestamp": "",
            "close_price": 0.0,
            "pnl": 0.0,
        }
        collection.data.insert(log)
        print("✅ stub日志已写入：", log)
    finally:
        client.close()
