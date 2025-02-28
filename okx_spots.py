import asyncio
import websockets
import json
import threading
from time import sleep

class OKXSpotWebSocket:
    def __init__(self):
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
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
                    # Subscribe to the ticker for BTC-USDT
                    subscribe_message = {
                        "op": "subscribe",
                        "args": [
                            {
                                "channel": "tickers",
                                "instType": "SPOT",
                                "instId": "BTC-USDT"
                            }
                        ]
                    }
                    await ws.send(json.dumps(subscribe_message))
                    print("OKX WebSocket connected")
                    
                    while True:
                        message = await ws.recv()
                        await self.handle_message(json.loads(message))

            except Exception as e:
                print(f"Error connecting to OKX WebSocket: {e}")
                await asyncio.sleep(5)

    async def handle_message(self, message):
        try:
            # Check if the message contains data
            if 'data' in message and isinstance(message['data'], list) and len(message['data']) > 0:
                ticker_data = message['data'][0]
                if self.data is None:
                    self.data = {}

                # Extract relevant data
                self.data.update({
                    "symbol": "BTC-USDT",
                    "mark_price": float(ticker_data.get('last', 0)),  # Last price
                    "bid_price": float(ticker_data.get('bidPx', 0)),  # Best bid price
                    "ask_price": float(ticker_data.get('askPx', 0)),  # Best ask price
                    "volume_24h": float(ticker_data.get('vol24h', 0))  # 24h volume
                })
                # print("OKX data updated:", self.data)

        except Exception as e:
            print(f"Error handling OKX message: {e}")

    def get_data(self):
        return self.data
