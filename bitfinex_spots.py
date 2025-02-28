import websocket
import json
import threading
from time import sleep

class BitfinexSpotWebSocket:
    def __init__(self):
        self.ws_url = 'wss://api-pub.bitfinex.com/ws/2'
        self.data = None
        self.connect()

    def on_open(self):
        # Subscribe to the ticker for BTC/USD
        subscribe_message = {
            "event": "subscribe",
            "channel": "ticker",
            "symbol": "tBTCUSD"
        }
        self.ws.send(json.dumps(subscribe_message))
        print("Subscribed to Bitfinex BTC/USD ticker")

    def on_message(self, message):
        message = json.loads(message)
        if isinstance(message, list) and len(message) > 1:
            # The first element is the channel ID, the second is the data
            channel_id = message[0]
            data = message[1]
            if isinstance(data, list) and len(data) >= 8:
                # Extracting relevant data
                self.data = {
                    "symbol": "BTC/USD",
                    "bid_price": float(data[0]),    # Best bid
                    "ask_price": float(data[2]),    # Best ask
                    "mark_price": float(data[6]),   # Last price
                    "volume_24h": float(data[7])    # 24h volume
                }
                print("Bitfinex data updated:", self.data)

    def on_error(self, error):
        print(f"Error: {error}")

    def on_close(self):
        print("WebSocket closed")

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=lambda ws: self.on_open(),
            on_message=lambda ws, msg: self.on_message(msg),
            on_error=lambda ws, err: self.on_error(err),
            on_close=lambda ws: self.on_close()
        )
        # Run the WebSocket in a separate thread
        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()

    def get_data(self):
        return self.data
