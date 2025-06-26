import asyncio, json, os, logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

async def _safe_callback(cb, price, src=""):
    try:
        if asyncio.iscoroutinefunction(cb):
            await cb(price, src)
        else:
            await asyncio.get_running_loop().run_in_executor(None, cb, price, src)
    except Exception:
        logging.exception("Callback error")

async def binance_ws_price(symbol="ETHUSDT", callback=None, backoff=5):
    from binance import AsyncClient, BinanceSocketManager
    while True:
        client = await AsyncClient.create()
        bm = BinanceSocketManager(client)
        try:
            async with bm.aggtrade_socket(symbol.upper()) as stream:
                logging.info(f"[Binance] Connected {symbol.upper()}")
                while True:
                    msg = await stream.recv()
                    price = float(msg.get("p", 0))
                    if callback:
                        asyncio.create_task(_safe_callback(callback, price, "BINANCE"))
        except Exception:
            logging.exception("[Binance] ws error")
            await asyncio.sleep(backoff)
        finally:
            await client.close_connection()

async def okx_ws_ticker(symbol="ETH-USDT-SWAP", callback=None, backoff=5):
    import websockets, time
    OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    while True:
        try:
            async with websockets.connect(OKX_WS_URL) as ws:
                await ws.send(json.dumps({
                    "op": "subscribe",
                    "args": [{"channel": "tickers", "instType": "SWAP", "instId": symbol}]
                }))
                logging.info(f"[OKX] Connected {symbol}")
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("op") == "ping":
                        await ws.send(json.dumps({"op": "pong"}))
                        continue
                    if "data" not in data:
                        continue
                    try:
                        price = float(data["data"][0]["last"])
                        if callback:
                            asyncio.create_task(_safe_callback(callback, price, "OKX"))
                    except (KeyError, IndexError, ValueError) as e:
                        logging.warning(f"[OKX] Invalid ticker data: {data}")
                        continue
        except Exception:
            logging.exception("[OKX] ws error")
            await asyncio.sleep(backoff)

async def run_ws_main(ws_callback):
    await asyncio.gather(
        binance_ws_price(callback=ws_callback),
        okx_ws_ticker(callback=ws_callback),
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    def demo_cb(price, src): print(f"DEMO: {src}: {price}")
    asyncio.run(run_ws_main(demo_cb))
