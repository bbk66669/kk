#!/usr/bin/env python3
from storage.weaviate_client import get_client, ensure_schema
import datetime, json
import random

def main():
    client = get_client()
    ensure_schema()

    # 示例：参数优化，可以替换为自动扫描/AI推荐逻辑
    # 这里暂用随机参数以便跑通自动化闭环
    recommended = {
        "risk_pct": round(random.uniform(0.005, 0.03), 4)
        # 后续可扩展更多参数，如 sl_pct, tp_pct, threshold 等
    }

    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "symbol": "ETH-USDT",
        "strategy_name": "llm_basic",
        "strategy_params": json.dumps(recommended),
        "ai_response": "RECOMMEND"
    }

    collection = client.collections.get("TradeLog")
    collection.data.insert(entry)

    client.close()
    print("✅ AI 参数推荐已写入", recommended)

if __name__ == "__main__":
    main()
