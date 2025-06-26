"""
LLM 决策 + 动态风控 + 下单 + 因果日志
设计初心：日志本质上应只记录“真实交易行为”和“决策因果链”，
而不是高频“无效信号”（如 HOLD）——否则未来所有回测、分析、AI 策略训练都会被噪声严重污染，丧失可用性。
只记录真实下单和关键分叉（如风控拒单、极端错误等），保证日志成为高价值因果链。
"""

import os, time, json, random, warnings
from typing import Literal, Dict, Any

warnings.filterwarnings("ignore", category=ResourceWarning)

from storage.weaviate_client import get_client
from trade.order   import place_order
from trade.market  import get_latest_price, get_instrument_spec
from risk.dynamic  import compute_volatility, compute_atr, calc_initial_sl
from risk.manager  import calc_size, calc_sl_tp

def agent_decide_and_execute(
    symbol: str,
    price: float | None,
    capital: float,
    risk_pct: float,
    *,
    mode: Literal["random", "llm", "fix_buy", "fix_sell"] = "random",
    kappa: float = 1.5,
    l_max: float = 100,
    log_collection: str = "TradeLog",
) -> None:
    # 0. 价格校验
    if price is None:
        print("⚠️  无法获取实时价格，本轮跳过")
        return

    # 1. AI / 随机 / 固定信号
    prompt = f"当前 {symbol} 价格 {price:.4f}，请判断：买/卖/观望？"
    if mode == "fix_sell":
        signal = "SELL"
    elif mode == "fix_buy":
        signal = "BUY"
    elif mode == "random":
        signal = random.choice(("BUY", "SELL", "HOLD"))
    else:  # llm
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            r = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"user","content":prompt}],
                timeout=6
            )
            signal = r.choices[0].message.content.strip().upper()
            if signal not in ("BUY", "SELL", "HOLD"):
                signal = "HOLD"
        except Exception as e:
            print("⚠️  LLM 调用失败，改用随机信号:", e)
            signal = random.choice(("BUY", "SELL", "HOLD"))

    # 2. 只在“真实决策”情况下记录日志：HOLD 不记录任何日志
    if signal == "HOLD":
        return  # 不写日志，不下单，直接跳过，避免噪声污染因果链

    # 3. 取合约规格
    spec = get_instrument_spec(symbol)   # {ct_val,min_sz,lot_sz,period_sec}
    ct_val, min_sz, lot_sz = spec["ct_val"], spec["min_sz"], spec["lot_sz"]

    # 4. 动态杠杆 & 止损
    kline = spec["recent_prices"]        # Pandas Series；需由 get_instrument_spec 带回
    sigma = compute_volatility(kline, spec["period_sec"])
    leverage = max(1, min(kappa / sigma if sigma else 1, l_max))
    leverage = float(leverage)   # 让 JSON 不带 np.float64

    atr   = compute_atr(spec["recent_high"], spec["recent_low"], kline)
    stop  = calc_initial_sl(price, atr, signal)
    stop_dist = abs(price - stop)

    # 极端值保护，只记录因果链关键分支
    if sigma == 0 or atr == 0 or stop_dist == 0:
        print(f"⚠️ ATR或σ或止损距离为0，本轮跳过。sigma={sigma}, atr={atr}, stop_dist={stop_dist}")
        _write_log(prompt, symbol, price, signal, 0, stop, leverage,
                   _extra(capital, risk_pct, leverage, sigma, atr, 0, 0, ct_val,
                          min_sz, lot_sz, stop_dist),
                   "EXTREME_ZERO", log_collection)
        return

    # 5. 计算张数
    size_raw = (capital * risk_pct) / (stop_dist * ct_val)
    size = calc_size(
        capital       = capital,
        risk_pct      = risk_pct,
        entry_price   = price,
        stop_price    = stop,
        ct_val        = ct_val,
        min_sz        = min_sz,
        lot_sz        = lot_sz,
    )
    if size == 0:
        print("size < minSz，放弃本单")
        _write_log(prompt, symbol, price, signal, 0, stop, 0,
                   _extra(capital, risk_pct, leverage, sigma, atr, size_raw, size, ct_val,
                          min_sz, lot_sz, stop_dist),
                   "SIZE_TOO_SMALL", log_collection)
        return

    # 6. 下单
    order = place_order(
        symbol   = symbol,
        side     = signal,
        qty      = size,
        leverage = leverage,
        td_mode  = "isolated",
        min_sz   = min_sz,
        lot_sz   = lot_sz,
    )
    status = order.get("status")

    # 7. 写日志（只在真实有意义决策分支）
    _write_log(prompt, symbol, price, signal, size, stop, leverage,
               _extra(capital, risk_pct, leverage, sigma, atr, size_raw, size, ct_val,
                      min_sz, lot_sz, stop_dist),
               status, log_collection, order_id=order.get("id",""))

# ----------------------------------------------------------------------
# Helper: 统一写日志
# ----------------------------------------------------------------------
def _extra(capital, risk_pct, leverage, sigma, atr, size_raw, size, ct_val,
           min_sz, lot_sz, stop_dist) -> Dict[str, Any]:
    return {
        "capital": capital, "risk_pct": risk_pct, "leverage": leverage,
        "sigma": sigma, "atr": atr,
        "size_raw": size_raw, "size_final": size,
        "ct_val": ct_val, "min_sz": min_sz, "lot_sz": lot_sz,
        "stop_dist": stop_dist,
    }

def _write_log(prompt, symbol, price, signal, size, stop, lev, extra, status,
               log_collection, order_id="") -> None:
    log = {
        "timestamp": int(time.time() * 1000),  # 当前毫秒级 Unix 时间戳
        "symbol": symbol, "price": price, "signal": signal,
        "size": size, "stop": stop, "leverage": lev,
        "status": status, "order_id": order_id,
        "prompt": prompt, "extra": json.dumps(extra, ensure_ascii=False),
    }
    try:
        cli = get_client(); cli.collections.get(log_collection).data.insert(log); cli.close()
    except Exception as e:
        print("⚠️ 写入日志失败:", e)
    print("✅ 因果日志:", log)
