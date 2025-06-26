import asyncio, os
from dotenv import load_dotenv
from binance import AsyncClient, BinanceSocketManager

# 加载 .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

async def subscribe_binance():
    client = await AsyncClient.create()
    bsm = BinanceSocketManager(client)
    socket = bsm.trade_socket("ETHUSDT")
    print("已连接 Binance WebSocket，开始打印所有消息…")
    async with socket as s:
        while True:
            msg = await s.recv()
            print(msg)  # 直接打印原始 dict
    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(subscribe_binance())
