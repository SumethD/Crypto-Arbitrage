import tkinter as tk
from time import sleep
import threading
import logging
from kraken_spots import KrakenSpotWebSocket
from bybit_spots import BybitSpotWebSocket
from bitfinex_spots import BitfinexSpotWebSocket
from okx_spots import OKXSpotWebSocket
from huobi_spots import HuobiSpotWebSocket
from exchange_data_repository import ExchangeDataRepository, update_repository_from_websocket

# Constants
COLUMNS = ['Symbol', 'Exchange', 'Mark Price', 'Volume 24h', 'Bid Price', 'Ask Price']

class CryptoSpreadsheet(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.entries = {}
        self.original_colors = {}
        self.symbol_exchange_row_mapping = {}  # Maps "symbol:exchange" to row
        self.free_rows = []
        self.current_row = 1
        self.highlight_colors = {
            'increase': '#c8e6c9',  # Light green
            'decrease': '#ffcdd2',  # Light red
            'neutral': '#ffffff'    # White
        }

        # Style configuration
        self.header_style = {
            'font': ('Arial', 10, 'bold'),
            'bg': '#2c3e50',
            'fg': 'white',
            'width': 20,
            'readonlybackground': '#2c3e50'
        }
        
        self.cell_style = {
            'font': ('Arial', 10),
            'bg': '#ffffff',
            'fg': '#2c3e50',
            'width': 20,
            'readonlybackground': '#ffffff'
        }

        # Create scrollable frame
        self.canvas = tk.Canvas(self, bg='#ffffff')
        self.frame = tk.Frame(self.canvas, bg='#ffffff')
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hsb = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        # Pack scrollbars and canvas
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.create_headers()

    def onFrameConfigure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_headers(self):
        for col, header in enumerate(COLUMNS):
            entry = tk.Entry(self.frame, **self.header_style)
            entry.grid(row=0, column=col, padx=1, pady=1, sticky='nsew')
            entry.insert(0, header)
            entry.config(state='readonly')
            self.entries[(0, col)] = entry
            self.original_colors[(0, col)] = self.header_style['bg']

    def add_row(self):
        row = self.current_row
        for col in range(len(COLUMNS)):
            entry = tk.Entry(self.frame, **self.cell_style)
            entry.grid(row=row, column=col, padx=1, pady=1, sticky='nsew')
            entry.config(state='readonly')  # Make cell read-only
            self.entries[(row, col)] = entry
            self.original_colors[(row, col)] = self.cell_style['bg']
        self.free_rows.append(row)
        self.current_row += 1
        return row

    def get_row(self, symbol, exchange):
        """
        Gets or creates a row for a specific symbol and exchange.
        Each exchange gets its own row, even for the same symbol.
        
        Args:
            symbol (str): The trading pair symbol
            exchange (str): The exchange name
            
        Returns:
            int: The row number
        """
        key = f"{symbol}:{exchange}"
        if key not in self.symbol_exchange_row_mapping:
            if self.free_rows:
                row = self.free_rows.pop(0)
            else:
                row = self.add_row()
            self.symbol_exchange_row_mapping[key] = row
            # Set symbol and exchange
            self.update_cell(row, 0, symbol)
            self.update_cell(row, 1, exchange)
        return self.symbol_exchange_row_mapping[key]

    def _compare_numeric_values(self, current_value, new_value):
        try:
            current_num = float(current_value.replace('$', '').replace(' BTC', ''))
            new_num = float(str(new_value).replace('$', '').replace(' BTC', ''))
            
            if current_num == 0:
                return 'neutral'
            return 'increase' if new_num > current_num else 'decrease' if new_num < current_num else 'neutral'
        except (ValueError, AttributeError):
            return 'neutral'

    def _get_highlight_type(self, col, current_value, new_value):
        if col in [2, 3, 4, 5]:  # Mark Price, Volume, Bid, Ask columns
            return self._compare_numeric_values(current_value, new_value)
        return 'neutral'

    def update_cell(self, row, col, value, highlight=True):
        entry = self.entries.get((row, col))
        if entry:
            current_value = entry.get()
            if str(current_value) != str(value):
                highlight_type = self._get_highlight_type(col, current_value, value)
                
                entry.config(state='normal')
                entry.delete(0, tk.END)
                entry.insert(0, value)
                entry.config(state='readonly')
                
                if highlight:
                    self.highlight_cell(row, col, highlight_type)

    def highlight_cell(self, row, col, highlight_type):
        entry = self.entries.get((row, col))
        if entry:
            original_color = self.original_colors[(row, col)]
            highlight_color = self.highlight_colors[highlight_type]
            entry.config(state='normal', readonlybackground=highlight_color)
            entry.config(state='readonly')
            self.after(500, lambda: self.reset_cell_color(entry, original_color))

    def reset_cell_color(self, entry, original_color):
        entry.config(state='normal', readonlybackground=original_color)
        entry.config(state='readonly')

    def update_from_repository(self, symbol, exchange, data):
        """
        Updates the UI with data from the repository.
        This is called by the repository when new data is available.
        
        Args:
            symbol (str): Trading pair symbol
            exchange (str): Exchange name
            data (dict): Ticker data
        """
        try:
            # Get or create a row for this symbol and exchange
            row = self.get_row(symbol, exchange)
            
            # Format values with fallbacks for missing data
            mark_price = data.get('mark_price')
            mark_price_str = f"${mark_price}" if mark_price is not None else "N/A"
            
            volume = data.get('volume_24h')
            volume_str = f"{volume} BTC" if volume is not None else "N/A"
            
            bid_price = data.get('bid_price')
            bid_price_str = f"${bid_price}" if bid_price is not None else "N/A"
            
            ask_price = data.get('ask_price')
            ask_price_str = f"${ask_price}" if ask_price is not None else "N/A"
            
            # Update cells with formatted values
            self.update_cell(row, 2, mark_price_str)
            self.update_cell(row, 3, volume_str)
            self.update_cell(row, 4, bid_price_str)
            self.update_cell(row, 5, ask_price_str)
            
            print(f"Updated UI for {symbol} on {exchange} with {data}")
        except Exception as e:
            print(f"Error updating UI from repository for {symbol} on {exchange}: {e}")
            import traceback
            traceback.print_exc()


# Create a class for displaying arbitrage opportunities
class ArbitrageFrame(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        
        # Create title label
        self.title_label = tk.Label(
            self,
            text="Arbitrage Opportunities",
            font=('Arial', 12, 'bold'),
            bg='#ffffff',
            fg='#2c3e50',
            pady=5
        )
        self.title_label.pack(fill='x')
        
        # Create text area for displaying opportunities
        self.text_area = tk.Text(
            self,
            font=('Arial', 10),
            bg='#ffffff',
            fg='#2c3e50',
            height=20,
            width=50
        )
        self.text_area.pack(fill='both', expand=True)
        
        # Add scrollbar
        self.scrollbar = tk.Scrollbar(self.text_area)
        self.scrollbar.pack(side='right', fill='y')
        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.text_area.yview)
    
    def update_opportunities(self, opportunities):
        """
        Updates the display with new arbitrage opportunities.
        
        Args:
            opportunities (list): List of arbitrage opportunities
        """
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        
        if not opportunities:
            self.text_area.insert(tk.END, "No arbitrage opportunities found.\n")
        else:
            self.text_area.insert(tk.END, f"Found {len(opportunities)} opportunities:\n\n")
            
            for i, opp in enumerate(opportunities):
                self.text_area.insert(tk.END, f"Opportunity {i+1}:\n")
                self.text_area.insert(tk.END, f"  Symbol: {opp['symbol']}\n")
                self.text_area.insert(tk.END, f"  Buy on: {opp['buy_exchange']} at ${opp['buy_price']:.2f}\n")
                self.text_area.insert(tk.END, f"  Sell on: {opp['sell_exchange']} at ${opp['sell_price']:.2f}\n")
                self.text_area.insert(tk.END, f"  Profit: {opp['profit_percent']:.2f}%\n\n")
        
        self.text_area.config(state='disabled')


def run_with_repository(spreadsheet, arbitrage_frame=None):
    """
    Runs the application with the central data repository.
    
    Args:
        spreadsheet (CryptoSpreadsheet): The spreadsheet UI component
        arbitrage_frame (ArbitrageFrame, optional): Frame for displaying arbitrage opportunities
    """
    # Create the central data repository
    repo = ExchangeDataRepository()
    
    # Register UI update callback
    repo.register_update_callback(spreadsheet.update_from_repository)
    print("Registered UI update callback")
    
    # Register arbitrage callback if arbitrage frame is provided
    if arbitrage_frame:
        def check_for_arbitrage():
            while True:
                try:
                    # Check for arbitrage opportunities
                    symbols = ["BTC/USDT", "BTC/USD"]
                    for symbol in symbols:
                        opportunities = repo.get_arbitrage_opportunities(symbol, min_profit_percent=0.2)
                        if opportunities:
                            # Update the arbitrage frame in the main thread
                            arbitrage_frame.after(0, lambda opps=opportunities: arbitrage_frame.update_opportunities(opps))
                    sleep(5)  # Check every 5 seconds
                except Exception as e:
                    print(f"Error checking for arbitrage: {e}")
                    sleep(5)
        
        # Start arbitrage checking thread
        arbitrage_thread = threading.Thread(target=check_for_arbitrage)
        arbitrage_thread.daemon = True
        arbitrage_thread.start()
    
    try:
        print("Initializing exchange WebSockets...")
        # Create WebSocket instances with better error handling
        exchanges = []
        
        try:
            bybit_ws = BybitSpotWebSocket()
            exchanges.append((bybit_ws, "BYBIT-spot"))
            print("Successfully initialized Bybit WebSocket")
        except Exception as e:
            print(f"Error initializing Bybit WebSocket: {e}")
        
        try:
            kraken_ws = KrakenSpotWebSocket()
            exchanges.append((kraken_ws, "KRAKEN-spot"))
            print("Successfully initialized Kraken WebSocket")
        except Exception as e:
            print(f"Error initializing Kraken WebSocket: {e}")
        
        try:
            huobi_ws = HuobiSpotWebSocket()
            exchanges.append((huobi_ws, "HUOBI-spot"))
            print("Successfully initialized Huobi WebSocket")
        except Exception as e:
            print(f"Error initializing Huobi WebSocket: {e}")
        
        try:
            okx_ws = OKXSpotWebSocket()
            exchanges.append((okx_ws, "OKX-spot"))
            print("Successfully initialized OKX WebSocket")
        except Exception as e:
            print(f"Error initializing OKX WebSocket: {e}")
        
        try:
            bitfinex_ws = BitfinexSpotWebSocket()
            exchanges.append((bitfinex_ws, "BITFINEX-spot"))
            print("Successfully initialized Bitfinex WebSocket")
        except Exception as e:
            print(f"Error initializing Bitfinex WebSocket: {e}")
        
        # Start threads to update the repository from each WebSocket
        threads = []
        for ws, name in exchanges:
            thread = threading.Thread(
                target=update_repository_from_websocket,
                args=(repo, ws, name)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            print(f"Started update thread for {name}")
        
        # Manually create initial rows for all exchanges to ensure they appear in UI
        for exchange_name in ["BYBIT-spot", "KRAKEN-spot", "HUOBI-spot", "OKX-spot", "BITFINEX-spot"]:
            for symbol in ["BTC/USDT", "BTC/USD"]:
                try:
                    # This ensures a row is created for each exchange, even before data arrives
                    row = spreadsheet.get_row(symbol, exchange_name)
                    print(f"Created initial row for {symbol} on {exchange_name}: row {row}")
                except Exception as e:
                    print(f"Error creating row for {symbol} on {exchange_name}: {e}")
        
    except Exception as e:
        print(f"Error setting up WebSockets: {e}")


def main():
    root = tk.Tk()
    root.title("Crypto Exchange Data")
    root.geometry("1200x600")

    # Configure root window
    root.configure(bg='#ffffff')
    
    # Add title label
    title_label = tk.Label(
        root,
        text="Cryptocurrency Market Data",
        font=('Arial', 16, 'bold'),
        bg='#ffffff',
        fg='#2c3e50',
        pady=10
    )
    title_label.pack()
    
    # Create main frame to hold spreadsheet and arbitrage panel
    main_frame = tk.Frame(root, bg='#ffffff')
    main_frame.pack(fill='both', expand=True, padx=10, pady=5)
    
    # Left frame for spreadsheet
    left_frame = tk.Frame(main_frame, bg='#ffffff')
    left_frame.pack(side='left', fill='both', expand=True)
    
    # Create spreadsheet in left frame
    spreadsheet = CryptoSpreadsheet(left_frame)
    spreadsheet.pack(fill='both', expand=True)
    
    # Right frame for arbitrage opportunities
    right_frame = tk.Frame(main_frame, bg='#ffffff', width=400)
    right_frame.pack(side='right', fill='y', padx=10)
    right_frame.pack_propagate(False)  # Prevent frame from shrinking
    
    # Create arbitrage display
    arbitrage_frame = ArbitrageFrame(right_frame)
    arbitrage_frame.pack(fill='both', expand=True)

    # Start with repository
    ws_thread = threading.Thread(
        target=run_with_repository, 
        args=(spreadsheet, arbitrage_frame)
    )
    ws_thread.daemon = True
    ws_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()
