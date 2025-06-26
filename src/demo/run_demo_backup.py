#!/usr/bin/env python3
import os, asyncio, pandas as pd
from dotenv import load_dotenv
from okx.Trade import TradeAPI
from binance import AsyncClient, BinanceSocketManager
from risk.manager import calc_size, calc_sl_tp
from risk.dynamic import compute_volatility, calc_leverage, compute_atr, calc_trailing_sl

load_dotenv()
client = TradeAPI(os.getenv("OKX_API_KEY"), os.getenv("OKX_API_SECRET"), os.getenv("OKX_API_PASSPHRASE"), "1")

async def run_demo():
    bcl = await AsyncClient.create()
    ws = BinanceSocketManager(bcl).trade_socket("ETHUSDT")
    async with ws as s: price = float((await s.recv())["p"])
    await bcl.close_connection()

    sigma = compute_volatility(pd.Series([price]*60))
    lev = calc_leverage(sigma)
    atr = compute_atr(pd.Series([price]*5), pd.Series([price]*5), pd.Series([price]*5), n=5)

    cap, pct = float(os.getenv("SIM_CAPITAL","300")), float(os.getenv("RISK_PCT","0.01"))
    raw = calc_size(cap, pct, price) * lev
    lot = 0.01
    units = int(raw/lot) or 1
    size = units * lot
    sl0, tp0 = calc_sl_tp(price, float(os.getenv("SL_PCT","0.01")), float(os.getenv("TP_PCT","0.02")))

    print(f"Price {price:.2f}, size {size}, SL0={sl0}")

    resp = client.place_order(
        instId="ETH-USDT-SWAP", tdMode="cross",
        side="buy", posSide="long",
        ordType="market", sz=str(size)
    )
    print("Open resp:", resp)

    algo = client.place_algo_order(
        instId="ETH-USDT-SWAP", tdMode="cross",
        side="sell", posSide="long",
        ordType="conditional", sz=str(size),
        slTriggerPx=str(sl0), slOrdPx="-1", slTriggerPxType="last"
    )
    print("Algo resp:", algo)
    algo_id = algo["data"][0].get("algoId")
    print("Algo ID:", algo_id or "—fail—")

if __name__ == "__main__":
    asyncio.run(run_demo())
