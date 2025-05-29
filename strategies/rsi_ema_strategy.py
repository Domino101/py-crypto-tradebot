import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting import Strategy
import traceback

# Helper function (ma_function) - Keep as is or adapt if needed
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
        if len(result) != len(source): result = result.reindex(source_pd.index)
        return result.values
    except Exception as e: print(f"Error in ma_function: {e}"); return np.full(len(source), np.nan)


# Strategy Class for RSI + EMA
class RsiEmaStrategy(Strategy):

    # --- Parameter Definition for GUI ---
    _params_def = {
        'rsi_length':   ('RSI 長度', int, 14, (2, 100)),
        'ema_length':   ('EMA 長度', int, 200, (10, 500)),
        'rsi_long_entry': ('RSI 做多閾值', float, 20.0, (1.0, 49.0)),
        'rsi_long_exit': ('RSI 多單離場閾值', float, 50.0, (50.0, 99.0)),
        'rsi_short_entry':('RSI 做空閾值', float, 80.0, (51.0, 99.0)),
        'rsi_short_exit':('RSI 空單離場閾值', float, 50.0, (1.0, 50.0)),
        'size_frac':    ('投入淨值比例', float, 0.1, (0.01, 0.95))
    }

    # --- Default values ---
    rsi_length = 14
    ema_length = 50  # 使用較短的EMA，更敏感
    rsi_long_entry = 30.0  # RSI超賣區域
    rsi_long_exit = 70.0   # RSI超買區域
    rsi_short_entry = 70.0 # RSI超買區域
    rsi_short_exit = 30.0  # RSI超賣區域
    size_frac = 0.1

    # --- Internal ---
    order_id_counter = 0

    def init(self):
        print("--- Strategy Init Start (RsiEmaStrategy - Equity Sizing) ---")
        # --- Data Validation ---
        try:
            required_attributes = ['Close', 'High', 'Low', 'index'] # Keep High/Low for potential future use or consistency
            print("  Checking for required attributes:", required_attributes)
            if not all(hasattr(self.data, attr) and getattr(self.data, attr) is not None and len(getattr(self.data, attr)) > 0 for attr in required_attributes):
                 missing = [attr for attr in required_attributes if not hasattr(self.data, attr) or getattr(self.data, attr) is None or len(getattr(self.data, attr)) == 0]
                 print(f"  Missing attributes check failed. Missing/Empty: {missing}")
                 raise ValueError(f"Data missing required/non-empty attributes: {', '.join(missing)}")
            print("  Required attributes check passed.")

            # --- Create Pandas Series ---
            close_series = pd.Series(self.data.Close, index=self.data.index, name='Close')
            # high_series = pd.Series(self.data.High, index=self.data.index, name='High') # Keep if needed later
            # low_series = pd.Series(self.data.Low, index=self.data.index, name='Low')   # Keep if needed later
            print(f"  Successfully created Pandas Series. Close head: {close_series.head().to_list()}")
        except ValueError as ve:
             print(f"FATAL ERROR checking data attributes: {ve}")
             traceback.print_exc()
             raise RuntimeError(f"Failed initialization due to data issues: {ve}")
        except Exception as e:
             print(f"FATAL ERROR creating Pandas Series: {e}")
             traceback.print_exc()
             raise RuntimeError(f"Failed to create essential Series: {e}")

        # --- Indicator Calculation ---
        # RSI
        try:
            if len(close_series.dropna()) < self.rsi_length: raise ValueError("Not enough data for RSI.")
            rsi_series = ta.rsi(close_series, length=self.rsi_length)
            if not isinstance(rsi_series, pd.Series): raise ValueError("ta.rsi failed.")
            self.rsi = self.I(lambda s: s.values, rsi_series, name="RSI")
            if np.isnan(self.rsi).all(): print("Warn: RSI all NaNs.")
        except Exception as e:
            print(f"ERR RSI: {e}. NaNs used."); traceback.print_exc()
            nan_s = np.full(len(self.data), np.nan)
            self.rsi = self.I(lambda: nan_s, name="RSI")

        # EMA
        try:
            if len(close_series.dropna()) < self.ema_length: raise ValueError("Not enough data for EMA.")
            # Use the helper ma_function which handles potential errors
            ema_values = ma_function(close_series, self.ema_length, "EMA")
            self.ema = self.I(lambda: ema_values, name=f"EMA_{self.ema_length}")
            if np.isnan(self.ema).all(): print(f"Warn: EMA_{self.ema_length} all NaNs.")
        except Exception as e:
            print(f"ERR EMA: {e}. NaNs used."); traceback.print_exc()
            nan_s = np.full(len(self.data), np.nan)
            self.ema = self.I(lambda: nan_s, name=f"EMA_{self.ema_length}")

        print("--- Strategy Init End ---")


    def next(self):
        current_bar_idx = len(self.data.Close) - 1
        # Ensure we have enough data for indicators to be calculated
        required_len = max(self.rsi_length, self.ema_length) + 5 # Add a buffer
        if current_bar_idx < required_len:
            # print(f"Bar {current_bar_idx}: Skipping (required_len={required_len})") # Optional: uncomment for very detailed debug
            return

        try:
            # Get current values
            current_close = self.data.Close[-1]
            current_rsi = self.rsi[-1]
            current_ema = self.ema[-1]

            # --- Add Detailed Logging ---
            # print(f"Bar {current_bar_idx}: Close={current_close:.2f}, RSI={current_rsi:.2f}, EMA={current_ema:.2f}, Position={self.position}") # Log values every bar

            # Check for NaN values - skip if any critical value is NaN
            if pd.isna(current_close) or pd.isna(current_rsi) or pd.isna(current_ema):
                # print(f"Bar {current_bar_idx}: Skipping due to NaN values (Close={current_close}, RSI={current_rsi}, EMA={current_ema})")
                return

            # --- Trading Logic ---
            size_value = self.size_frac
            if not (0 < size_value < 1): size_value = 0.1 # Default safety check

            # 修改策略邏輯：更實用的RSI均值回歸策略
            # 多單：RSI超賣時買入（不考慮EMA，純粹的均值回歸）
            long_entry_condition = current_rsi < self.rsi_long_entry
            long_exit_condition = current_rsi > self.rsi_long_exit

            # 空單：RSI超買時賣出（不考慮EMA，純粹的均值回歸）
            short_entry_condition = current_rsi > self.rsi_short_entry
            short_exit_condition = current_rsi < self.rsi_short_exit

            # --- Long Logic ---
            # Entry Condition: RSI < entry threshold (超賣買入)
            if long_entry_condition:
                if not self.position.is_long:
                    # Close any existing short position before entering long
                    if self.position.is_short:
                        self.position.close()
                        print(f"Bar {current_bar_idx}: Closed Short (Reason: Long Entry Signal)")
                    # Enter Long
                    self.order_id_counter += 1
                    tag = f"L_{self.order_id_counter}"
                    # Note: No SL/TP defined in the request, placing market order
                    self.buy(size=size_value, tag=tag)
                    print(f"Bar {current_bar_idx}: Entered Long (RSI: {current_rsi:.2f} < {self.rsi_long_entry}) Tag: {tag}")

            # Exit Condition: RSI > exit threshold (超買賣出) - 改為獨立的if
            if long_exit_condition:
                if self.position.is_long:
                    self.position.close()
                    print(f"Bar {current_bar_idx}: Closed Long (Reason: RSI {current_rsi:.2f} > {self.rsi_long_exit})")


            # --- Short Logic ---
            # Entry Condition: RSI > entry threshold (超買賣出)
            if short_entry_condition:
                 if not self.position.is_short:
                    # Close any existing long position before entering short
                    if self.position.is_long:
                        self.position.close()
                        print(f"Bar {current_bar_idx}: Closed Long (Reason: Short Entry Signal)")
                    # Enter Short
                    self.order_id_counter += 1
                    tag = f"S_{self.order_id_counter}"
                    # Note: No SL/TP defined in the request, placing market order
                    self.sell(size=size_value, tag=tag)
                    print(f"Bar {current_bar_idx}: Entered Short (RSI: {current_rsi:.2f} > {self.rsi_short_entry}) Tag: {tag}")

            # Exit Condition: RSI < exit threshold (超賣平倉) - 改為獨立的if
            if short_exit_condition:
                if self.position.is_short:
                    self.position.close()
                    print(f"Bar {current_bar_idx}: Closed Short (Reason: RSI {current_rsi:.2f} < {self.rsi_short_exit})")
            # else: # Optional: Log when no action is taken
                # print(f"Bar {current_bar_idx}: No action taken. Conditions: LongEntry={long_entry_condition}, LongExit={long_exit_condition}, ShortEntry={short_entry_condition}, ShortExit={short_exit_condition}, Position={self.position}")


        except IndexError:
            # This might happen if accessing [-1] when data is too short, though the initial check should prevent it.
            print(f"Warn: IndexError at bar {current_bar_idx}. Data length: {len(self.data.Close)}")
            return
        except Exception as e:
            print(f"ERR Next Loop Bar {current_bar_idx}: {e}")
            traceback.print_exc()
            return

# if __name__ == '__main__': pass # Keep commented out or remove
