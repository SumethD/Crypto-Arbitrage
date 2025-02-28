import websockets
import json
import asyncio
import threading
import time

class KrakenSpotWebSocket:
    def __init__(self):
        self.ws_url = "wss://ws.kraken.com/v2"  # Updated to v2 endpoint
        self.data = None
        self.loop = None
        self.start_ws_thread()

    async def connect(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Subscribe message for BTC/USD ticker
                    subscribe_message = {
                        "method": "subscribe",
                        "params": {
                            "channel": "ticker",
                            "symbol": ["BTC/USD"]
                        }
                    }
                    await ws.send(json.dumps(subscribe_message))
                    print("Kraken WebSocket connected")
                    
                    while True:
                        message = await ws.recv()
                        await self.handle_message(json.loads(message))

            except Exception as e:
                print(f"Error connecting to Kraken WebSocket: {e}")
                await asyncio.sleep(5)

    async def handle_message(self, message):
        try:
            # Debug the raw message
            print(f"Kraken raw message: {message}")
            
            if isinstance(message, dict) and 'data' in message:
                data = message['data'][0]  # First element contains ticker data
                
                # Create a new data dictionary with proper values
                self.data = {
                    "symbol": "BTC/USD",
                    "bid_price": float(data.get('bid', 0)),
                    "ask_price": float(data.get('ask', 0)),
                    "mark_price": float(data.get('last', 0)),
                    "volume_24h": float(data.get('volume', 0))
                }
                
                # Ensure we have non-zero values
                if self.data["mark_price"] == 0 and data.get('last'):
                    self.data["mark_price"] = float(data.get('last'))
                
                # Debug the processed data
                print(f"Kraken processed data: {self.data}")

        except Exception as e:
            print(f"Error handling Kraken message: {e}")
            import traceback
            traceback.print_exc()

    def start_ws_thread(self):
        def run_async_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.connect())

        thread = threading.Thread(target=run_async_loop)
        thread.daemon = True
        thread.start()

    def get_data(self):
        # Add a debug print to see what data is being returned
        print(f"Kraken get_data returning: {self.data}")
        return self.data
