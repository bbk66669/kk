# schema.py: structured log template for each trade
from typing import Any, Dict

TradeLogTemplate = {
    "timestamp": str,
    "symbol": str,
    "signal": str,
    "price": float,
    "strategy_name": str,
    "strategy_params": Dict[str, Any],
    "prompt": str,
    "ai_response": str,
    "order_id": str,
    "size": float,
    "sl": float,
    "tp": float,
    "order_status": str,
    "close_timestamp": str,
    "close_price": float,
    "pnl": float,
    "context": str,
}
