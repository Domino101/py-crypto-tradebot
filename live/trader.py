import time
import threading
import os
from datetime import datetime
from typing import Type
from alpaca.trading.enums import OrderSide, TimeInForce, PositionSide
from alpaca.data.live.crypto import CryptoDataStream
from alpaca.data.live.stock import StockDataStream
import queue # Import queue for type hinting
from dotenv import load_dotenv # Import dotenv for example usage
import pandas as pd
import math # For trailing stop calculations
import ast # For safely evaluating string representations of lists/dicts if needed
import inspect # Needed for adapting backtest strategy
import traceback # For printing tracebacks

from data.alpaca import AlpacaData, connection_pool
# Import strategies (adjust as needed)
from strategies.live_rsi_ema import LiveRsiEmaStrategy
# Import the base class to check instance type if needed later
from backtesting import Strategy as BacktestStrategyBase

class LiveTrader:
    """
    Manages the live trading process for a selected strategy using Alpaca.
    """
    def __init__(self, strategy_class: Type, symbol: str, interval: str, trade_quantity: float, paper_trading: bool = True, slippage_tolerance: float = 0.001, strategy_params: dict = None, gui_queue: queue.Queue = None):
        """
        Initializes the LiveTrader.

        Args:
            strategy_class: The class of the trading strategy to use.
            symbol (str): The symbol to trade (e.g., 'AAPL', 'BTC/USD').
            interval (str): The time interval for the strategy (e.g., '1h', '15m').
            trade_quantity (float): The quantity to trade per signal.
            paper_trading (bool): Whether to use Alpaca's paper trading environment.
            slippage_tolerance (float): Maximum acceptable slippage (currently informational).
            strategy_params (dict): Dictionary of parameters for the strategy constructor.
            gui_queue (queue.Queue): Queue to send status updates back to the GUI.
        """
        # 從策略類獲取參數定義並合併參數
        self.params_definition = getattr(strategy_class, '_params_def', {})
        default_params = {k: v[2] for k, v in self.params_definition.items() if len(v) > 2}
        self.strategy_params = {**default_params, **(strategy_params or {})}
        self.strategy_class = strategy_class
        self.symbol = symbol
        self.interval = interval # Store interval
        self.trade_quantity = trade_quantity
        self.slippage_tolerance = slippage_tolerance # TODO: Implement slippage check logic
        self.is_crypto = '/' in symbol # Basic check for crypto symbol format
        self.gui_queue = gui_queue # Store the GUI queue

        print(f"Initializing LiveTrader for {self.symbol} on {self.interval} interval...")
        self.alpaca = AlpacaData(paper_trading=paper_trading)
        self.strategy = None # Will be instantiated in _init_strategy
        self.stream = None # WebSocket stream
        self.running = False
        self.data_thread = None # Thread for WebSocket data
        self.status_thread = None # Thread for status updates
        self.last_order_time = None # To prevent rapid consecutive orders
        self.current_position_side = None # None, 'long', 'short' - Track position state fetched from API
        self.strategy_type = None # 'live' or 'backtest'
        self.active_trailing_stops = {} # Stores state for active trailing stops {symbol: state_dict}

        # Check connection and initialize strategy
        try:
            account_info = self.alpaca.get_account_info() # Now returns Account object or raises ConnectionError
            print(f"Alpaca connection successful. Account ID: {account_info.account_number}, Status: {account_info.status}, Paper: {paper_trading}")
            # Initialize strategy only after successful connection
            self._init_strategy()
            if not self.strategy:
                 # _init_strategy should handle its own errors, but double-check
                 raise RuntimeError("Strategy initialization failed after successful Alpaca connection.")
        except ConnectionError as ce:
            # Catch the specific error from get_account_info
            print(f"Error connecting to Alpaca: {ce}")
            # No need to raise again, as the trader instance won't be fully functional.
            # Optionally, send a message to GUI if available
            if self.gui_queue:
                try: self.gui_queue.put(("messagebox", ("error", "Alpaca 連接失敗", f"無法連接到 Alpaca API: {ce}")))
                except: pass
            # Stop further initialization by raising a more specific error or returning
            raise RuntimeError("LiveTrader initialization failed due to Alpaca connection error.") from ce
        except Exception as e:
            # Catch other potential errors during init (like strategy init issues)
            print(f"Unexpected error during LiveTrader initialization: {e}")
            traceback.print_exc()
            if self.gui_queue:
                 try: self.gui_queue.put(("messagebox", ("error", "初始化錯誤", f"LiveTrader 初始化期間發生意外錯誤: {e}")))
                 except: pass
            raise RuntimeError("LiveTrader initialization failed.") from e

        # Initial status update attempt (only if init was successful)
        self._update_gui_status()

    def _init_strategy(self):
        """Initializes the trading strategy instance with parameters."""
        print(f"Initializing strategy: {self.strategy_class.__name__} with params: {self.strategy_params}")
        try:
            # Check if it's a backtesting.py strategy needing adaptation
            is_backtesting_strategy = hasattr(self.strategy_class, 'next') and callable(getattr(self.strategy_class, 'next')) and not hasattr(self.strategy_class, 'update')

            if is_backtesting_strategy:
                 print("Adapting backtest strategy for live trading...")
                 class MockBroker:
                     def __init__(self): self.orders, self.positions = [], {}
                     def submit(self, order): print(f"Mock Broker: Submitting order {order}"); self.orders.append(order)
                 class MockData: # Basic mock data structure
                     def __init__(self): self.Open, self.High, self.Low, self.Close, self.Volume, self.index = [],[],[],[],[],[]
                 
                 self.mock_broker = MockBroker()
                 self.mock_data = MockData() 

                 # Initialize the backtesting strategy with mocks and params
                 sig = inspect.signature(self.strategy_class.__init__)
                 init_kwargs = {}
                 if 'broker' in sig.parameters:
                     init_kwargs['broker'] = self.mock_broker
                 if 'data' in sig.parameters:
                     init_kwargs['data'] = self.mock_data
                 
                 # --- Pass parameters using the 'params' keyword argument ---
                 # backtesting.py Strategy base class expects parameters in a dict via 'params' kwarg
                 # Individual parameters defined in the subclass __init__ are usually set *within* the strategy's init
                 # --- Pass broker, data, and params positionally ---
                 # backtesting.py Strategy base class expects (broker, data, params)
                 print(f"  Passing params positionally to backtest strategy: {self.strategy_params}")
                 # Ensure strategy_params is a dict, even if empty
                 params_to_pass = self.strategy_params if isinstance(self.strategy_params, dict) else {}
                 self.strategy = self.strategy_class(self.mock_broker, self.mock_data, params_to_pass)
                 # --- End positional argument passing ---

                 self.strategy_type = 'backtest'
                 print("Backtest strategy adapted successfully.")
            else:
                 # Assume it's a live-ready strategy (expects params directly)
                 self.strategy = self.strategy_class(**self.strategy_params)
                 self.strategy_type = 'live' 
                 if not (hasattr(self.strategy, 'update') and callable(getattr(self.strategy, 'update'))):
                      raise ValueError("Live strategy must have an 'update' method.")
                 print("Live strategy initialized successfully.")

        except Exception as e:
            print(f"Error initializing strategy: {e}")
            traceback.print_exc() 
            self.strategy = None
            self.strategy_type = None
            self.running = False
            if self.gui_queue:
                 try: self.gui_queue.put(("messagebox", ("error", "策略初始化失敗", f"初始化策略時出錯: {e}")))
                 except: pass 
            return 


    async def _handle_stock_trade(self, trade):
        """Callback for processing incoming stock trade data."""
        if not self.strategy or not self.running: return
        try:
            # --- Update Trailing Stop First ---
            self._update_trailing_stop(self.symbol, trade.price)

            # --- Check Trailing Stop Trigger ---
            if self._check_trailing_stop_trigger(self.symbol, trade.price):
                print(f"Trailing stop triggered for {self.symbol} at price {trade.price}. Closing position.")
                self.alpaca.close_position(self.symbol)
                # Clear trailing stop state after closing
                if self.symbol in self.active_trailing_stops:
                    del self.active_trailing_stops[self.symbol]
                return # Stop further processing for this trade if closed

            # --- Process Strategy Signal ---
            signal = 0
            if self.strategy_type == 'live':
                signal = self.strategy.update(trade.price, trade.timestamp)
            elif self.strategy_type == 'backtest':
                self._update_mock_data(trade)
                # Check for orders placed by strategy.next()
                # This requires accessing the strategy's internal state or broker mock
                # For simplicity, we assume strategy.next() might set a flag or return something
                # Or, more directly, check if the strategy instance has pending orders
                # Let's assume the strategy places orders via self.buy/self.sell which might have custom args
                
                # --- Extract potential order details from backtest strategy ---
                # This part is tricky as backtesting.py doesn't directly expose the last order intent easily.
                # We rely on the custom `_stop_loss_params` passed during self.buy/self.sell in the strategy.
                # We need to check if the mock broker has a new order *and* extract those params.
                
                # A simplified approach: Check if the strategy *would* place an order now.
                # This requires more complex adaptation or modifying the strategy base.
                # For now, let's assume the signal logic is handled within _execute_signal
                # based on the *next* call potentially modifying some state we can check.
                # A better way: Modify the strategy to store its last intended action.
                
                # Let's call next() and then check if an order was intended
                original_order_count = len(self.mock_broker.orders)
                self.strategy.next()
                new_order_count = len(self.mock_broker.orders)

                if new_order_count > original_order_count:
                     last_order_intent = self.mock_broker.orders[-1] # Get the last order placed in the mock
                     # Infer signal based on the mock order (this is an approximation)
                     signal = 1 if last_order_intent.is_buy else -1
                     # Try to get custom params passed to buy/sell
                     stop_loss_params = getattr(last_order_intent, '_stop_loss_params', None)
                     print(f"Backtest strategy generated order intent: Signal={signal}, SL Params={stop_loss_params}")
                     # Pass params for _execute_signal
                     self._execute_signal(signal, stop_loss_params=stop_loss_params)
                     # Note: This might execute multiple times if not handled carefully.
                     # Reset mock orders or add state tracking if needed.
                     # self.mock_broker.orders = [] # Example reset

            else: print("Unknown strategy type.")

            # Execute signal only for live strategies here, backtest handled above
            if self.strategy_type == 'live' and signal != 0:
                 # Live strategies should return signal and potentially SL params
                 stop_loss_params = getattr(self.strategy, 'last_stop_loss_params', None) # Example attribute
                 self._execute_signal(signal, stop_loss_params=stop_loss_params)
        except Exception as e: print(f"Error processing stock trade: {e}"); traceback.print_exc()

    async def _handle_crypto_trade(self, trade):
        """Callback for processing incoming crypto trade data."""
        if not self.strategy or not self.running: return
        try:
            # --- Update Trailing Stop First ---
            self._update_trailing_stop(self.symbol, trade.price)

            # --- Check Trailing Stop Trigger ---
            if self._check_trailing_stop_trigger(self.symbol, trade.price):
                print(f"Trailing stop triggered for {self.symbol} at price {trade.price}. Closing position.")
                self.alpaca.close_position(self.symbol)
                # Clear trailing stop state after closing
                if self.symbol in self.active_trailing_stops:
                    del self.active_trailing_stops[self.symbol]
                return # Stop further processing for this trade if closed

            # --- Process Strategy Signal ---
            signal = 0
            if self.strategy_type == 'live':
                signal = self.strategy.update(trade.price, trade.timestamp)
            elif self.strategy_type == 'backtest':
                self._update_mock_data(trade)
                # Check for orders placed by strategy.next() - similar logic as stock handler
                original_order_count = len(self.mock_broker.orders)
                self.strategy.next()
                new_order_count = len(self.mock_broker.orders)

                if new_order_count > original_order_count:
                     last_order_intent = self.mock_broker.orders[-1]
                     signal = 1 if last_order_intent.is_buy else -1
                     stop_loss_params = getattr(last_order_intent, '_stop_loss_params', None)
                     print(f"Backtest strategy generated order intent: Signal={signal}, SL Params={stop_loss_params}")
                     self._execute_signal(signal, stop_loss_params=stop_loss_params)
                     # Consider resetting mock orders if needed: self.mock_broker.orders = []

            else: print("Unknown strategy type.")

            # Execute signal only for live strategies here
            if self.strategy_type == 'live' and signal != 0:
                 stop_loss_params = getattr(self.strategy, 'last_stop_loss_params', None)
                 self._execute_signal(signal, stop_loss_params=stop_loss_params)
        except Exception as e: print(f"Error processing crypto trade: {e}"); traceback.print_exc()

    def _update_mock_data(self, trade):
         """Updates the mock data object for backtesting strategies."""
         if not hasattr(self, 'mock_data'): return 
         price = trade.price
         size = getattr(trade, 'size', 0) # Use getattr for safety
         timestamp = pd.to_datetime(trade.timestamp)
         self.mock_data.Open.append(price)
         self.mock_data.High.append(price)
         self.mock_data.Low.append(price)
         self.mock_data.Close.append(price)
         self.mock_data.Volume.append(size) 
         self.mock_data.index.append(timestamp)


    def _execute_signal(self, signal, stop_loss_params=None):
        """
        Executes a trade based on the strategy signal, checking current position.
        Handles stop loss parameter setup, especially for trailing stops.
        """
        if signal is None or signal == 0: return
        current_time = datetime.now()
        if self.last_order_time and (current_time - self.last_order_time).total_seconds() < 5: 
             print("Rate limiting order placement.")
             return
        target_side = OrderSide.BUY if signal == 1 else OrderSide.SELL
        print(f"Strategy generated signal: {target_side} for {self.symbol}")
        try:
            existing_pos = None; position_qty = 0.0; current_pos_side_api = None
            try:
                existing_pos = self.alpaca.trading_client.get_open_position(self.symbol)
                current_pos_side_api = existing_pos.side 
                position_qty = abs(float(existing_pos.qty))
                print(f"Current position from API: Side={current_pos_side_api}, Qty={position_qty}")
            except Exception as pos_error: 
                 from alpaca.common.exceptions import APIError
                 if isinstance(pos_error, APIError) and pos_error.status_code == 404:
                     current_pos_side_api = None; position_qty = 0.0
                     print("No existing position found via API.")
                 else:
                     print(f"Warning: Could not get position info via API: {pos_error}"); return 
            self.current_position_side = current_pos_side_api
            order_placed = False; order_details = None
            if target_side == OrderSide.BUY:
                if self.current_position_side == PositionSide.SHORT:
                    print(f"Signal BUY: Closing SHORT ({position_qty}) for {self.symbol}")
                    order_details = self.alpaca.place_market_order(symbol=self.symbol, qty=position_qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
                    order_placed = True
                elif self.current_position_side is None: 
                    print(f"Signal BUY: Entering LONG ({self.trade_quantity}) for {self.symbol}")
                    # --- Check for Trailing Stop Params ---
                    if stop_loss_params and stop_loss_params.get('type') == 'trailing':
                        print(f"  Applying Trailing Stop: {stop_loss_params}")
                        # Don't pass sl/tp to Alpaca, store params instead
                        order_details = self.alpaca.place_market_order(symbol=self.symbol, qty=self.trade_quantity, side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
                        if order_details and order_details.status != 'rejected':
                             self._setup_trailing_stop(self.symbol, OrderSide.BUY, stop_loss_params)
                        order_placed = True
                    else: # Standard order without trailing stop (or params not provided)
                        order_details = self.alpaca.place_market_order(symbol=self.symbol, qty=self.trade_quantity, side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
                        order_placed = True
                else: print("Signal BUY: Already LONG.")
            elif target_side == OrderSide.SELL:
                if self.current_position_side == PositionSide.LONG:
                    print(f"Signal SELL: Closing LONG ({position_qty}) for {self.symbol}")
                    order_details = self.alpaca.place_market_order(symbol=self.symbol, qty=position_qty, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
                    order_placed = True
                    # Clear trailing stop state if closing position
                    if self.symbol in self.active_trailing_stops:
                        del self.active_trailing_stops[self.symbol]
                        print(f"  Cleared trailing stop state for {self.symbol}.")
                elif self.current_position_side is None:
                    print(f"Signal SELL: Entering SHORT ({self.trade_quantity}) for {self.symbol}")
                    # --- Check for Trailing Stop Params ---
                    if stop_loss_params and stop_loss_params.get('type') == 'trailing':
                        print(f"  Applying Trailing Stop: {stop_loss_params}")
                        order_details = self.alpaca.place_market_order(symbol=self.symbol, qty=self.trade_quantity, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
                        if order_details and order_details.status != 'rejected':
                             self._setup_trailing_stop(self.symbol, OrderSide.SELL, stop_loss_params)
                        order_placed = True
                    else: # Standard order
                        order_details = self.alpaca.place_market_order(symbol=self.symbol, qty=self.trade_quantity, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
                        order_placed = True
                else: print("Signal SELL: Already SHORT.")

            # --- Post-Order Placement ---
            if order_placed and order_details:
                 print(f"Order {order_details.id} submitted: {target_side} {order_details.qty} {self.symbol}. Status: {order_details.status}")
                 self.last_order_time = current_time
                 # Update status immediately after order placement attempt
                 self._update_gui_status()
            elif order_placed: print(f"Order placement failed. Details: {order_details}")
        except Exception as e:
            print(f"Error executing trade signal: {e}"); traceback.print_exc()
            # Ensure trailing stop state is cleared if order fails badly
            if order_placed and not order_details and self.symbol in self.active_trailing_stops:
                 print(f"  Clearing potentially orphaned trailing stop state for {self.symbol} due to order error.")
                 del self.active_trailing_stops[self.symbol]


    def _setup_trailing_stop(self, symbol, side, params):
        """Initializes the state for a new trailing stop."""
        if symbol in self.active_trailing_stops:
            print(f"Warning: Trailing stop already active for {symbol}. Overwriting.")

        try:
            # Fetch entry price - crucial for activation %
            # This might need a slight delay or confirmation check
            time.sleep(0.5) # Small delay to allow position to register
            position = self.alpaca.trading_client.get_open_position(symbol)
            entry_price = float(position.avg_entry_price)
            print(f"  Trailing stop setup for {symbol} ({side}): Entry Price={entry_price:.4f}, Params={params}")
        except Exception as e:
            print(f"Error fetching entry price for trailing stop setup: {e}. Cannot activate stop.")
            return # Cannot proceed without entry price

        self.active_trailing_stops[symbol] = {
            'side': side, # OrderSide.BUY (long) or OrderSide.SELL (short)
            'entry_price': entry_price,
            'activation_pct': params.get('activation_pct', 0.01), # Default 1%
            'trail_pct': params.get('trail_pct', 0.015), # Default 1.5%
            'atr_multiplier': params.get('atr_multiplier', 1.5), # Default 1.5
            'current_atr': params.get('current_atr'), # Store ATR at entry if provided
            'is_active': False,
            'highest_price': entry_price if side == OrderSide.BUY else -math.inf, # Track peak for long
            'lowest_price': entry_price if side == OrderSide.SELL else math.inf,   # Track trough for short
            'stop_price': None # Calculated dynamically
        }

    def _update_trailing_stop(self, symbol, current_price):
        """Updates the state of an active trailing stop based on the current price."""
        if symbol not in self.active_trailing_stops:
            return

        state = self.active_trailing_stops[symbol]
        entry_price = state['entry_price']
        side = state['side']

        # 1. Check Activation
        if not state['is_active']:
            if side == OrderSide.BUY and current_price >= entry_price * (1 + state['activation_pct']):
                state['is_active'] = True
                state['highest_price'] = current_price # Start tracking from activation point
                print(f"Trailing stop for {symbol} (LONG) activated at {current_price:.4f}")
            elif side == OrderSide.SELL and current_price <= entry_price * (1 - state['activation_pct']):
                state['is_active'] = True
                state['lowest_price'] = current_price # Start tracking from activation point
                print(f"Trailing stop for {symbol} (SHORT) activated at {current_price:.4f}")

        # 2. Update High/Low and Calculate Stop Price if Active
        if state['is_active']:
            trail_pct = state['trail_pct']
            # Optional: Adjust trail_pct based on ATR if needed
            # atr = state['current_atr'] # Or fetch latest ATR
            # if atr and state['atr_multiplier']:
            #     dynamic_trail_amount = atr * state['atr_multiplier']
            #     # Convert amount to percentage or use directly if risk engine supports it
            #     # trail_pct = dynamic_trail_amount / current_price # Example adjustment

            if side == OrderSide.BUY:
                state['highest_price'] = max(state['highest_price'], current_price)
                state['stop_price'] = state['highest_price'] * (1 - trail_pct)
            elif side == OrderSide.SELL:
                state['lowest_price'] = min(state['lowest_price'], current_price)
                state['stop_price'] = state['lowest_price'] * (1 + trail_pct)
            # print(f"  TS Update {symbol}: High/Low={state.get('highest_price', state.get('lowest_price')):.4f}, Stop={state['stop_price']:.4f}") # Debug

    def _check_trailing_stop_trigger(self, symbol, current_price):
        """Checks if the current price triggers the calculated trailing stop."""
        if symbol not in self.active_trailing_stops:
            return False

        state = self.active_trailing_stops[symbol]

        if not state['is_active'] or state['stop_price'] is None:
            return False # Not active or stop price not calculated yet

        if state['side'] == OrderSide.BUY and current_price <= state['stop_price']:
            print(f"TRIGGER: Trailing Stop (LONG) for {symbol}. Price {current_price:.4f} <= Stop {state['stop_price']:.4f}")
            return True
        elif state['side'] == OrderSide.SELL and current_price >= state['stop_price']:
            print(f"TRIGGER: Trailing Stop (SHORT) for {symbol}. Price {current_price:.4f} >= Stop {state['stop_price']:.4f}")
            return True

        return False


    def _update_gui_status(self):
        """Fetches current account status and sends it to the GUI queue."""
        if not self.gui_queue: return 
        status_data = {'balance': '錯誤', 'positions': '錯誤', 'orders': '錯誤'}
        try:
            account_info = self.alpaca.get_account_info()
            equity = float(account_info.equity) 
            cash = float(account_info.cash)
            status_data['balance'] = f"權益 ${equity:,.2f} (現金 ${cash:,.2f})"
            positions = self.alpaca.trading_client.get_all_positions()
            if positions:
                pos_strings = [f"{pos.symbol}: {float(pos.qty):.4f} {pos.side.value.upper()} @ {float(pos.avg_entry_price):.2f} (市值 ${float(pos.market_value):,.2f}, P/L ${float(pos.unrealized_pl):,.2f})" for pos in positions]
                status_data['positions'] = "\n".join(pos_strings) if pos_strings else "無"
            else: status_data['positions'] = "無"
            orders = self.alpaca.trading_client.get_orders()
            if orders:
                order_strings = []
                for order in orders:
                    limit_price = f"@ {float(order.limit_price):.2f}" if order.limit_price else ""
                    stop_price = f"Stop @ {float(order.stop_price):.2f}" if order.stop_price else ""
                    price_info = f"{limit_price}{stop_price}".strip()
                    order_strings.append(f"{order.symbol}: {order.side.value.upper()} {float(order.qty):.4f} {order.order_type.value} {price_info} ({order.status.value})")
                status_data['orders'] = "\n".join(order_strings) if order_strings else "無"
            else: status_data['orders'] = "無"
        except Exception as e: print(f"Error fetching live status: {e}"); traceback.print_exc()
        try: self.gui_queue.put_nowait(("update_live_status", status_data))
        except queue.Full: print("Warning: GUI queue is full. Skipping status update.")
        except Exception as q_err: print(f"Error putting status update into GUI queue: {q_err}")

    def _status_update_loop(self):
        """Periodically calls the status update function."""
        print("Status update loop started.")
        time.sleep(2) 
        while self.running:
            try: self._update_gui_status()
            except Exception as e: print(f"Error in status update loop: {e}") 
            interval = 5 
            for _ in range(interval):
                 if not self.running: break
                 time.sleep(1)
        print("Status update loop stopped.")

    def _run_data_loop(self):
        """The main loop that connects to the WebSocket and processes data."""
        self._init_strategy()
        if not self.strategy:
            print("Strategy initialization failed. Exiting data loop.")
            self.running = False 
            if self.gui_queue:
                 try: self.gui_queue.put(("status", "策略初始化失敗"))
                 except: pass
            return
        print("Starting WebSocket connection...")
        try:
            api_key = os.getenv('ALPACA_API_KEY')
            secret_key = os.getenv('ALPACA_SECRET_KEY')
            if not api_key or not secret_key: raise ValueError("API keys not found in environment for WebSocket.")

            # --- Use standard Alpaca data stream URL ---
            # The base WebSocket URL for data is generally the same for paper/live.
            base_ws_url = "wss://stream.data.alpaca.markets"
            print(f"Using base WebSocket URL: {base_ws_url}")
            # --- End URL definition ---

            if self.is_crypto:
                 # Crypto uses /v1beta3/crypto/us endpoint
                 ws_endpoint = f"{base_ws_url}/v1beta3/crypto/us"
                 print(f"Connecting to Crypto WebSocket: {ws_endpoint}")
                 # Pass the full endpoint URL to url_override
                 # Set raw_data=False (or remove) to get parsed objects instead of dicts
                 self.stream = CryptoDataStream(api_key, secret_key, url_override=ws_endpoint, raw_data=False)
                 self.stream.subscribe_trades(self._handle_crypto_trade, self.symbol)
            else:
                 # Stocks use /v2/[feed] endpoint (e.g., /v2/iex or /v2/sip)
                 feed = 'iex' # Default to IEX for broader compatibility (or 'sip' for paid data)
                 ws_endpoint = f"{base_ws_url}/v2/{feed}"
                 print(f"Connecting to Stock WebSocket ({feed}): {ws_endpoint}")
                 # StockDataStream likely uses url_override, similar to CryptoDataStream
                 # Set raw_data=False (or remove) to get parsed objects instead of dicts
                 self.stream = StockDataStream(api_key, secret_key, url_override=ws_endpoint, feed=feed, raw_data=False)
                 self.stream.subscribe_trades(self._handle_stock_trade, self.symbol)

            print(f"Subscribed to trades for {self.symbol}. Running stream...")
            self.stream.run()
        except Exception as e:
            print(f"WebSocket error or connection issue: {e}")
            traceback.print_exc()
        finally:
            print("WebSocket connection closed or failed.")
            self.running = False
            # Ensure GUI controls are re-enabled if the loop exits unexpectedly
            if self.gui_queue:
                 try: self.gui_queue.put(("live_trade_stopped", None))
                 except: pass

    def start(self):
        """Starts the trading loop in a separate thread."""
        if self.running: print("Trader is already running."); return
        print("Starting LiveTrader...")
        self.running = True
        self.data_thread = threading.Thread(target=self._run_data_loop, daemon=True)
        self.data_thread.start()
        print("LiveTrader data thread started.")
        self.status_thread = threading.Thread(target=self._status_update_loop, daemon=True)
        self.status_thread.start()
        print("LiveTrader status thread started.")

    def stop(self):
        """Stops the trading loop and WebSocket connection."""
        if not self.running: print("Trader is not running."); return
        print("Stopping LiveTrader...")
        self.running = False 
        if self.stream:
            try:
                print("Requesting WebSocket stream stop...")
                self.stream.stop_ws()
                print("WebSocket stream stop requested.")
                # 確保完全關閉並釋放連線
                if self.stream:
                    connection_pool.release_connection(self.stream)
                    self.stream = None
            except Exception as e:
                print(f"Error stopping WebSocket stream: {e}")
                traceback.print_exc()
        # Clear trailing stop states on stop
        self.active_trailing_stops = {}
        print("Cleared all active trailing stop states.")
        if self.data_thread and self.data_thread.is_alive():
            print("Waiting for data thread to join...")
            self.data_thread.join(timeout=10)
            if self.data_thread.is_alive(): print("Warning: Data thread did not stop gracefully.")
            else: print("Data thread joined successfully.")
        self.data_thread = None; self.status_thread = None; self.stream = None 
        print("LiveTrader stopped.")

# Example Usage (for testing purposes, normally called from main.py or GUI)
if __name__ == '__main__':
    load_dotenv() 
    TEST_SYMBOL = "BTC/USD"; TEST_INTERVAL = '1m'; TRADE_QTY = 0.001; PAPER_MODE = True 
    STRATEGY_PARAMS = {'rsi_length': 14, 'ema_length': 50, 'rsi_long_entry': 30.0, 'rsi_long_exit': 60.0, 'rsi_short_entry': 70.0, 'rsi_short_exit': 40.0}
    trader = None
    try:
        print("--- Starting LiveTrader Example ---")
        trader = LiveTrader(
            strategy_class=LiveRsiEmaStrategy, strategy_params=STRATEGY_PARAMS, 
            symbol=TEST_SYMBOL, interval=TEST_INTERVAL, trade_quantity=TRADE_QTY, 
            paper_trading=PAPER_MODE, gui_queue=None 
        )
        trader.start()
        start_time = time.time()
        while trader.running and (time.time() - start_time) < 60: time.sleep(1)
        print("\n--- Example run duration elapsed ---")
    except KeyboardInterrupt: print("\n--- Manual stop requested ---")
    except Exception as e: print(f"\n--- Error during example: {e} ---"); traceback.print_exc() 
    finally:
        if trader: print("--- Stopping trader ---"); trader.stop()
        print("--- LiveTrader Example Finished ---")
