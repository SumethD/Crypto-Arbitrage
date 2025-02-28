import asyncio
import websockets
import json
import gzip
import threading
from time import sleep

class HuobiSpotWebSocket:
    def __init__(self):
        self.ws_url = "wss://api.huobi.pro/ws"
        self.data = None
        self.loop = None
        self.start_ws_thread()

    def start_ws_thread(self):
        def run_async_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.connect())

        thread = threading.Thread(target=run_async_loop)
        thread.daemon = True
        thread.start()

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Subscribe to BTC/USDT ticker
                    subscribe_message = {
                        "sub": "market.btcusdt.ticker",
                        "id": "id1"
                    }
                    await ws.send(json.dumps(subscribe_message))

                    while True:
                        try:
                            message = await ws.recv()
                            
                            # Handle binary (gzipped) messages
                            if isinstance(message, bytes):
                                try:
                                    message = gzip.decompress(message).decode('utf-8')
                                except Exception as e:
                                    print(f"Error decompressing message: {e}")
                                    continue

                            # Parse JSON
                            try:
                                data = json.loads(message)
                            except json.JSONDecodeError:
                                continue

                            # Handle ping/pong
                            if "ping" in data:
                                pong_msg = {"pong": data["ping"]}
                                await ws.send(json.dumps(pong_msg))
                                continue

                            # Handle ticker data
                            if "tick" in data:
                                tick = data["tick"]
                                self.data = {
                                    "symbol": "BTCUSDT",
                                    "mark_price": float(tick.get("close", 0)),
                                    "bid_price": float(tick.get("bid", 0)),
                                    "ask_price": float(tick.get("ask", 0)),
                                    "volume_24h": float(tick.get("amount", 0))
                                }

                        except Exception as e:
                            print(f"Error processing message: {e}")
                            continue

            except Exception as e:
                print(f"WebSocket connection error: {e}")
                await asyncio.sleep(5)
                continue

    def get_data(self):
        """Returns the latest ticker data"""
        return self.data
