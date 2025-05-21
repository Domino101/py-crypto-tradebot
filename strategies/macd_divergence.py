import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting import Strategy
from collections import deque
import traceback

# Helper functions (find_pivots, ma_function) - Keep as is
def find_pivots(series: pd.Series, lbL: int, lbR: int):
    series_np = series.to_numpy(); n = len(series_np)
    is_ph = np.zeros(n, dtype=bool); is_pl = np.zeros(n, dtype=bool)
    for i in range(n):
        if pd.isna(series_np[i]): continue
        is_strict_ph = True; is_strict_pl = True; pivot_val = series_np[i]
        for k in range(max(0, i - lbL), i):
            if pd.isna(series_np[k]): continue
            if series_np[k] >= pivot_val: is_strict_ph = False
            if series_np[k] <= pivot_val: is_strict_pl = False
            if not is_strict_ph and not is_strict_pl: break
        if not is_strict_ph and not is_strict_pl: continue
        for k in range(i + 1, min(n, i + lbR + 1)):
            if pd.isna(series_np[k]): continue
            if series_np[k] >= pivot_val: is_strict_ph = False
            if series_np[k] <= pivot_val: is_strict_pl = False
            if not is_strict_ph and not is_strict_pl: break
        if is_strict_ph: is_ph[i] = True
        if is_strict_pl: is_pl[i] = True
    return pd.Series(is_ph, index=series.index), pd.Series(is_pl, index=series.index)

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
        else: result = ta.ema(source_pd, length=length)
        if len(result) != len(source): result = result.reindex(source_pd.index)
        return result.values
    except Exception as e: print(f"Error in ma_function: {e}"); return np.full(len(source), np.nan)


# Strategy Class - Corrected Attribute Check
class MacdDivergenceStrategy(Strategy):

    # --- Parameter Definition for GUI ---
    _params_def = {
        'fast_length':      ('MACD 快線', int, 13, None),
        'slow_length':      ('MACD 慢線', int, 34, None),
        'signal_length':    ('MACD 信號線', int, 9, (1, 50)),
        'atr_length':       ('ATR 長度', int, 13, None),
        'atr_multiplier':   ('ATR 乘數', float, 1.5, (0.1, 10.0)),
        'max_search_vals':  ('背離搜索K數', int, 5, (2, 10)),
        'bigger_less_than': ('背離比率', float, 0.618, (0.01, 0.99)),
        'lbL':              ('Pivot 左 K', int, 1, None),
        'lbR':              ('Pivot 右 K', int, 1, None),
        # 'size_frac':        ('投入淨值比例', float, 0.1, (0.01, 0.95)) # Remove size_frac
        'order_cash_value': ('每次下單金額', float, 2000, (100, 100000)) # Add fixed cash value per order
    }

    # --- Default values ---
    fast_length = 13; slow_length = 34; signal_length = 9
    lbR = 1; lbL = 1
    max_search_vals = 5; bigger_less_than = 0.618
    atr_length = 13; atr_smoothing = "RMA"; atr_multiplier = 1.5
    # size_frac = 0.1 # Remove size_frac
    order_cash_value = 2000 # Default fixed cash value

    # --- Internal ---
    maxarraysize = 20; order_id_counter = 0

    def init(self):
        print("--- Strategy Init Start (MacdDivergenceStrategy - Equity Sizing) ---")
        # --- *** Add Debugging for self.data *** ---
        print(f"  type(self.data): {type(self.data)}")
        # Print available attributes to see what backtesting.py provides
        print(f"  dir(self.data): {dir(self.data)}")
        # --- *** End Debugging *** ---

        # --- *** Corrected Attribute Check *** ---
        try:
            # Use FULL names: Close, High, Low, index
            required_attributes = ['Close', 'High', 'Low', 'index']
            print("  Checking for required attributes:", required_attributes)
            if not all(hasattr(self.data, attr) and getattr(self.data, attr) is not None and len(getattr(self.data, attr)) > 0 for attr in required_attributes):
                 missing = [attr for attr in required_attributes if not hasattr(self.data, attr) or getattr(self.data, attr) is None or len(getattr(self.data, attr)) == 0]
                 print(f"  Missing attributes check failed. Missing/Empty: {missing}") # Print what's missing
                 raise ValueError(f"Data missing required/non-empty attributes: {', '.join(missing)}")
            print("  Required attributes check passed.")

            # --- Create Pandas Series ---
            close_series = pd.Series(self.data.Close, index=self.data.index, name='Close')
            high_series = pd.Series(self.data.High, index=self.data.index, name='High')
            low_series = pd.Series(self.data.Low, index=self.data.index, name='Low')
            print(f"  Successfully created Pandas Series. Close head: {close_series.head().to_list()}")
        except ValueError as ve: # Catch the specific error we might raise
             print(f"FATAL ERROR checking data attributes: {ve}")
             traceback.print_exc()
             raise RuntimeError(f"Failed initialization due to data issues: {ve}") # Re-raise as RuntimeError
        except Exception as e: # Catch other potential errors during Series creation
             print(f"FATAL ERROR creating Pandas Series: {e}")
             traceback.print_exc()
             raise RuntimeError(f"Failed to create essential Series: {e}")
        # --- *** End Corrected Attribute Check & Series Creation *** ---

        # --- MACD Calculation ---
        macd_df = None
        try:
            if len(close_series.dropna()) < self.slow_length+self.signal_length: raise ValueError("Not enough data for MACD.")
            macd_df = ta.macd(close_series, fast=self.fast_length, slow=self.slow_length, signal=self.signal_length, append=False)
            if not isinstance(macd_df, pd.DataFrame): raise ValueError("ta.macd failed.")
            mc,sc,hc=f"MACD_{self.fast_length}_{self.slow_length}_{self.signal_length}", f"MACDs_{self.fast_length}_{self.slow_length}_{self.signal_length}", f"MACDh_{self.fast_length}_{self.slow_length}_{self.signal_length}"
            exp=[mc,sc,hc];
            if not all(c in macd_df.columns for c in exp):
                if all(c in macd_df.columns for c in ['MACD','MACDs','MACDh']): mc,sc,hc = 'MACD','MACDs','MACDh'
                else: raise ValueError("MACD columns not found.")
        except Exception as e: print(f"ERR MACD: {e}. NaNs used."); traceback.print_exc(); nan_s=pd.Series(np.nan, index=self.data.index); mc,sc,hc='MACD','MACDs','MACDh'; macd_df=pd.DataFrame({mc:nan_s.copy(), sc:nan_s.copy(), hc:nan_s.copy()}, index=self.data.index)
        self.macd_line=self.I(lambda df: df[mc].values, macd_df, name="MACD"); self.signal_line=self.I(lambda df: df[sc].values, macd_df, name="Signal"); self.macd_hist=self.I(lambda df: df[hc].values, macd_df, name="Hist")

        # --- ATR Calculation ---
        try:
            tr_s = ta.true_range(high_series, low_series, close_series);
            if not isinstance(tr_s, pd.Series): raise ValueError("ta.true_range failed.")
            self.atr=self.I(ma_function, tr_s, self.atr_length, self.atr_smoothing, name="ATR");
            if np.isnan(self.atr).all(): print("Warn: ATR all NaNs.")
            self.atr_multiplied=self.I(lambda atr, mult: atr*mult, self.atr, self.atr_multiplier, name="ATR_Mult")
            self.atr_high_band=self.I(lambda h, atr_m: h+atr_m, self.data.High, self.atr_multiplied, name="ATR_High") # Use self.data.High (_Array)
            self.atr_low_band=self.I(lambda l, atr_m: l-atr_m, self.data.Low, self.atr_multiplied, name="ATR_Low")   # Use self.data.Low (_Array)
        except Exception as e: print(f"ERR ATR: {e}. NaNs used."); traceback.print_exc(); nan_a=np.full(len(self.data),np.nan); self.atr=self.I(lambda:nan_a); self.atr_multiplied=self.I(lambda:nan_a); self.atr_high_band=self.I(lambda:nan_a); self.atr_low_band=self.I(lambda:nan_a)

        # --- Pivot Calculation ---
        try:
            min_hist_len=max(self.lbL, self.lbR)+1; hist_s=macd_df[hc]; valid_hist=hist_s.dropna()
            if len(valid_hist) >= min_hist_len:
                 is_ph_s, is_pl_s = find_pivots(hist_s, self.lbL, self.lbR)
                 self.is_pivot_high=self.I(lambda s: s.reindex(self.data.index).fillna(False).values, is_ph_s, name="IsPH")
                 self.is_pivot_low=self.I(lambda s: s.reindex(self.data.index).fillna(False).values, is_pl_s, name="IsPL")
            else: raise ValueError("Not enough hist data for pivots.")
        except Exception as e: print(f"ERR Pivots: {e}. False used."); traceback.print_exc(); false_a=np.zeros(len(self.data),dtype=bool); self.is_pivot_high=self.I(lambda: false_a); self.is_pivot_low=self.I(lambda: false_a)

        # --- Initialize Pivot Storage ---
        self.ph_pivots = deque(maxlen=self.maxarraysize); self.pl_pivots = deque(maxlen=self.maxarraysize)
        print("--- Strategy Init End ---")


    def next(self):
        # (next method remains the same as the previous version using size_frac)
        current_bar_idx = len(self.data.Close) - 1
        required_len = self.slow_length + self.signal_length + max(self.lbL, self.lbR) + self.lbR + 5
        if current_bar_idx < required_len: return
        prev_bar_idx = current_bar_idx - 1; ref_idx_offset = self.lbR - 1
        if prev_bar_idx < 0: return
        ph_found = False; pl_found = False
        try:
            if len(self.is_pivot_high) <= prev_bar_idx: return
            ph_found = self.is_pivot_high[prev_bar_idx]; pl_found = self.is_pivot_low[prev_bar_idx]
            if ph_found or pl_found:
                pivot_bar_idx = prev_bar_idx - self.lbR
                if pivot_bar_idx < 0 or len(self.macd_hist) <= pivot_bar_idx: return
                pivot_macd = self.macd_hist[pivot_bar_idx];
                if pd.isna(pivot_macd): return
                if ph_found and pivot_macd > 0:
                    pivot_price = self.data.High[pivot_bar_idx]
                    if not pd.isna(pivot_price): self.ph_pivots.append((pivot_bar_idx, pivot_macd, pivot_price))
                if pl_found and pivot_macd < 0:
                    pivot_price = self.data.Low[pivot_bar_idx]
                    if not pd.isna(pivot_price): self.pl_pivots.append((pivot_bar_idx, pivot_macd, pivot_price))
        except IndexError: return
        except Exception as e: print(f"ERR Pivot Storage: {e}"); traceback.print_exc(); return
        pos_reg_div = False
        if pl_found and len(self.pl_pivots) >= 2:
            curr_p=self.pl_pivots[-1]; min_pl=curr_p[1]
            for i in range(2, min(self.max_search_vals+1, len(self.pl_pivots)+1)):
                prev_p=self.pl_pivots[-i]; min_pl=min(min_pl, prev_p[1])
                if not any(map(pd.isna,[curr_p[1],curr_p[2],prev_p[1],prev_p[2]])):
                    if (curr_p[2]<prev_p[2] and curr_p[1]>prev_p[1] and prev_p[1]<=min_pl and abs(prev_p[1])*self.bigger_less_than<=abs(curr_p[1])): pos_reg_div=True; break
        neg_reg_div = False
        if ph_found and len(self.ph_pivots) >= 2:
            curr_p=self.ph_pivots[-1]; max_ph=curr_p[1]
            for i in range(2, min(self.max_search_vals+1, len(self.ph_pivots)+1)):
                prev_p=self.ph_pivots[-i]; max_ph=max(max_ph, prev_p[1])
                if not any(map(pd.isna,[curr_p[1],curr_p[2],prev_p[1],prev_p[2]])):
                    if (curr_p[2]>prev_p[2] and curr_p[1]<prev_p[1] and prev_p[1]>=max_ph and abs(prev_p[1])*self.bigger_less_than>=abs(curr_p[1])): neg_reg_div=True; break
        # --- Add Logging ---
        log_prefix = f"Bar {current_bar_idx} ({self.data.index[-1]}):"
        if pl_found:
            print(f"{log_prefix} Pivot Low found. Last PL: {self.pl_pivots[-1] if self.pl_pivots else 'None'}")
        if ph_found:
            print(f"{log_prefix} Pivot High found. Last PH: {self.ph_pivots[-1] if self.ph_pivots else 'None'}")
        if pos_reg_div:
            print(f"{log_prefix} Positive Regular Divergence DETECTED. CurrP: {curr_p}, PrevP: {prev_p}, MinPL: {min_pl}")
        if neg_reg_div:
            print(f"{log_prefix} Negative Regular Divergence DETECTED. CurrP: {curr_p}, PrevP: {prev_p}, MaxPH: {max_ph}")
        # --- End Logging ---

        if neg_reg_div or pos_reg_div:
            # Correct ref_idx to match Pine Script's [lbR-1] logic
            ref_idx = current_bar_idx - self.lbR
            if ref_idx < 0 or ref_idx >= len(self.data.Close): return # Ensure index is valid

            # Ensure the index for ATR bands is also valid and shifted correctly
            atr_ref_idx = ref_idx -1 # Use previous bar's ATR for SL/TP calculation
            if atr_ref_idx < 0: return # Check if atr_ref_idx is valid

            try:
                # Use corrected ref_idx for entry limit
                entry_limit = self.data.Close[ref_idx]
                # Use corrected atr_ref_idx for ATR bands
                ref_high_band = self.atr_high_band[atr_ref_idx]
                ref_low_band = self.atr_low_band[atr_ref_idx]

                if pd.isna(entry_limit) or entry_limit <= 0 or pd.isna(ref_high_band) or pd.isna(ref_low_band): return

                # SL/TP based on the previous bar's ATR bands
                short_sl = ref_high_band; short_tp = ref_low_band; long_sl = ref_low_band; long_tp = ref_high_band
                # Calculate order size based on fixed cash value
                if entry_limit <= 0: return # Avoid division by zero or negative price
                order_size = self.order_cash_value / entry_limit
                if order_size <= 0: return # Ensure positive order size

                # Use limit orders to match Pine Script behavior
                if neg_reg_div:
                    if short_sl > entry_limit and short_tp < entry_limit:
                        # Remove closing existing long position to allow multiple trades
                        # if self.position.is_long: self.position.close()
                        # Place short limit order with calculated size
                        self.order_id_counter+=1; tag=f"S_{self.order_id_counter}"
                        print(f"{log_prefix} Placing SHORT Limit Order: Entry={entry_limit:.4f}, SL={short_sl:.4f}, TP={short_tp:.4f}, Size={order_size:.8f}, Tag={tag}") # Log order placement
                        self.sell(limit=entry_limit, sl=short_sl, tp=short_tp, size=order_size, tag=tag) # Use calculated order_size
                elif pos_reg_div:
                    if long_sl < entry_limit and long_tp > entry_limit:
                        # Remove closing existing short position to allow multiple trades
                        # if self.position.is_short: self.position.close()
                        # Place long limit order with calculated size
                        self.order_id_counter+=1; tag=f"L_{self.order_id_counter}"
                        print(f"{log_prefix} Placing LONG Limit Order: Entry={entry_limit:.4f}, SL={long_sl:.4f}, TP={long_tp:.4f}, Size={order_size:.8f}, Tag={tag}") # Log order placement
                        self.buy(limit=entry_limit, sl=long_sl, tp=long_tp, size=order_size, tag=tag) # Use calculated order_size
            except IndexError: print(f"{log_prefix} IndexError during order placement."); return
            except AssertionError as e: print(f"{log_prefix} ASSERT ERR Order: {e}. Size: {order_size}.")
            except Exception as e: print(f"ERR Order: {e}"); traceback.print_exc(); return

# if __name__ == '__main__': pass
