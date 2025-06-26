#!/usr/bin/env python3
import os
import sys
import time
import json
import asyncio
import pandas as pd
from dotenv import load_dotenv
from binance import AsyncClient, BinanceSocketManager
from okx.Trade import TradeAPI

# —— 项目路径 & 本地模块 ——  
PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT, "src"))
from risk.manager import calc_size, calc_sl_tp
from risk.dynamic import compute_volatility, calc_leverage, compute_atr, calc_trailing_sl

# —— 环境变量 ——  
load_dotenv(os.path.join(PROJECT, ".env"))
API_KEY    = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASS   = os.getenv("OKX_API_PASSPHRASE")
SYMBOL     = "ETH-USDT-SWAP"
SIM_CAP    = float(os.getenv("SIM_CAPITAL","300"))
RISK_PCT   = float(os.getenv("RISK_PCT","0.01"))
SL_PCT     = float(os.getenv("SL_PCT","0.01"))
TP_PCT     = float(os.getenv("TP_PCT","0.02"))
LOT_SIZE   = 0.01  # 最小下单单位

# —— OKX 模拟盘客户端 ——  
client = TradeAPI(API_KEY, API_SECRET, API_PASS, flag="1")

# —— 获取实时价格 ——  
async def get_price():
    bclient = await AsyncClient.create()
    bsm = BinanceSocketManager(bclient)
    ws = bsm.trade_socket("ETHUSDT")
    async with ws as s:
        msg = await s.recv()
        price = float(msg["p"])
    await bclient.close_connection()
    return price

# —— 主流程 ——  
async def run_demo():
    # 1️⃣ 初始行情
    entry_price = await get_price()
    print(f"[INIT] price = {entry_price:.2f}")

    # 2️⃣ 风控参数
    data60 = pd.Series([entry_price]*60)
    sigma  = compute_volatility(data60)
    lev    = calc_leverage(sigma)
    atr    = compute_atr(pd.Series([entry_price]*5),
                        pd.Series([entry_price]*5),
                        pd.Series([entry_price]*5), n=5)

    raw_qty = calc_size(SIM_CAP, RISK_PCT, entry_price) * lev
    units   = max(1, int(raw_qty / LOT_SIZE))
    size    = units * LOT_SIZE

    sl0, tp0 = calc_sl_tp(entry_price, SL_PCT, TP_PCT)
    print(f"📈 entry={entry_price:.2f}, size={size:.4f}, SL0={sl0:.2f}, TP0={tp0:.2f}")

    # 3️⃣ 市价开多
    open_r = client.place_order(
        instId=SYMBOL,
        tdMode="cross", side="buy", posSide="long",
        ordType="market", sz=str(size)
    )
    print("🥂 Open resp:", open_r)
    if open_r.get("code") != "0":
        return

    # 4️⃣ 初始算法止损
    algo_r = client.place_algo_order(
        instId=SYMBOL,
        tdMode="cross", side="sell", posSide="long",
        ordType="conditional", sz=str(size),
        slTriggerPx=str(sl0), slOrdPx="-1",
        slTriggerPxType="last"
    )
    print("⏳ SL resp:", algo_r)
    if algo_r.get("code") != "0":
        return
    algo_id    = algo_r["data"][0]["algoId"]
    current_sl = sl0

    # 5️⃣ 动态追踪止损
    print("🌀 动态止损追踪启动…")
    bclient = await AsyncClient.create()
    bsm     = BinanceSocketManager(bclient)
    ws2     = bsm.trade_socket("ETHUSDT")

    async with ws2 as s:
        while True:
            msg   = await s.recv()
            price = float(msg["p"])
            print(f"[{time.strftime('%H:%M:%S')}] price={price:.2f}, SL={current_sl:.2f}")

            new_sl, _ = calc_trailing_sl(entry_price, price, atr, size)
            if new_sl and new_sl > current_sl:
                current_sl = new_sl
                print(f"🔁 SL上移至 {current_sl:.2f}")
                # 取消旧止损单
                client.cancel_order(instId=SYMBOL, ordId=algo_id)
                # 重挂新止损单
                upd = client.place_algo_order(
                    instId=SYMBOL,
                    tdMode="cross", side="sell", posSide="long",
                    ordType="conditional", sz=str(size),
                    slTriggerPx=str(current_sl), slOrdPx="-1",
                    slTriggerPxType="last"
                )
                print("🔄 Upd SL resp:", upd)
                algo_id = upd["data"][0]["algoId"]

            if price <= current_sl:
                print(f"⚠️ 触发止损 {price:.2f} <= {current_sl:.2f}，平仓")
                close_r = client.place_order(
                    instId=SYMBOL,
                    tdMode="cross", side="sell", posSide="long",
                    ordType="market", sz=str(size)
                )
                print("🏁 Close resp:", close_r)
                break

    await bclient.close_connection()

if __name__ == "__main__":
    asyncio.run(run_demo())
