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
SIM_CAP    = float(os.getenv("SIM_CAPITAL", "300"))
RISK_PCT   = float(os.getenv("RISK_PCT", "0.01"))
SL_PCT     = float(os.getenv("SL_PCT", "0.01"))
TP_PCT     = float(os.getenv("TP_PCT", "0.02"))

# —— OKX 模拟盘客户端 ——  
client = TradeAPI(API_KEY, API_SECRET, API_PASS, flag="1")

async def get_price():
    bclient = await AsyncClient.create()
    bsm = BinanceSocketManager(bclient)
    ws = bsm.trade_socket("ETHUSDT")
    async with ws as stream:
        msg = await stream.recv()
        price = float(msg["p"])
    await bclient.close_connection()
    return price

async def run_demo():
    # 1. 初始价格
    price = await get_price()
    print(f"[INIT] price = {price:.2f}")

    # 2. 风控计算
    data60 = pd.Series([price] * 60)
    sigma  = compute_volatility(data60)
    lev    = calc_leverage(sigma)
    atr    = compute_atr(pd.Series([price]*5), pd.Series([price]*5), pd.Series([price]*5), n=5)
    raw    = calc_size(SIM_CAP, RISK_PCT, price) * lev
    size   = round(raw, 4) or 0.01
    sl0, tp0 = calc_sl_tp(price, SL_PCT, TP_PCT)
    print(f"📈 price={price:.2f}, size={size:.4f}, SL0={sl0:.2f}, TP0={tp0:.2f}")

    # 3. 市价开多（去掉 instType）
    open_r = client.place_order(
        instId=SYMBOL,
        tdMode="cross", side="buy", posSide="long",
        ordType="market", sz=str(size)
    )
    print("🥂 Open resp:", open_r)
    if open_r.get("code") != "0":
        return

    # 4. 初始算法止损单
    algo_r = client.place_algo_order(
        instId=SYMBOL, instType="SWAP",
        tdMode="cross", side="sell", posSide="long",
        ordType="conditional", sz=str(size),
        slTriggerPx=str(sl0), slOrdPx="-1",
        slTriggerPxType="last"
    )
    print("⏳ SL resp:", algo_r)
    if algo_r.get("code") != "0":
        return
    algo_id = algo_r["data"][0]["algoId"]
    current_sl = sl0

    # 5. 实时追踪 & 动态止损
    print("🌀 动态止损追踪启动…")
    bclient = await AsyncClient.create()
    bsm     = BinanceSocketManager(bclient)
    ws2     = bsm.trade_socket("ETHUSDT")

    async with ws2 as stream:
        while True:
            msg   = await stream.recv()
            price = float(msg["p"])
            print(f"[{time.strftime('%H:%M:%S')}] price={price:.2f}, SL={current_sl:.2f}")

            new_sl, _ = calc_trailing_sl(sl0, price, atr, size)
            if new_sl and new_sl > current_sl:
                current_sl = new_sl
                print(f"🔁 提升 SL → {current_sl:.2f}")
                # 取消旧止损单
                client.cancel_order(instId=SYMBOL, ordId=algo_id)
                # 重挂新止损单
                upd = client.place_algo_order(
                    instId=SYMBOL, instType="SWAP",
                    tdMode="cross", side="sell", posSide="long",
                    ordType="conditional", sz=str(size),
                    slTriggerPx=str(current_sl), slOrdPx="-1",
                    slTriggerPxType="last"
                )
                print("🔄 Upd SL resp:", upd)
                algo_id = upd["data"][0]["algoId"]

            if price <= current_sl:
                print(f"⚠️ 触发止损 {price:.2f} <= SL {current_sl:.2f}, 平仓")
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
