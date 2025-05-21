# strategies/vegas_double_tunnel.py
import pandas as pd
import pandas_ta as ta
from backtesting import Strategy
import numpy as np
import traceback

# Helper function (copied from existing strategies for consistency)
def ma_function(source, length: int, ma_type: str = "EMA"):
    """Calculates Moving Average based on type."""
    if isinstance(source, pd.Series): source_pd = source
    elif hasattr(source, 'to_series'): source_pd = source.to_series()
    else: source_pd = pd.Series(source)

    if len(source_pd.dropna()) < length:
        # print(f"Warning: Not enough data ({len(source_pd.dropna())}) for MA({ma_type}, {length}). Returning NaNs.")
        return np.full(len(source), np.nan)
    try:
        if ma_type == "SMA": result = ta.sma(source_pd, length=length)
        elif ma_type == "EMA": result = ta.ema(source_pd, length=length)
        elif ma_type == "RMA": result = ta.rma(source_pd, length=length)
        elif ma_type == "WMA": result = ta.wma(source_pd, length=length)
        else:
            # print(f"Warning: Unknown MA type '{ma_type}'. Defaulting to EMA.")
            result = ta.ema(source_pd, length=length) # Default to EMA

        # Ensure the result has the same index as the input source
        if result is None: # Handle cases where ta might return None
             return np.full(len(source), np.nan)

        # Reindex might be needed if pandas_ta drops initial NaNs differently
        if len(result) < len(source_pd):
             result = result.reindex(source_pd.index) # Align index, fills missing with NaN
        elif len(result) > len(source_pd):
             result = result.iloc[-len(source_pd):] # Trim if result is longer

        return result.values # Return as numpy array matching backtesting.py expectations
    except Exception as e:
        print(f"Error in ma_function({ma_type}, {length}): {e}")
        traceback.print_exc()
        return np.full(len(source), np.nan)

class VegasDoubleTunnelStrategy(Strategy):
    """
    Vegas Double Tunnel Strategy Implementation.
    Based on crossovers of MA tunnels and a filter MA.
    Includes dynamic SL/TP based on percentage.
    """
    # --- Parameter Definition for GUI ---
    _params_def = {
        # Moving Averages
        'ma1_period': ('MA1 週期', int, 144, (10, 300)),
        'ma1_type':   ('MA1 類型', str, 'EMA', ['SMA', 'EMA', 'WMA', 'RMA']),
        'ma3_period': ('MA3 週期', int, 576, (200, 1000)),
        'ma3_type':   ('MA3 類型', str, 'EMA', ['SMA', 'EMA', 'WMA', 'RMA']),
        'ma5_period': ('MA5 週期 (過濾)', int, 14, (5, 50)),
        'ma5_type':   ('MA5 類型 (過濾)', str, 'EMA', ['SMA', 'EMA', 'WMA', 'RMA']),
        # Optional MAs (can be added if needed for plotting or logic later)
        # 'ma2_period': ('MA2 週期', int, 169, (10, 300)),
        # 'ma2_type':   ('MA2 類型', str, 'EMA', ['SMA', 'EMA', 'WMA', 'RMA']),
        # 'ma4_period': ('MA4 週期', int, 676, (200, 1000)),
        # 'ma4_type':   ('MA4 類型', str, 'EMA', ['SMA', 'EMA', 'WMA', 'RMA']),

        # Order Management
        'stoploss_long_pct':  ('停損 多單 (%)', float, 1.0, (0.1, 10.0)),
        'stoploss_short_pct': ('停損 空單 (%)', float, 1.0, (0.1, 10.0)),
        'takeProfit_long_pct':('停利 多單 (%)', float, 1.0, (0.1, 20.0)),
        'takeProfit_short_pct':('停利 空單 (%)', float, 1.0, (0.1, 20.0)),
        'size_frac':          ('投入淨值比例', float, 0.1, (0.01, 0.95)),

        # Trading Controls
        'direction':    ('交易方向', str, 'Both', ["Long Only", "Short Only", "Both"]),
        'trading_days': ('交易日', str, '24/7', ["24/7", "Weekdays Only"]),
    }

    # --- Class Variables for Parameters (defaults matching _params_def) ---
    # These need to be defined for the backtesting framework to recognize them at runtime,
    # even though _params_def handles GUI/optimization aspects.
    ma1_period = 144
    ma1_type = 'EMA'
    ma3_period = 576
    ma3_type = 'EMA'
    ma5_period = 14
    ma5_type = 'EMA'
    stoploss_long_pct = 1.0
    stoploss_short_pct = 1.0
    takeProfit_long_pct = 1.0 # Default value
    takeProfit_short_pct = 1.0 # Default value
    size_frac = 0.1
    direction = "Both"
    trading_days = "24/7"

    # --- Internal Variables ---
    # These will be initialized by backtesting.py based on _params_def
    ma1 = None
    ma2 = None
    ma3 = None
    ma4 = None
    ma5 = None
    filter_ma = None # EMA(close, 144) used in conditions

    def init(self):
        """Initialize strategy and calculate indicators."""
        print("--- Strategy Init Start (VegasDoubleTunnelStrategy) ---")
        try:
            # --- Create Pandas Series from data ---
            # Ensure index is datetime
            if not isinstance(self.data.index, pd.DatetimeIndex):
                 try:
                     self.data.index = pd.to_datetime(self.data.index)
                     print("  Converted index to DatetimeIndex.")
                 except Exception as e:
                     raise ValueError(f"Failed to convert data index to DatetimeIndex: {e}")

            close_series = pd.Series(self.data.Close, index=self.data.index, name='Close')
            print(f"  Data length: {len(close_series)}")
            if len(close_series) == 0: raise ValueError("Close price data is empty.")

            # --- Calculate Moving Averages ---
            print(f"  Calculating MAs: MA1({self.ma1_type},{self.ma1_period}), MA3({self.ma3_type},{self.ma3_period}), MA5({self.ma5_type},{self.ma5_period})")
            self.ma1 = self.I(ma_function, close_series, self.ma1_period, self.ma1_type, name="MA1")
            self.ma3 = self.I(ma_function, close_series, self.ma3_period, self.ma3_type, name="MA3")
            self.ma5 = self.I(ma_function, close_series, self.ma5_period, self.ma5_type, name="MA5")

            # Calculate the filter MAs used in conditions
            # Pine: MA5 > ta.ema(close, 144) and MA5 < ta.ema(close, 144)
            filter_ma_period = 144 # Hardcoded as per Pine script logic
            print(f"  Calculating Filter MA: EMA({filter_ma_period})")
            self.filter_ma = self.I(ma_function, close_series, filter_ma_period, "EMA", name=f"EMA{filter_ma_period}")

            # Calculate other MAs for potential plotting/future use (optional)
            # self.ma2 = self.I(ma_function, close_series, self.ma2_period, self.ma2_type, name="MA2")
            # self.ma4 = self.I(ma_function, close_series, self.ma4_period, self.ma4_type, name="MA4")

            print(f"  MA1 last: {self.ma1[-1]:.4f}" if len(self.ma1)>0 and not np.isnan(self.ma1[-1]) else "MA1 N/A")
            print(f"  MA3 last: {self.ma3[-1]:.4f}" if len(self.ma3)>0 and not np.isnan(self.ma3[-1]) else "MA3 N/A")
            print(f"  MA5 last: {self.ma5[-1]:.4f}" if len(self.ma5)>0 and not np.isnan(self.ma5[-1]) else "MA5 N/A")
            print(f"  Filter MA last: {self.filter_ma[-1]:.4f}" if len(self.filter_ma)>0 and not np.isnan(self.filter_ma[-1]) else "Filter MA N/A")

        except ValueError as ve:
             print(f"FATAL ERROR checking data: {ve}")
             traceback.print_exc()
             raise RuntimeError(f"Initialization failed due to data issues: {ve}")
        except Exception as e:
             print(f"FATAL ERROR during indicator initialization: {e}")
             traceback.print_exc()
             raise RuntimeError(f"Initialization failed: {e}")
        print("--- Strategy Init End ---")


    def next(self):
        """Define logic for the next bar."""
        # --- Data/Indicator Availability Check ---
        # Ensure we have enough data points and calculated indicator values
        # Need current values for MA1, MA3, MA5, FilterMA, and Close price
        # Also need previous values for crossover checks
        required_len = max(self.ma1_period, self.ma3_period, self.ma5_period, 144) + 2 # Need at least 2 points for crossover
        if len(self.data.Close) < required_len:
            return # Not enough data yet

        # Get current and previous values
        try:
            current_price = self.data.Close[-1]
            ma1_now = self.ma1[-1]
            ma1_prev = self.ma1[-2]
            ma3_now = self.ma3[-1]
            ma3_prev = self.ma3[-2]
            ma5_now = self.ma5[-1]
            filter_ma_now = self.filter_ma[-1]

            # Check for NaN values in critical indicators for the current step
            if np.isnan(current_price) or np.isnan(ma1_now) or np.isnan(ma1_prev) or \
               np.isnan(ma3_now) or np.isnan(ma3_prev) or np.isnan(ma5_now) or np.isnan(filter_ma_now):
                # print(f"Warning: NaN detected in critical indicators at index {len(self.data.Close)-1}. Skipping.")
                return

        except IndexError:
            # print(f"Warning: IndexError accessing indicator data at index {len(self.data.Close)-1}. Skipping.")
            return # Should not happen if required_len check is correct, but safety first

        # --- Trading Day Check ---
        isTradingTime = True
        if self.trading_days == "Weekdays Only":
            current_timestamp = self.data.index[-1] # Get pandas Timestamp
            # dayofweek: Monday=0, Sunday=6
            isTradingTime = current_timestamp.dayofweek < 5 # 0-4 are Mon-Fri

        if not isTradingTime:
            return # Skip if outside allowed trading days

        # --- Define Crossover/Crossunder Conditions ---
        # Crossover: ma1 crosses above ma3
        buy_crossover = ma1_prev < ma3_prev and ma1_now > ma3_now
        # Crossunder: ma1 crosses below ma3
        sell_crossunder = ma1_prev > ma3_prev and ma1_now < ma3_now

        # --- Define Filter Conditions ---
        buy_filter = ma5_now > filter_ma_now
        sell_filter = ma5_now < filter_ma_now

        # --- Combine Conditions ---
        buy_condition = buy_crossover and buy_filter
        sell_condition = sell_crossunder and sell_filter

        # --- Position Sizing ---
        size_value = self.size_frac
        if not (0 < size_value <= 1):
            # print(f"Warning: Invalid size_frac ({self.size_frac}). Defaulting to 0.1.")
            size_value = 0.1

        # --- Stop Loss and Take Profit Calculation ---
        # Long SL/TP
        sl_long_price = current_price * (1 - self.stoploss_long_pct / 100)
        tp_long_price = current_price * (1 + self.takeProfit_long_pct / 100)
        # Short SL/TP
        sl_short_price = current_price * (1 + self.stoploss_short_pct / 100)
        tp_short_price = current_price * (1 - self.takeProfit_short_pct / 100)

        # --- Entry Logic ---
        # Close existing opposite position before entering new one
        if buy_condition and (self.direction == "Both" or self.direction == "Long Only"):
            if self.position.is_short:
                self.position.close()
                # print(f"Idx {len(self.data.Close)-1}: Closed Short before Long entry.")
            if not self.position: # Only enter if no position exists
                 # Validate SL/TP prices
                 if sl_long_price < current_price < tp_long_price:
                     try:
                         self.buy(sl=sl_long_price, tp=tp_long_price, size=size_value)
                         # print(f"Idx {len(self.data.Close)-1}: BUY @{current_price:.4f}, SL={sl_long_price:.4f}, TP={tp_long_price:.4f}, Size={size_value:.3f}")
                     except AssertionError as e:
                         print(f"ASSERT ERR Buy Order: {e}. Price={current_price:.4f}, SL={sl_long_price:.4f}, TP={tp_long_price:.4f}")
                     except Exception as e:
                         print(f"ERR Buy Order: {e} at index {len(self.data.Close)-1}")
                         traceback.print_exc()
                 else:
                      print(f"Warning: Invalid Long SL/TP (SL={sl_long_price:.4f}, P={current_price:.4f}, TP={tp_long_price:.4f}). Order skipped.")


        elif sell_condition and (self.direction == "Both" or self.direction == "Short Only"):
            if self.position.is_long:
                self.position.close()
                # print(f"Idx {len(self.data.Close)-1}: Closed Long before Short entry.")
            if not self.position: # Only enter if no position exists
                 # Validate SL/TP prices
                 if tp_short_price < current_price < sl_short_price:
                     try:
                         self.sell(sl=sl_short_price, tp=tp_short_price, size=size_value)
                         # print(f"Idx {len(self.data.Close)-1}: SELL @{current_price:.4f}, SL={sl_short_price:.4f}, TP={tp_short_price:.4f}, Size={size_value:.3f}")
                     except AssertionError as e:
                         print(f"ASSERT ERR Sell Order: {e}. Price={current_price:.4f}, SL={sl_short_price:.4f}, TP={tp_short_price:.4f}")
                     except Exception as e:
                         print(f"ERR Sell Order: {e} at index {len(self.data.Close)-1}")
                         traceback.print_exc()
                 else:
                      print(f"Warning: Invalid Short SL/TP (TP={tp_short_price:.4f}, P={current_price:.4f}, SL={sl_short_price:.4f}). Order skipped.")
