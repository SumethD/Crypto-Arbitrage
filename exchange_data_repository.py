import threading
import time
from datetime import datetime
from collections import defaultdict

class ExchangeDataRepository:
    """
    Central repository for storing and accessing real-time market data from multiple exchanges.
    Thread-safe implementation that can be updated by multiple WebSocket connections
    and accessed by the UI thread.
    """
    def __init__(self):
        # Use RLock for thread safety (allows recursive locking by the same thread)
        self._data_lock = threading.RLock()
        
        # Main data structure: {symbol: {exchange: ticker_data}}
        # ticker_data is a dict with keys: mark_price, bid_price, ask_price, volume_24h
        self._ticker_data = defaultdict(dict)
        
        # Track when each exchange's data was last updated
        self._last_update = defaultdict(dict)  # {symbol: {exchange: timestamp}}
        
        # List of callback functions to notify when data is updated
        self._update_callbacks = []
    
    def update_ticker(self, symbol, exchange, ticker_data):
        """
        Updates ticker data for a specific symbol and exchange.
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTC/USDT")
            exchange (str): Exchange name (e.g., "BYBIT-spot")
            ticker_data (dict): Ticker data with keys like mark_price, bid_price, etc.
        """
        # Standardize the symbol format
        std_symbol = self._standardize_symbol(symbol)
        
        with self._data_lock:
            # Store previous data for change detection
            prev_data = self._ticker_data[std_symbol].get(exchange)
            
            # Update data with standardized symbol
            ticker_data['symbol'] = std_symbol
            self._ticker_data[std_symbol][exchange] = ticker_data
            self._last_update[std_symbol][exchange] = datetime.now().timestamp()
            
            # Notify callbacks if price changed
            if prev_data is None or prev_data.get('mark_price') != ticker_data.get('mark_price'):
                for callback in self._update_callbacks:
                    callback(std_symbol, exchange, ticker_data)
    
    def get_ticker(self, symbol, exchange=None):
        """
        Gets the latest ticker data for a symbol from a specific exchange or all exchanges.
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTC/USDT")
            exchange (str, optional): Exchange name. If None, returns data from all exchanges.
            
        Returns:
            dict or None: Ticker data for the specified symbol and exchange
        """
        std_symbol = self._standardize_symbol(symbol)
        
        with self._data_lock:
            if std_symbol not in self._ticker_data:
                return None
                
            if exchange:
                return self._ticker_data[std_symbol].get(exchange)
            else:
                return self._ticker_data[std_symbol].copy()
    
    def get_all_tickers(self):
        """
        Gets all ticker data for all symbols and exchanges.
        
        Returns:
            dict: All ticker data
        """
        with self._data_lock:
            return {symbol: data.copy() for symbol, data in self._ticker_data.items()}
    
    def register_update_callback(self, callback):
        """
        Registers a callback to be notified when ticker data is updated.
        
        Args:
            callback (function): Function to call with updated data
                                 Signature: callback(symbol, exchange, ticker_data)
        """
        self._update_callbacks.append(callback)
    
    def get_arbitrage_opportunities(self, symbol, min_profit_percent=0.5):
        """
        Analyzes current prices across exchanges to find arbitrage opportunities.
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTC/USDT")
            min_profit_percent (float): Minimum profit percentage to consider
            
        Returns:
            list: List of arbitrage opportunities sorted by profit percentage
        """
        opportunities = []
        std_symbol = self._standardize_symbol(symbol)
        
        with self._data_lock:
            if std_symbol not in self._ticker_data:
                return []
                
            exchanges = self._ticker_data[std_symbol]
            
            # Check for stale data (older than 30 seconds)
            current_time = datetime.now().timestamp()
            active_exchanges = {
                ex: data for ex, data in exchanges.items() 
                if current_time - self._last_update[std_symbol].get(ex, 0) < 30
            }
            
            # Debug print to see what data is being used for arbitrage
            print(f"Arbitrage calculation for {std_symbol} using data: {active_exchanges}")
            
            # Find arbitrage opportunities
            exchange_list = list(active_exchanges.keys())
            for i in range(len(exchange_list)):
                buy_exchange = exchange_list[i]
                buy_price = active_exchanges[buy_exchange].get('ask_price')
                
                if buy_price is None or buy_price == 0:
                    continue
                    
                for j in range(len(exchange_list)):
                    if i == j:
                        continue
                        
                    sell_exchange = exchange_list[j]
                    sell_price = active_exchanges[sell_exchange].get('bid_price')
                    
                    if sell_price is None or sell_price == 0:
                        continue
                    
                    # Calculate profit percentage
                    profit_percent = (sell_price - buy_price) / buy_price * 100
                    
                    if profit_percent >= min_profit_percent:
                        opportunities.append({
                            'symbol': std_symbol,
                            'buy_exchange': buy_exchange,
                            'buy_price': buy_price,
                            'sell_exchange': sell_exchange,
                            'sell_price': sell_price,
                            'profit_percent': profit_percent
                        })
            
            # Sort by profit percentage (highest first)
            opportunities.sort(key=lambda x: x['profit_percent'], reverse=True)
            
        return opportunities
    
    def _standardize_symbol(self, symbol):
        """
        Standardizes symbol format across exchanges.
        
        Args:
            symbol (str): The symbol to standardize
            
        Returns:
            str: Standardized symbol
        """
        if symbol is None:
            return "BTC/USDT"  # Default symbol
            
        # Convert to uppercase
        symbol = str(symbol).upper()
        
        # Handle different separators
        if '/' in symbol:
            return symbol  # Already in BTC/USDT format
        elif '-' in symbol:
            base, quote = symbol.split('-')
            return f"{base}/{quote}"
        elif symbol == "BTCUSDT":
            return "BTC/USDT"
        elif symbol == "BTCUSD":
            return "BTC/USD"
        elif "BTC" in symbol and ("USDT" in symbol or "USD" in symbol):
            # Try to extract BTC and USDT/USD from any format
            if "USDT" in symbol:
                return "BTC/USDT"
            else:
                return "BTC/USD"
        
        # If we can't standardize, return as is
        return symbol


def update_repository_from_websocket(repo, exchange_ws, exchange_name):
    """
    Updates the repository with data from a WebSocket connection.
    """
    print(f"Starting update thread for {exchange_name}")
    connection_attempts = 0
    
    # Default symbols for each exchange
    default_symbols = {
        "BYBIT-spot": "BTC/USDT",
        "KRAKEN-spot": "BTC/USD",
        "HUOBI-spot": "BTC/USDT",
        "OKX-spot": "BTC/USDT",
        "BITFINEX-spot": "BTC/USD"
    }
    
    while True:
        try:
            data = exchange_ws.get_data()
            
            # Special handling for Kraken
            if exchange_name == "KRAKEN-spot":
                # Debug what we're getting from Kraken
                print(f"Kraken data received in update thread: {data}")
                
                # If we have no data yet, create a placeholder
                if data is None:
                    data = {
                        "symbol": "BTC/USD",
                        "mark_price": None,
                        "bid_price": None,
                        "ask_price": None,
                        "volume_24h": None
                    }
                
                # Ensure symbol is set
                if "symbol" not in data or not data["symbol"]:
                    data["symbol"] = "BTC/USD"
                
                # Ensure all values are numeric and non-zero
                for key in ["mark_price", "bid_price", "ask_price", "volume_24h"]:
                    try:
                        if key in data and data[key] is not None:
                            data[key] = float(data[key])
                            # If value is zero, try to get it from another field
                            if data[key] == 0 and key == "mark_price" and "last" in data:
                                data[key] = float(data["last"])
                    except (ValueError, TypeError):
                        data[key] = None
            
            if data:
                # Add symbol if missing for any exchange
                if "symbol" not in data or not data["symbol"]:
                    data["symbol"] = default_symbols.get(exchange_name, "BTC/USDT")
                
                symbol = data.get("symbol")
                
                # Ensure all required fields exist (with None if missing)
                required_fields = ["mark_price", "bid_price", "ask_price", "volume_24h"]
                for field in required_fields:
                    if field not in data:
                        data[field] = None
                
                # Skip update if all price fields are zero or None
                if all(data.get(field) in [0, None] for field in ["mark_price", "bid_price", "ask_price"]):
                    print(f"Skipping update for {exchange_name} - all prices are zero or None")
                    time.sleep(0.5)
                    continue
                
                # Update repository
                repo.update_ticker(symbol, exchange_name, data)
                
                # Print update occasionally
                if connection_attempts % 20 == 0:
                    print(f"Updated {exchange_name} data: {data}")
            else:
                # Only log occasionally
                if connection_attempts % 50 == 0:
                    print(f"Waiting for data from {exchange_name}...")
            
            connection_attempts += 1
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error updating repository from {exchange_name}: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
