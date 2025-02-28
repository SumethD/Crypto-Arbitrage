from pybit.unified_trading import WebSocket
import time

class BybitSpotWebSocket:
    def __init__(self):
        self.ws = None
        self.data = {}  # Shared dictionary for storing our desired fields
        self.connect()

    def connect(self):
        try:
            # Connect using V5 WebSocket for spot
            self.ws = WebSocket(
                testnet=False,
                channel_type="spot",
                ping_interval=20,
                ping_timeout=10
            )

            # Subscribe to the ticker stream for BTCUSDT
            self.ws.ticker_stream(
                symbol="BTCUSDT",
                callback=self.handle_ticker_data
            )
            # Subscribe to the orderbook stream for BTCUSDT
            self.ws.orderbook_stream(
                symbol="BTCUSDT",
                depth=50,  # Depth of 50 levels; adjust if needed
                callback=self.handle_orderbook_data
            )
            print("Bybit WebSocket connected")
        except Exception as e:
            print(f"Error connecting to Bybit WebSocket: {e}")
            time.sleep(5)
            self.connect()

    def handle_ticker_data(self, message):
        try:
            if "data" in message and isinstance(message["data"], dict):
                data = message["data"]
                # Update the shared data with ticker values:
                # mark_price from lastPrice and 24hr volume
                self.data.update({
                    "symbol": "BTCUSDT",
                    "mark_price": float(data.get("lastPrice", 0)),
                    "volume_24h": float(data.get("volume24h", 0))
                })
                # print("Bybit ticker updated:", self.data)
        except Exception as e:
            print(f"Error handling ticker: {e}")
            print("Message causing error:", message)

    def handle_orderbook_data(self, message):
        try:
            if "data" in message and isinstance(message["data"], dict):
                data = message["data"]
                # Check if bid and ask arrays exist and are non-empty
                if "b" in data and data["b"] and "a" in data and data["a"]:
                    best_bid = float(data["b"][0][0])
                    best_ask = float(data["a"][0][0])
                    self.data.update({
                        "bid_price": best_bid,
                        "ask_price": best_ask
                    })
                    # print("Bybit orderbook updated:", self.data)
                else:
                    print("Bid/ask data not available")
        except Exception as e:
            print(f"Error handling orderbook: {e}")
            print("Message causing error:", message)

    def get_data(self):
        return self.data
