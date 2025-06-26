#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
from storage.weaviate_client import ensure_schema
ensure_schema()  # 启动时自动确保TradeLog表结构

"""
LLM-Driven Trading Demo 入口
- 只调度：CLI → 最新价 → agent_decide_and_execute
- 杠杆、止损、止盈均在 llm_agent 内部动态生成，本脚本不再传这些参数
"""

import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

import time
import argparse
from trade.market import get_latest_price
from agent.llm_agent import agent_decide_and_execute

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LLM-Driven Trading Demo")
    p.add_argument("--symbol",   default="ETH-USDT-SWAP")
    p.add_argument("--capital",  type=float, default=300,  help="可用本金 USDT")
    p.add_argument("--risk_pct", type=float, default=0.01, help="单笔风险占比")
    # --leverage / --sl_pct / --tp_pct 已由动态风控接管，保留 CLI 但不再下传
    p.add_argument("--leverage", type=float, default=10,   help="初始杠杆上限(保留占位)")
    p.add_argument("--mode", choices=("random", "llm", "fix_buy", "fix_sell"),
                   default="random", help="信号来源")
    p.add_argument("--loops", type=int, default=1,  help="循环次数")
    p.add_argument("--sleep", type=float, default=2, help="循环间隔秒")
    return p.parse_args()

def main() -> None:
    args = parse_args()
    for i in range(args.loops):
        price = get_latest_price(args.symbol)
        print(f"[{i+1}/{args.loops}] 当前价格：{price}")
        agent_decide_and_execute(
            symbol   = args.symbol,
            price    = price,
            capital  = args.capital,
            risk_pct = args.risk_pct,
            mode     = args.mode,
        )
        if i < args.loops - 1:
            time.sleep(args.sleep)

if __name__ == "__main__":
    main()
