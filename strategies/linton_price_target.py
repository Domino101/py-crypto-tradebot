# Version 3: Re-introducing LPT state indicators and basic trading logic
import pandas as pd
import numpy as np
import math
# Import the base Strategy class from the backtesting library
try:
    from backtesting import Strategy as BacktestingStrategy
    from backtesting.lib import crossover
    print("Successfully imported backtesting.Strategy in linton_price_target.py (v3)")
except ImportError:
    print("Error: 'backtesting' library not found in linton_price_target.py (v3). Please install it.")
    # Define a dummy class if backtesting is not installed
    class BacktestingStrategy:
        def I(self, func, *args, **kwargs):
             print("Warning: backtesting.Strategy not found, I() called on dummy.")
             try:
                 # Attempt to return something sensible based on input type/shape
                 if len(args) > 0 and hasattr(args[0], 'shape'):
                     # Assuming the first arg might be a Series/array-like for length
                     return pd.Series(np.nan, index=range(len(args[0])))
                 elif len(args) > 0 and isinstance(args[0], (list, np.ndarray)):
                      return pd.Series(np.nan, index=range(len(args[0])))
                 else: return np.nan
             except: return np.nan
        # Provide dummy data attributes expected by the strategy during init and next
        class Data: High, Low, Close = [], [], []
        data = Data()
        class Position: is_long=False; is_short=False; close=lambda:print("Dummy position.close()")
        position = Position()
        # Dummy trading methods
        buy = lambda self: print("Dummy self.buy()")
        sell = lambda self: print("Dummy self.sell()")


# --- Helper Function for ATR (compatible with backtesting data) ---
def calculate_atr_bt(high, low, close, period):
    """Calculates Average True Range (ATR) using pandas Series."""
    if not isinstance(high, pd.Series): high = pd.Series(high)
    if not isinstance(low, pd.Series): low = pd.Series(low)
    if not isinstance(close, pd.Series): close = pd.Series(close)
    if len(high) < period + 1: return pd.Series(np.nan, index=high.index)
    try:
        high_low = high - low
        high_close = abs(high - close.shift(1))
        low_close = abs(low - close.shift(1))
        tr_df = pd.DataFrame({'hl': high_low, 'hc': high_close, 'lc': low_close})
        tr = tr_df.max(axis=1)
        atr = tr.rolling(window=period, min_periods=period).mean()
        return atr
    except Exception as e:
        print(f"Error in calculate_atr_bt: {e}")
        return pd.Series(np.nan, index=high.index)


class LintonPriceTargetStrategy(BacktestingStrategy):
    # --- Parameter Definition for GUI ---
    _params_def = {
        'atr_length':         ('ATR 長度', int, 14, None),
        'atr_multiplier':     ('ATR 乘數 (價格單位)', float, 0.5, None),
        'reversal_amount':    ('反轉單位 (鎖定)', int, 3, None),
        'activation_threshold': ('突破單位 (激活)', int, 1, None),
        'price_target_factor': ('價格目標因子', float, 2.0, None),
        'time_target_factor':  ('時間目標因子 (Thrust Angle)', float, 0.5, None), # Still experimental
    }

    # --- Strategy Parameters ---
    atr_length = 14
    atr_multiplier = 0.5
    reversal_amount = 3
    activation_threshold = 1
    price_target_factor = 2.0
    time_target_factor = 0.5

    def init(self):
        """Initialize the strategy. Calculate indicators and define output arrays."""
        print(f"--- Initializing LintonPriceTargetStrategy (v3 - Indicators + Basic Trades) ---")

        # Ensure data is available
        if not hasattr(self.data, 'Close') or len(self.data.Close) == 0:
             print("Warning: No data available during init.")
             self.atr = pd.Series(dtype=float)
             self.price_unit = pd.Series(dtype=float)
             data_len = 0 # Set length to 0 if no data
        else:
            data_len = len(self.data.Close) # Get length from actual data
            try:
                # Calculate basic ATR and PriceUnit
                self.atr = self.I(calculate_atr_bt,
                                  pd.Series(self.data.High, dtype=float),
                                  pd.Series(self.data.Low, dtype=float),
                                  pd.Series(self.data.Close, dtype=float),
                                  self.atr_length,
                                  name="ATR")
                self.price_unit = self.atr * self.atr_multiplier
            except Exception as e:
                 print(f"Error during self.I calculation in init: {e}")
                 # Use np.full for creating arrays of NaNs
                 self.atr = self.I(lambda: np.full(data_len, np.nan), name="ATR")
                 self.price_unit = self.I(lambda: np.full(data_len, np.nan), name="PriceUnit")

        # --- State Variables (Internal) ---
        self.up_info = self._reset_thrust_info()
        self.down_info = self._reset_thrust_info()
        self.last_low = np.nan
        self.last_high = np.nan
        self.last_low_idx = -1
        self.last_high_idx = -1

        # --- Define Output Indicators using self.I ---
        # Use np.full for initialization matching data length
        self.up_thrust_start = self.I(lambda: np.full(data_len, np.nan), name="UpThrustStart", overlay=True)
        self.up_thrust_end = self.I(lambda: np.full(data_len, np.nan), name="UpThrustEnd", overlay=True)
        self.up_locked = self.I(lambda: np.full(data_len, np.nan), name="UpLocked", overlay=False)
        self.up_active = self.I(lambda: np.full(data_len, np.nan), name="UpActive", overlay=False)
        self.up_activation_lvl = self.I(lambda: np.full(data_len, np.nan), name="UpActivationLvl", overlay=True)
        self.up_negation_lvl = self.I(lambda: np.full(data_len, np.nan), name="UpNegationLvl", overlay=True)
        self.up_target_price = self.I(lambda: np.full(data_len, np.nan), name="UpTargetPrice", overlay=True)

        self.down_thrust_start = self.I(lambda: np.full(data_len, np.nan), name="DownThrustStart", overlay=True)
        self.down_thrust_end = self.I(lambda: np.full(data_len, np.nan), name="DownThrustEnd", overlay=True)
        self.down_locked = self.I(lambda: np.full(data_len, np.nan), name="DownLocked", overlay=False)
        self.down_active = self.I(lambda: np.full(data_len, np.nan), name="DownActive", overlay=False)
        self.down_activation_lvl = self.I(lambda: np.full(data_len, np.nan), name="DownActivationLvl", overlay=True)
        self.down_negation_lvl = self.I(lambda: np.full(data_len, np.nan), name="DownNegationLvl", overlay=True)
        self.down_target_price = self.I(lambda: np.full(data_len, np.nan), name="DownTargetPrice", overlay=True)

        # Signal indicators (for plotting activation points) - Use scatter plot markers
        self.up_signal_marker = self.I(lambda: np.full(data_len, np.nan), name="UpSignal", overlay=True)
        self.down_signal_marker = self.I(lambda: np.full(data_len, np.nan), name="DownSignal", overlay=True)

        print("--- LintonPriceTargetStrategy (v3) init complete. ---")


    def _reset_thrust_info(self):
        # Reset state for a single thrust
        return {'start': np.nan, 'end': np.nan, 'bars': 0, 'locked': False, 'active': False,
                'activation_lvl': np.nan, 'negation_lvl': np.nan, 'target_price': np.nan,
                'target_bars': 0, 'start_idx': -1, 'lock_idx': -1, 'activation_idx': -1}

    def next(self):
        """Process the next data point (bar). Calculate LPT state and execute trades."""
        current_idx = len(self.data.Close) - 1
        # Ensure indicators and data are available and aligned
        # Check if price_unit array is long enough and the current value is valid
        if current_idx < 1 or len(self.price_unit) <= current_idx or pd.isna(self.price_unit[current_idx]) or self.price_unit[current_idx] <= 0:
            self._update_output_indicators() # Update with NaNs if needed
            return

        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        price_unit = self.price_unit[-1] # Use index -1 for current value

        # Store previous state for detecting changes (negation)
        prev_up_negation_lvl = self.up_info['negation_lvl']
        prev_down_negation_lvl = self.down_info['negation_lvl']

        # --- Pivot Detection (Simplified) ---
        if pd.isna(self.last_low) and current_idx > 0:
             if current_idx - 1 >= 0:
                 self.last_low = self.data.Low[-2]; self.last_low_idx = current_idx - 1
                 self.last_high = self.data.High[-2]; self.last_high_idx = current_idx - 1
             else:
                 self.last_low = current_low; self.last_low_idx = current_idx
                 self.last_high = current_high; self.last_high_idx = current_idx

        if not pd.isna(self.last_low):
            if current_low < self.last_low: self.last_low = current_low; self.last_low_idx = current_idx
        else: self.last_low = current_low; self.last_low_idx = current_idx

        if not pd.isna(self.last_high):
             if current_high > self.last_high: self.last_high = current_high; self.last_high_idx = current_idx
        else: self.last_high = current_high; self.last_high_idx = current_idx


        # --- Upside Target Processing ---
        up_activated_this_bar = False
        up_negated_this_bar = False
        # 1. Start New Up Thrust?
        if not pd.isna(self.last_low) and pd.isna(self.up_info['start']) and current_high > self.last_low:
            self.down_info = self._reset_thrust_info()
            self.up_info['start'] = self.last_low; self.up_info['end'] = current_high; self.up_info['bars'] = 1
            self.up_info['locked'] = False; self.up_info['active'] = False
            self.up_info['negation_lvl'] = self.up_info['start']; self.up_info['start_idx'] = self.last_low_idx
            self.last_high = current_high; self.last_high_idx = current_idx

        # 2. Continue Up Thrust
        elif not pd.isna(self.up_info['start']) and not self.up_info['locked'] and current_high > self.up_info['end']:
            self.up_info['end'] = current_high; self.up_info['bars'] += 1
            self.up_info['negation_lvl'] = self.up_info['start']
            self.last_high = current_high; self.last_high_idx = current_idx

        # 3. Lock Up Thrust on Reversal
        elif not pd.isna(self.up_info['start']) and not self.up_info['locked'] and current_low < self.up_info['end'] - (self.reversal_amount * price_unit):
            self.up_info['locked'] = True
            self.up_info['activation_lvl'] = self.up_info['end'] + (self.activation_threshold * price_unit)
            thrust_height = self.up_info['end'] - self.up_info['start']
            if thrust_height > 0:
                self.up_info['target_price'] = self.up_info['end'] + (thrust_height * self.price_target_factor)
                self.up_info['target_bars'] = 0 # Placeholder
            else: self.up_info['target_price'] = np.nan; self.up_info['target_bars'] = 0
            self.up_info['lock_idx'] = current_idx
            self.last_low = current_low; self.last_low_idx = current_idx

        # 4. Activate Up Target
        elif self.up_info['locked'] and not self.up_info['active'] and current_high >= self.up_info['activation_lvl']:
            self.up_info['active'] = True; self.up_info['activation_idx'] = current_idx
            self.last_high = current_high; self.last_high_idx = current_idx
            up_activated_this_bar = True
            self.up_signal_marker[-1] = current_low * 0.99 # Place marker slightly below low

        # 5. Negate Up Target
        if not pd.isna(self.up_info['start']) and current_low <= self.up_info['negation_lvl']:
            if not pd.isna(prev_up_negation_lvl): # Check if it was previously valid before reset
                 up_negated_this_bar = True
            self.up_info = self._reset_thrust_info()
            self.last_low = current_low; self.last_low_idx = current_idx


        # --- Downside Target Processing ---
        down_activated_this_bar = False
        down_negated_this_bar = False
        # 1. Start New Down Thrust?
        if not pd.isna(self.last_high) and pd.isna(self.down_info['start']) and current_low < self.last_high:
            self.up_info = self._reset_thrust_info()
            self.down_info['start'] = self.last_high; self.down_info['end'] = current_low; self.down_info['bars'] = 1
            self.down_info['locked'] = False; self.down_info['active'] = False
            self.down_info['negation_lvl'] = self.down_info['start']; self.down_info['start_idx'] = self.last_high_idx
            self.last_low = current_low; self.last_low_idx = current_idx

        # 2. Continue Down Thrust
        elif not pd.isna(self.down_info['start']) and not self.down_info['locked'] and current_low < self.down_info['end']:
            self.down_info['end'] = current_low; self.down_info['bars'] += 1
            self.down_info['negation_lvl'] = self.down_info['start']
            self.last_low = current_low; self.last_low_idx = current_idx

        # 3. Lock Down Thrust on Reversal (Rally)
        elif not pd.isna(self.down_info['start']) and not self.down_info['locked'] and current_high > self.down_info['end'] + (self.reversal_amount * price_unit):
            self.down_info['locked'] = True
            self.down_info['activation_lvl'] = self.down_info['end'] - (self.activation_threshold * price_unit)
            thrust_height = self.down_info['start'] - self.down_info['end']
            if thrust_height > 0:
                self.down_info['target_price'] = self.down_info['end'] - (thrust_height * self.price_target_factor)
                self.down_info['target_bars'] = 0 # Placeholder
            else: self.down_info['target_price'] = np.nan; self.down_info['target_bars'] = 0
            self.down_info['lock_idx'] = current_idx
            self.last_high = current_high; self.last_high_idx = current_idx

        # 4. Activate Down Target
        elif self.down_info['locked'] and not self.down_info['active'] and current_low <= self.down_info['activation_lvl']:
            self.down_info['active'] = True; self.down_info['activation_idx'] = current_idx
            self.last_low = current_low; self.last_low_idx = current_idx
            down_activated_this_bar = True
            self.down_signal_marker[-1] = current_high * 1.01 # Place marker slightly above high

        # 5. Negate Down Target
        if not pd.isna(self.down_info['start']) and current_high >= self.down_info['negation_lvl']:
             if not pd.isna(prev_down_negation_lvl): # Check if it was previously valid before reset
                 down_negated_this_bar = True
             self.down_info = self._reset_thrust_info()
             self.last_high = current_high; self.last_high_idx = current_idx

        # --- Update Output Indicators ---
        self._update_output_indicators()

        # --- Basic Trading Logic ---
        # Close existing position if negated
        if up_negated_this_bar and self.position.is_long:
            self.position.close()
        elif down_negated_this_bar and self.position.is_short:
            self.position.close()

        # Enter new position on activation if not already in position
        # Ensure we don't immediately close a position opened on the same bar
        if up_activated_this_bar and not self.position: # Check if no position exists
            self.buy()
        elif down_activated_this_bar and not self.position:
            self.sell()


    def _update_output_indicators(self):
        """Helper to update the self.I defined indicators for the current bar."""
        # Use index -1 which corresponds to the current bar in next()
        current_bar_index = -1

        # Check if indicators were initialized (data_len > 0)
        if not hasattr(self, 'up_thrust_start') or len(self.up_thrust_start) == 0:
             return # Don't try to update if indicators are not properly initialized

        try:
            # Update Up Info Indicators
            self.up_thrust_start[-1] = self.up_info['start']
            self.up_thrust_end[-1] = self.up_info['end']
            self.up_locked[-1] = 1 if self.up_info['locked'] else 0
            self.up_active[-1] = 1 if self.up_info['active'] else 0
            self.up_activation_lvl[-1] = self.up_info['activation_lvl']
            self.up_negation_lvl[-1] = self.up_info['negation_lvl']
            self.up_target_price[-1] = self.up_info['target_price']

            # Update Down Info Indicators
            self.down_thrust_start[-1] = self.down_info['start']
            self.down_thrust_end[-1] = self.down_info['end']
            self.down_locked[-1] = 1 if self.down_info['locked'] else 0
            self.down_active[-1] = 1 if self.down_info['active'] else 0
            self.down_activation_lvl[-1] = self.down_info['activation_lvl']
            self.down_negation_lvl[-1] = self.down_info['negation_lvl']
            self.down_target_price[-1] = self.down_info['target_price']

            # Note: Signal markers are updated directly in the activation logic in next()
        except IndexError:
             # This might happen if data length is very small or something is misaligned
             print(f"Warning: IndexError in _update_output_indicators at index {current_bar_index}. Data length: {len(self.data.Close)}")
        except Exception as e:
             print(f"Error in _update_output_indicators: {e}")