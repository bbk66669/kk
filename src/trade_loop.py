import os
from dotenv import load_dotenv

# 步骤一：加载环境变量（会自动在脚本/当前目录找 .env）
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# 步骤二：强制 print 校验
print("API_KEY:", os.getenv("OKX_API_KEY"))
print("API_SECRET:", os.getenv("OKX_API_SECRET"))
print("PASSPHRASE:", os.getenv("OKX_API_PASSPHRASE"))

# === 下面保留原有主循环逻辑 ===
import time
import traceback
from agent.llm_agent import agent_decide_and_execute
from trade.market import get_latest_price

SYMBOL = "ETH-USDT"
CAPITAL = 1000
RISK_PCT = 0.01
INTERVAL = 10

def main():
    while True:
        try:
            price = get_latest_price(SYMBOL)
            agent_decide_and_execute(SYMBOL, price, CAPITAL, RISK_PCT)
        except Exception as e:
            print("❗️主控异常：", e)
            traceback.print_exc()
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
