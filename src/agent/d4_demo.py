#!/usr/bin/env python3
# src/agent/d4_demo.py

import os
import sys
from dotenv import load_dotenv
from trade.market import get_latest_price
from agent.agent_stub import generate_signal, execute_signal

def main():
    load_dotenv()

    symbol = "ETH-USDT"
    capital = 1000.0
    risk_pct = 0.01

    price = get_latest_price(symbol)
    print(f"当前价格：{price}")

    # 支持命令行切换信号生成模式（如random、stub等，便于后续扩展）
    mode = sys.argv[1] if len(sys.argv) > 1 else "stub"
    params = {"price": price, "mode": mode}
    signal = generate_signal(params)
    print(f"Stub Agent 信号：{signal}")

    execute_signal(symbol, signal, capital, risk_pct)

if __name__ == "__main__":
    main()
