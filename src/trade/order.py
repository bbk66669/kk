from dotenv import load_dotenv; load_dotenv()
import os, threading
from typing import Optional, Literal, Dict, Any
import okx.Trade   as _okx_trade
import okx.Account as _okx_acct
from ..monitor.metrics import okx_fees_usdt_total         # Prometheus

_trade_lock, _acct_lock = threading.Lock(), threading.Lock()
_trade_cli = _acct_cli = None

def _trade() -> _okx_trade.TradeAPI:
    global _trade_cli
    with _trade_lock:
        if _trade_cli is None:
            _trade_cli = _okx_trade.TradeAPI(
                api_key=os.getenv("OKX_API_KEY", ""),
                api_secret_key=os.getenv("OKX_API_SECRET", ""),
                passphrase=os.getenv("OKX_API_PASSPHRASE", ""),
                flag=os.getenv("OKX_API_FLAG", "1"),
            )
        return _trade_cli

def _acct() -> _okx_acct.AccountAPI:
    global _acct_cli
    with _acct_lock:
        if _acct_cli is None:
            _acct_cli = _okx_acct.AccountAPI(
                api_key=os.getenv("OKX_API_KEY", ""),
                api_secret_key=os.getenv("OKX_API_SECRET", ""),
                passphrase=os.getenv("OKX_API_PASSPHRASE", ""),
                flag=os.getenv("OKX_API_FLAG", "1"),
            )
        return _acct_cli

def place_order(
    symbol: str,
    side: Literal["BUY", "SELL"],
    qty: float,
    *,
    td_mode: Literal["isolated", "cross"] = "isolated",
    leverage: Optional[float] = None,
    min_sz: float,
    lot_sz: float,
    reduce_only: bool = False,
) -> Dict[str, Any]:
    if qty < min_sz or abs((qty / lot_sz) - round(qty / lot_sz)) > 1e-8:
        return {"id": "", "status": "SIZE_TOO_SMALL", "api_response": {}}

    params: Dict[str, Any] = dict(
        instId   = symbol,
        tdMode   = td_mode,
        ordType  = "market",
        side     = side.lower(),
        sz       = str(qty),
        ccy      = "USDT",
        posSide  = "long" if side == "BUY" else "short",
    )
    if reduce_only:
        params["reduceOnly"] = "true"

    try:
        res = _trade().place_order(**params)
        data0 = (res.get("data") or [{}])[0]
        fee = abs(float(data0.get("fee", 0)))
        okx_fees_usdt_total.inc(fee)
        return {"id": data0.get("ordId", ""), "status": res.get("code", "X"), "api_response": res}
    except Exception as e:
        return {"id": "", "status": "EXCEPTION", "error": str(e)}

# ─────────────────────────────────────────────────────────────
# Trailing-Stop Algo Order（OKX 原生）
# ----------------------------------------------------------------
def place_algo_order_trailing_sl(
    symbol: str,
    side: Literal["BUY", "SELL"],          # 仍按开仓方向传进来
    trigger_px: str,
    callback_rate: str,
) -> Dict[str, Any]:
    """
    下原生 trailing-stop：
      trigger_px    = 开仓价
      callback_rate = "0.5" 表示 0.5 %
    """
    # 1. 计算平仓方向
    close_side = "sell" if side == "BUY" else "buy"
    pos_side   = "long" if side == "BUY" else "short"

    params: Dict[str, Any] = {
        "instId"       : symbol,
        "tdMode"       : "isolated",
        "side"         : close_side,          # **反向平仓**
        "posSide"      : pos_side,
        "ordType"      : "trailing_stop",     # ← 对应 OKX v5 文档
        "sz"           : "0",                 # OKX 要求填写，可填 0
        "triggerPx"    : trigger_px,          # 字段名改为 triggerPx
        "callbackRatio": callback_rate,       # "0.5" → 0.5 %
    }
    try:
        res = _trade().place_algo_order(**params)
        return res
    except Exception as e:
        print("❌ place_algo_order_trailing_sl 异常:", e)
        return {"code": "-1", "msg": str(e)}
