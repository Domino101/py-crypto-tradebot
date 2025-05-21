# strategies/random_coin_flip.py
import random
import pandas as pd
import pandas_ta as ta # 導入 pandas_ta
from backtesting import Strategy
import traceback
import numpy as np # 導入 numpy

# Helper function (copied from macd_divergence for ATR calculation consistency)
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
        # Ensure the result has the same index as the input source
        if len(result) != len(source):
            result = result.reindex(source_pd.index)
        return result.values
    except Exception as e:
        print(f"Error in ma_function: {e}")
        traceback.print_exc()
        return np.full(len(source), np.nan)


class RandomCoinFlipStrategy(Strategy):
    """
    一個隨機進場（像拋硬幣一樣）的策略，
    具有 RSI 過濾器和基於 ATR 的動態停損/停利。
    """
    # --- Parameter Definition for GUI ---
    _params_def = {
        'rsi_length':       ('RSI 長度', int, 14, (2, 100)),      # RSI 週期
        'rsi_upper_limit':  ('RSI 做多上限', float, 70.0, (50.0, 100.0)), # RSI 高於此值不做多
        'rsi_lower_limit':  ('RSI 做空下限', float, 30.0, (0.0, 50.0)),   # RSI 低於此值不做空
        'atr_length':       ('ATR 長度', int, 14, (2, 100)),      # ATR 週期
        'atr_sl_multiplier':('ATR 停損乘數', float, 1.5, (0.1, 10.0)), # ATR 乘數決定停損距離
        'rr_ratio':         ('風險回報比', float, 1.5, (0.1, 10.0)), # 停利距離 = 停損距離 * rr_ratio
        'size_frac':        ('投入淨值比例', float, 0.1, (0.01, 0.95)) # 倉位大小佔總資產比例
    }

    # --- Default values ---
    rsi_length = 14
    rsi_upper_limit = 70.0
    rsi_lower_limit = 30.0
    atr_length = 14
    atr_smoothing = "RMA" # ATR 平滑方法，與 MACD 策略保持一致
    atr_sl_multiplier = 1.5
    rr_ratio = 1.5 # 原始是 3% / 2% = 1.5
    size_frac = 0.1

    def init(self):
        """初始化策略並計算指標。"""
        print("--- Strategy Init Start (RandomCoinFlipStrategy_v2) ---")
        # 基本的數據檢查
        try:
            required_attributes = ['Close', 'High', 'Low', 'index']
            print("  檢查必需屬性:", required_attributes)
            if not all(hasattr(self.data, attr) and getattr(self.data, attr) is not None and len(getattr(self.data, attr)) > 0 for attr in required_attributes):
                 missing = [attr for attr in required_attributes if not hasattr(self.data, attr) or getattr(self.data, attr) is None or len(getattr(self.data, attr)) == 0]
                 print(f"  缺少屬性檢查失敗。缺少/空值: {missing}")
                 raise ValueError(f"數據缺少必需/非空屬性: {', '.join(missing)}")
            print("  必需屬性檢查通過。")

            # --- 創建 Pandas Series ---
            close_series = pd.Series(self.data.Close, index=self.data.index, name='Close')
            high_series = pd.Series(self.data.High, index=self.data.index, name='High')
            low_series = pd.Series(self.data.Low, index=self.data.index, name='Low')
            print(f"  成功創建 Pandas Series。收盤價頭部: {close_series.head().to_list()}")

            # --- RSI 計算 ---
            if len(close_series.dropna()) >= self.rsi_length:
                self.rsi = self.I(ta.rsi, close_series, length=self.rsi_length, name="RSI")
                print(f"  RSI 計算完成。最後值: {self.rsi[-1] if len(self.rsi) > 0 else 'N/A'}")
            else:
                print(f"警告: 數據不足 ({len(close_series.dropna())}) 無法計算 RSI({self.rsi_length})。將使用 NaN。")
                self.rsi = self.I(lambda: np.full(len(self.data), np.nan), name="RSI") # 返回 NaN 數組

            # --- ATR 計算 ---
            if len(high_series.dropna()) >= self.atr_length and len(low_series.dropna()) >= self.atr_length and len(close_series.dropna()) >= self.atr_length:
                tr_s = ta.true_range(high_series, low_series, close_series)
                if isinstance(tr_s, pd.Series):
                     self.atr = self.I(ma_function, tr_s, self.atr_length, self.atr_smoothing, name="ATR")
                     print(f"  ATR 計算完成。最後值: {self.atr[-1] if len(self.atr) > 0 else 'N/A'}")
                     if np.isnan(self.atr).all(): print("警告: ATR 全是 NaN。")
                else:
                     print("警告: ta.true_range 未返回 Series。ATR 將使用 NaN。")
                     self.atr = self.I(lambda: np.full(len(self.data), np.nan), name="ATR")
            else:
                print(f"警告: 數據不足無法計算 ATR({self.atr_length})。將使用 NaN。")
                self.atr = self.I(lambda: np.full(len(self.data), np.nan), name="ATR")

        except ValueError as ve:
             print(f"FATAL ERROR 檢查數據屬性: {ve}")
             traceback.print_exc()
             raise RuntimeError(f"因數據問題初始化失敗: {ve}")
        except Exception as e:
             print(f"FATAL ERROR 初始化指標時出錯: {e}")
             traceback.print_exc()
             raise RuntimeError(f"初始化指標失敗: {e}")
        print("--- Strategy Init End ---")
        # 初始化上次決策的小時時間戳
        self.last_decision_hour_ts = None

    def next(self):
        """定義下一根 K 棒的邏輯。"""
        # 確保指標和價格數據足夠
        # 需要當前價格、RSI 和 ATR
        current_bar_idx = len(self.data.Close) - 1
        # 檢查指標是否有足夠的計算長度 (保守估計)
        required_len = max(self.rsi_length, self.atr_length) + 5
        if current_bar_idx < required_len:
            return # 數據或指標計算不足

        # 獲取最新的價格和指標值
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_atr = self.atr[-1]

        # 驗證當前值
        if pd.isna(current_price) or current_price <= 0 or pd.isna(current_rsi) or pd.isna(current_atr) or current_atr <= 0:
            # print(f"警告: 在索引 {current_bar_idx} 處的值無效 (Price={current_price}, RSI={current_rsi}, ATR={current_atr})。跳過此 K 棒。")
            return # 如果任何值無效，跳過

        # --- 小時頻率控制 ---
        current_timestamp = self.data.index[-1] # 獲取當前 K 線的時間戳 (pandas Timestamp)
        current_hour_ts = current_timestamp.floor('H') # 將當前時間戳截斷到小時

        # 檢查是否進入了新的一小時（相對於上次決策）
        allow_decision_this_bar = (self.last_decision_hour_ts is None or current_hour_ts > self.last_decision_hour_ts)

        # --- 進場邏輯：僅在沒有持倉 且 到達新的一小時 且 允許決策時進場 ---
        if not self.position and allow_decision_this_bar:
            # --- 記錄本次決策嘗試的小時時間戳 ---
            self.last_decision_hour_ts = current_hour_ts
            # print(f"Idx {current_bar_idx}: New hour ({current_hour_ts}). Attempting random decision...") # Debugging

            # --- 執行隨機決策和下單邏輯 ---
            # 拋硬幣：0 代表買入，1 代表賣出
            coin_flip = random.randint(0, 1)

            # --- RSI 過濾 ---
            buy_signal_allowed = True
            sell_signal_allowed = True

            if current_rsi > self.rsi_upper_limit:
                buy_signal_allowed = False # RSI 過高，禁止做多
                # print(f"Idx {current_bar_idx}: RSI ({current_rsi:.2f}) > {self.rsi_upper_limit:.2f}, 禁止做多。")
            if current_rsi < self.rsi_lower_limit:
                sell_signal_allowed = False # RSI 過低，禁止做空
                # print(f"Idx {current_bar_idx}: RSI ({current_rsi:.2f}) < {self.rsi_lower_limit:.2f}, 禁止做空。")

            # --- 決定交易方向 ---
            trade_direction = None # None, 'buy', 'sell'
            if coin_flip == 0 and buy_signal_allowed:
                trade_direction = 'buy'
            elif coin_flip == 1 and sell_signal_allowed:
                trade_direction = 'sell'
            # else:
                # print(f"Idx {current_bar_idx}: 隨機方向 ({'買' if coin_flip == 0 else '賣'}) 被 RSI 過濾。")


            # --- 如果有允許的交易方向，計算動態 SL/TP 並下單 ---
            if trade_direction:
                # 計算基於 ATR 的停損距離
                sl_distance = current_atr * self.atr_sl_multiplier
                if sl_distance <= 0: # 確保距離為正
                    print(f"警告: 在索引 {current_bar_idx} 計算出的 SL 距離無效 ({sl_distance:.4f})。跳過下單。")
                    return

                # 計算停利距離
                tp_distance = sl_distance * self.rr_ratio
                if tp_distance <= 0: # 確保距離為正
                    print(f"警告: 在索引 {current_bar_idx} 計算出的 TP 距離無效 ({tp_distance:.4f})。跳過下單。")
                    return

                # 計算絕對的 SL/TP 價格
                if trade_direction == 'buy':
                    buy_sl = current_price - sl_distance
                    buy_tp = current_price + tp_distance
                    # 確保 SL < Price < TP
                    if not (buy_sl < current_price < buy_tp):
                         print(f"警告: 買入 SL/TP 計算無效 (SL={buy_sl:.4f}, Price={current_price:.4f}, TP={buy_tp:.4f})。跳過下單。")
                         return
                else: # trade_direction == 'sell'
                    sell_sl = current_price + sl_distance
                    sell_tp = current_price - tp_distance
                    # 確保 TP < Price < SL
                    if not (sell_tp < current_price < sell_sl):
                         print(f"警告: 賣出 SL/TP 計算無效 (TP={sell_tp:.4f}, Price={current_price:.4f}, SL={sell_sl:.4f})。跳過下單。")
                         return

                # 驗證並設置倉位大小
                size_value = self.size_frac
                if not (0 < size_value <= 1):
                    print(f"警告: 無效的 size_frac ({self.size_frac})。將預設為 0.1。")
                    size_value = 0.1

                # --- 下單 ---
                try:
                    if trade_direction == 'buy':
                        self.buy(sl=buy_sl, tp=buy_tp, size=size_value)
                        # print(f"Idx {current_bar_idx}: 下買單 @{current_price:.4f}, SL={buy_sl:.4f}, TP={buy_tp:.4f}, Size={size_value:.3f}")
                    else: # trade_direction == 'sell'
                        self.sell(sl=sell_sl, tp=sell_tp, size=size_value)
                        # print(f"Idx {current_bar_idx}: 下賣單 @{current_price:.4f}, SL={sell_sl:.4f}, TP={sell_tp:.4f}, Size={size_value:.3f}")

                except AssertionError as e:
                    print(f"ASSERT ERR 下單錯誤: {e}. Price={current_price:.4f}, Size={size_value:.3f}, Dir={trade_direction}, ATR={current_atr:.4f}")
                except Exception as e:
                    print(f"ERR 下單錯誤: {e} at index {current_bar_idx}")
                    traceback.print_exc()


# 可選：添加 if __name__ == '__main__': 塊
# if __name__ == '__main__':
#     # 如何獨立測試此策略的示例（需要數據設置）
#     # from backtesting import Backtest
#     # import pandas as pd
#     #
#     # # 在此處加載您的數據，例如從 CSV 文件
#     # data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)
#     #
#     # bt = Backtest(data, RandomCoinFlipStrategy, cash=10000, commission=.002)
#     # stats = bt.run()
#     # print(stats)
#     # bt.plot()
#     pass
