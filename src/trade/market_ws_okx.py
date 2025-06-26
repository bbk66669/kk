import asyncio, json, os, time
import websockets
from dotenv import load_dotenv

# 加载 .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"

async def subscribe_okx():
    async with websockets.connect(OKX_WS_URL) as ws:
        await ws.send(json.dumps({
            "op": "subscribe",
            "args": [{"channel": "tickers", "instType": "SPOT", "instId": "ETH-USDT"}]
        }))
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已发送订阅请求，开始接收…")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            # 如果是订阅确认或心跳，就打印一下或跳过
            if data.get("event") in ("subscribe", "error", "heartbeat"):
                print("系统消息：", data)
                continue
            # 只有当存在实际行情数据时才处理
            if data.get("arg", {}).get("channel") == "tickers" and "data" in data:
                d = data["data"][0]
                print(f"[OKX {d['ts']}] {d['instId']} 最后价 = {d['last']}")
            else:
                # 其它消息暂不处理
                continue

if __name__ == "__main__":
    asyncio.run(subscribe_okx())
