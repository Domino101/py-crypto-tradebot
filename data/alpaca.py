import threading
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.live.crypto import CryptoDataStream
from alpaca.data.live.stock import StockDataStream
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest, OrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderType
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
import pandas as pd
import os

# WebSocket 連接池管理
class AlpacaConnectionPool:
    def __init__(self, max_connections=3):
        self.max_connections = max_connections
        self.active_connections = []
        self.lock = threading.Lock()

    def get_connection(self, is_crypto=False):
        with self.lock:
            # 尋找可用連接或創建新連接
            for conn in self.active_connections:
                if not conn['in_use'] and conn['is_crypto'] == is_crypto:
                    conn['in_use'] = True
                    return conn['stream']
            
            if len(self.active_connections) < self.max_connections:
                api_key = os.getenv('ALPACA_API_KEY')
                secret_key = os.getenv('ALPACA_SECRET_KEY')
                base_ws_url = "wss://stream.data.alpaca.markets"
                
                if is_crypto:
                    ws_endpoint = f"{base_ws_url}/v1beta3/crypto/us"
                    stream = CryptoDataStream(api_key, secret_key, url_override=ws_endpoint, raw_data=False)
                else:
                    ws_endpoint = f"{base_ws_url}/v2/iex"
                    stream = StockDataStream(api_key, secret_key, url_override=ws_endpoint, feed='iex', raw_data=False)
                
                new_conn = {'stream': stream, 'in_use': True, 'is_crypto': is_crypto}
                self.active_connections.append(new_conn)
                return stream
            
            raise ConnectionError("Maximum connections reached")

    def release_connection(self, stream):
        with self.lock:
            # 複製當前連線列表避免迭代時修改
            current_connections = list(self.active_connections)
            
            for conn in current_connections:
                # 強制關閉WebSocket連接
                try:
                    if conn['stream']._ws and not conn['stream']._ws.closed:
                        conn['stream']._ws.close()
                        print(f"Closed {conn['stream'].__class__.__name__} connection")
                except Exception as e:
                    print(f"Error closing connection: {str(e)}")
                
                # 移除匹配的連線或已關閉的連線
                if conn['stream'] == stream or (conn['stream']._ws and conn['stream']._ws.closed):
                    try:
                        self.active_connections.remove(conn)
                        print(f"Removed {conn['stream'].__class__.__name__} connection")
                    except ValueError:
                        pass  # 避免重複移除
            
            # 記錄最終連線狀態
            print("\nFinal connection pool status:")
            self._log_connections()

# 全局連接池實例
connection_pool = AlpacaConnectionPool(max_connections=3)

# TODO: Consider splitting data fetching and trading into separate classes or modules
class AlpacaData:
    def __init__(self, paper_trading: bool = True):
        """
        Initializes clients for Alpaca data and trading.

        Args:
            paper_trading (bool): If True, connects to the paper trading environment.
                                  Defaults to True.
        """
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')

        if not api_key or not secret_key:
            raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in environment variables.")

        # Use StockHistoricalDataClient for stocks, CryptoHistoricalDataClient for crypto
        # For simplicity here, we might need logic to switch based on symbol type later
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.crypto_data_client = CryptoHistoricalDataClient(api_key, secret_key)

        # Trading client handles both stocks and crypto
        self.trading_client = TradingClient(api_key, secret_key, paper=paper_trading)

    def get_historical_stock_data(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
            limit: int = 500,
            adjustment: str = 'raw' # or 'split', 'dividend', 'all'
        ) -> pd.DataFrame:
        """
        Get historical stock bars data from Alpaca.

        Parameters:
            symbol (str): Stock symbol e.g. AAPL.
            timeframe (TimeFrame): TimeFrame enum e.g. TimeFrame.Hour
            start (datetime): Start datetime
            end (datetime): End datetime
            limit (int): Max number of data points.
            adjustment (str): Price adjustment type.

        Returns:
            pd.DataFrame: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
        """
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit,
                adjustment=adjustment
            )

            bars = self.data_client.get_stock_bars(request_params)
            # Ensure correct columns and index for consistency
            if symbol in bars.df.index.get_level_values(0):
                 df = bars.df.loc[symbol]
            else:
                 df = bars.df # Handle single symbol case if structure differs
            df = df.reset_index()
            # Rename columns if necessary (Alpaca v2 might have slightly different names)
            df.rename(columns={'timestamp': 'timestamp', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'}, inplace=True)
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp']) # Ensure datetime objects
            df.set_index('timestamp', inplace=True)
            return df

        except Exception as e:
            print(f"Error fetching Alpaca stock data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def get_historical_crypto_data(
        self,
        symbol: str, # e.g., BTC/USD
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Get historical crypto bars data from Alpaca.

        Parameters:
            symbol (str): Crypto symbol pair e.g. BTC/USD.
            timeframe (TimeFrame): TimeFrame enum e.g. TimeFrame.Hour.
            start (datetime): Start datetime.
            end (datetime): End datetime.
            limit (int): Max number of data points.

        Returns:
            pd.DataFrame: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
        """
        try:
            request_params = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit
            )

            bars = self.crypto_data_client.get_crypto_bars(request_params)
            # Ensure correct columns and index for consistency
            if symbol in bars.df.index.get_level_values(0):
                 df = bars.df.loc[symbol]
            else:
                 df = bars.df # Handle single symbol case if structure differs
            df = df.reset_index()
            # Rename columns if necessary
            df.rename(columns={'timestamp': 'timestamp', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'}, inplace=True)
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp']) # Ensure datetime objects
            df.set_index('timestamp', inplace=True)
            return df

        except Exception as e:
            print(f"Error fetching Alpaca crypto data for {symbol}: {str(e)}")
            return pd.DataFrame()

    # --- Trading Methods ---

    def place_market_order(self, symbol: str, qty: float, side: OrderSide, time_in_force: TimeInForce = TimeInForce.GTC) -> dict:
        """
        Places a market order.

        Args:
            symbol (str): Symbol to trade (e.g., 'AAPL', 'BTC/USD').
            qty (float): Number of shares or quantity of crypto.
            side (OrderSide): OrderSide.BUY or OrderSide.SELL.
            time_in_force (TimeInForce): Time in force (default GTC).

        Returns:
            dict: Order object from Alpaca API.
        """
        try:
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=time_in_force
            )
            market_order = self.trading_client.submit_order(order_data=market_order_data)
            print(f"Market order placed for {qty} {symbol} {side}: {market_order.id}")
            return market_order.dict() # Return dict representation
        except Exception as e:
            print(f"Error placing market order for {symbol}: {str(e)}")
            return {'error': str(e)}

    def place_limit_order(self, symbol: str, qty: float, side: OrderSide, limit_price: float, time_in_force: TimeInForce = TimeInForce.GTC) -> dict:
        """
        Places a limit order.

        Args:
            symbol (str): Symbol to trade.
            qty (float): Number of shares or quantity of crypto.
            side (OrderSide): OrderSide.BUY or OrderSide.SELL.
            limit_price (float): The limit price for the order.
            time_in_force (TimeInForce): Time in force (default GTC).

        Returns:
            dict: Order object from Alpaca API.
        """
        try:
            limit_order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                limit_price=limit_price,
                time_in_force=time_in_force
            )
            limit_order = self.trading_client.submit_order(order_data=limit_order_data)
            print(f"Limit order placed for {qty} {symbol} {side} @ {limit_price}: {limit_order.id}")
            return limit_order.dict()
        except Exception as e:
            print(f"Error placing limit order for {symbol}: {str(e)}")
            return {'error': str(e)}

    def place_bracket_order(self, symbol: str, qty: float, side: OrderSide, limit_price: float, take_profit_price: float, stop_loss_price: float, time_in_force: TimeInForce = TimeInForce.GTC) -> dict:
        """
        Places a bracket order (limit order with take profit and stop loss).

        Args:
            symbol (str): Symbol to trade.
            qty (float): Number of shares or quantity of crypto.
            side (OrderSide): OrderSide.BUY or OrderSide.SELL.
            limit_price (float): The entry limit price for the order.
            take_profit_price (float): The take profit price.
            stop_loss_price (float): The stop loss price.
            time_in_force (TimeInForce): Time in force (default GTC).

        Returns:
            dict: Order object from Alpaca API.
        """
        try:
            bracket_order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                limit_price=limit_price,
                time_in_force=time_in_force,
                order_class=OrderClass.BRACKET,
                take_profit=TakeProfitRequest(limit_price=take_profit_price),
                stop_loss=StopLossRequest(stop_price=stop_loss_price) # Can also use limit_price for stop limit
            )
            bracket_order = self.trading_client.submit_order(order_data=bracket_order_data)
            print(f"Bracket order placed for {qty} {symbol} {side} @ {limit_price} (TP: {take_profit_price}, SL: {stop_loss_price}): {bracket_order.id}")
            return bracket_order.dict()
        except Exception as e:
            print(f"Error placing bracket order for {symbol}: {str(e)}")
            return {'error': str(e)}

    def get_open_orders(self) -> list:
        """Gets a list of all open orders."""
        try:
            orders = self.trading_client.get_orders()
            return [order.dict() for order in orders if order.status == 'open' or order.status == 'new' or order.status == 'partially_filled'] # Adjust statuses as needed
        except Exception as e:
            print(f"Error fetching open orders: {str(e)}")
            return []

    def get_positions(self) -> list:
        """Gets a list of all current positions."""
        try:
            positions = self.trading_client.get_all_positions()
            return [pos.dict() for pos in positions]
        except Exception as e:
            print(f"Error fetching positions: {str(e)}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancels an open order by its ID.

        Args:
            order_id (str): The ID of the order to cancel.

        Returns:
            bool: True if cancellation was successful (or order already closed), False otherwise.
        """
        try:
            # Check if order exists and is open first (optional but good practice)
            # order = self.trading_client.get_order_by_id(order_id)
            # if order.status not in ['new', 'partially_filled', 'held', 'accepted', 'pending_new', 'calculated']:
            #     print(f"Order {order_id} is not open, cannot cancel.")
            #     return True # Consider it successful if already closed

            self.trading_client.cancel_order_by_id(order_id)
            print(f"Cancel request sent for order {order_id}")
            return True
        except Exception as e:
            # Handle cases where order might not exist or is already filled/cancelled
            if "order not found" in str(e) or "order is not cancelable" in str(e):
                 print(f"Order {order_id} could not be cancelled (may already be filled/cancelled): {str(e)}")
                 return True # Treat as success if it's already done
            print(f"Error cancelling order {order_id}: {str(e)}")
            return False

    def cancel_all_orders(self) -> bool:
        """Cancels all open orders."""
        try:
            self.trading_client.cancel_orders()
            print("Cancel all open orders request sent.")
            return True
        except Exception as e:
            print(f"Error cancelling all orders: {str(e)}")
            return False

    def get_account_info(self): # Removed incorrect type hint -> dict
        """
        Gets account information.

        Returns:
            alpaca.trading.models.Account: The account object on success.

        Raises:
            Exception: If there is an error fetching account info from Alpaca.
        """
        try:
            account = self.trading_client.get_account()
            return account # Return the actual Account object
        except Exception as e:
            print(f"Error fetching account info: {str(e)}")
            # Re-raise the exception to be handled by the caller
            raise ConnectionError(f"Failed to fetch account info from Alpaca: {e}") from e
