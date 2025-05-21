import pandas as pd
import pandas_ta as ta
import numpy as np
from collections import deque

# Helper function remains the same or can be integrated if preferred
def ma_function(source, length: int, ma_type: str = "EMA"):
    if isinstance(source, pd.Series): source_pd = source
    elif hasattr(source, 'to_series'): source_pd = source.to_series()
    else: source_pd = pd.Series(source)
    if len(source_pd) < length: return np.full(len(source), np.nan)
    try:
        if ma_type == "SMA": result = ta.sma(source_pd, length=length)
        elif ma_type == "EMA": result = ta.ema(source_pd, length=length)
        elif ma_type == "RMA": result = ta.rma(source_pd, length=length)
        elif ma_type == "WMA": result = ta.wma(source_pd, length=length)
        else: result = ta.ema(source_pd, length=length) # Default to EMA
        # Ensure the result aligns with the input index if lengths differ
        if len(result) != len(source):
             result = result.reindex(source_pd.index)
        return result.values
    except Exception as e:
        print(f"Error in ma_function: {e}")
        return np.full(len(source), np.nan)

class LiveRsiEmaStrategy:
    # --- Parameter Definition for GUI ---
    _params_def = {
        'rsi_length':      ('RSI 長度', int, 14, None),
        'ema_length':      ('EMA 長度', int, 200, None),
        'rsi_long_entry':  ('RSI 多單進場', float, 20.0, None),
        'rsi_long_exit':   ('RSI 多單出場', float, 50.0, None),
        'rsi_short_entry': ('RSI 空單進場', float, 80.0, None),
        'rsi_short_exit':  ('RSI 空單出場', float, 50.0, None),
    }
    """
    RSI + EMA strategy adapted for live trading data streams.
    Calculates indicators incrementally.
    """
    def __init__(self, rsi_length=14, ema_length=200, rsi_long_entry=20.0,
                 rsi_long_exit=50.0, rsi_short_entry=80.0, rsi_short_exit=50.0):
        """
        Initializes the live strategy parameters and internal state.

        Args:
            rsi_length (int): Lookback period for RSI.
            ema_length (int): Lookback period for EMA.
            rsi_long_entry (float): RSI threshold to enter long.
            rsi_long_exit (float): RSI threshold to exit long.
            rsi_short_entry (float): RSI threshold to enter short.
            rsi_short_exit (float): RSI threshold to exit short.
        """
        self.rsi_length = rsi_length
        self.ema_length = ema_length
        self.rsi_long_entry = rsi_long_entry
        self.rsi_long_exit = rsi_long_exit
        self.rsi_short_entry = rsi_short_entry
        self.rsi_short_exit = rsi_short_exit

        # Internal state for incremental calculation
        # We need enough data points to calculate the longest indicator + a buffer
        self.buffer_size = max(self.rsi_length, self.ema_length) + 50 # Keep a buffer
        self.close_prices = deque(maxlen=self.buffer_size)
        self.timestamps = deque(maxlen=self.buffer_size) # Keep track of time if needed

        self.current_rsi = np.nan
        self.current_ema = np.nan
        self.last_signal = 0 # 0: Hold, 1: Buy, -1: Sell

        print(f"LiveRsiEmaStrategy initialized with RSI({self.rsi_length}), EMA({self.ema_length})")

    def update(self, price: float, timestamp=None):
        """
        Updates the strategy with a new price point and recalculates indicators.

        Args:
            price (float): The latest closing price.
            timestamp: Optional timestamp for the price.

        Returns:
            int: Signal (1 for Buy, -1 for Sell, 0 for Hold).
        """
        self.close_prices.append(price)
        if timestamp:
            self.timestamps.append(timestamp)

        # Check if we have enough data to calculate indicators
        required_data_points = max(self.rsi_length, self.ema_length)
        if len(self.close_prices) < required_data_points:
            # print(f"Need {required_data_points} data points, have {len(self.close_prices)}. Waiting...")
            return 0 # Not enough data yet

        # Convert deque to Pandas Series for pandas_ta
        # Using a copy to avoid modifying the deque structure if Series operations do that
        close_series = pd.Series(list(self.close_prices), name='Close')

        # Calculate indicators using the latest data window
        try:
            # RSI
            rsi_values = ta.rsi(close_series, length=self.rsi_length)
            if rsi_values is not None and not rsi_values.empty:
                self.current_rsi = rsi_values.iloc[-1]
            else:
                self.current_rsi = np.nan

            # EMA (using helper function for consistency and error handling)
            ema_values = ma_function(close_series, self.ema_length, "EMA")
            if ema_values is not None and len(ema_values) > 0:
                 # ma_function returns numpy array, get the last value
                 self.current_ema = ema_values[-1]
            else:
                 self.current_ema = np.nan

        except Exception as e:
            print(f"Error calculating indicators: {e}")
            self.current_rsi = np.nan
            self.current_ema = np.nan
            return 0 # Cannot generate signal if indicators fail

        # Check for NaN indicators
        if pd.isna(self.current_rsi) or pd.isna(self.current_ema):
            # print(f"Indicators contain NaN (RSI: {self.current_rsi}, EMA: {self.current_ema}). Holding.")
            return 0

        # --- Generate Signal based on the latest values ---
        signal = 0 # Default to Hold
        current_close = price # Use the latest price passed to update

        long_entry_condition = self.current_rsi < self.rsi_long_entry and current_close > self.current_ema
        long_exit_condition = self.current_rsi > self.rsi_long_exit
        short_entry_condition = self.current_rsi > self.rsi_short_entry and current_close < self.current_ema
        short_exit_condition = self.current_rsi < self.rsi_short_exit

        # Determine signal based on current state (self.last_signal) and conditions
        # This logic assumes we want to generate a signal *once* when conditions are met,
        # and potentially hold until an exit condition is met.
        # More complex state management (e.g., tracking active position) should happen in LiveTrader.

        if self.last_signal <= 0: # If not currently long or holding
            if long_entry_condition:
                signal = 1 # Buy signal
        elif self.last_signal == 1: # If currently long
            if long_exit_condition:
                signal = -1 # Sell signal (to close long)

        if self.last_signal >= 0: # If not currently short or holding
            if short_entry_condition:
                signal = -1 # Sell signal (to enter short)
        elif self.last_signal == -1: # If currently short
            if short_exit_condition:
                signal = 1 # Buy signal (to close short)


        # --- Debug Print (Optional) ---
        # print(f"Timestamp: {timestamp}, Price: {price:.2f}, RSI: {self.current_rsi:.2f}, EMA: {self.current_ema:.2f}, Signal: {signal}")

        self.last_signal = signal # Update last signal state
        return signal

    def generate_signal(self, price: float, timestamp=None):
         """Alias for update method for consistency if needed."""
         return self.update(price, timestamp)

# Example usage (for testing the class directly)
if __name__ == '__main__':
    strategy = LiveRsiEmaStrategy(rsi_length=5, ema_length=10) # Use smaller lengths for faster testing

    # Simulate some price updates
    prices = [100, 101, 102, 101, 103, 105, 104, 106, 108, 110, 109, 107, 105, 103, 100, 98, 99, 101, 104]
    print("Simulating price updates:")
    for i, p in enumerate(prices):
        sig = strategy.update(p, timestamp=f"T{i}")
        print(f"Time T{i}: Price={p:.2f}, RSI={strategy.current_rsi:.2f}, EMA={strategy.current_ema:.2f}, Signal={sig}")
        if i < strategy.buffer_size -1 : # Show buffer filling
             print(f"  Buffer size: {len(strategy.close_prices)}/{strategy.buffer_size}")
