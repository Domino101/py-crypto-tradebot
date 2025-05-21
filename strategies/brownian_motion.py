# strategies/brownian_motion.py
import random
import pandas as pd
import pandas_ta as ta
from backtesting import Strategy
import traceback
import numpy as np
import math
from datetime import timedelta

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
        if len(result) != len(source):
            result = result.reindex(source_pd.index)
        return result.values
    except Exception as e:
        print(f"Error in ma_function: {e}")
        traceback.print_exc()
        return np.full(len(source), np.nan)

class BrownianMotionStrategy(Strategy):
    """
    基於布朗運動的短線隨機交易策略。
    每 5 分鐘隨機決定是否開單，方向由模擬的布朗運動決定。
    使用移動追蹤止損。
    """
    # --- Parameter Definition for GUI ---
    _params_def = {
        'entry_probability': ('開單機率 (0-1)', float, 0.5, (0.01, 1.0)), # 每 5 分鐘觸發時的開單機率
        'brownian_volatility': ('布朗運動波動率', float, 0.03, (0.001, 0.1)), # 模擬價格變動的波動率
        'brownian_dt': ('布朗運動時間步長 (秒)', int, 1, (1, 60)), # 模擬的時間步長
        'atr_length':       ('ATR 長度 (用於止損)', int, 14, (2, 100)),      # ATR 週期
        'atr_smoothing':    ('ATR 平滑方法', str, "RMA", ["SMA", "EMA", "RMA", "WMA"]), # ATR 平滑方法
        'ts_activation_pct':('追蹤止損啟動 (%)', float, 2.0, (0.1, 10.0)), # 獲利達到此百分比後啟動追蹤止損
        'ts_trail_pct':     ('追蹤止損回撤 (%)', float, 1.5, (0.1, 10.0)), # 從最高/最低點回撤此百分比觸發止損
        'ts_atr_multiplier':('追蹤止損ATR乘數', float, 1.5, (0.1, 5.0)), # 可選：結合ATR動態調整回撤距離
        'tp_pct':           ('固定止盈 (%)', float, 3.0, (0.1, 20.0)), # 新增固定止盈參數
        'size_frac':        ('投入淨值比例', float, 0.1, (0.01, 0.95)) # 倉位大小佔總資產比例
    }

    # --- Default values ---
    entry_probability = 0.5
    brownian_volatility = 0.03
    brownian_dt = 1 # 1 second dt for simulation step
    atr_length = 14
    atr_smoothing = "RMA"
    ts_activation_pct = 2.0 / 100 # Convert percentage to fraction
    ts_trail_pct = 1.5 / 100      # Convert percentage to fraction
    ts_atr_multiplier = 1.5       # Multiplier for ATR adjustment (optional in risk engine)
    tp_pct = 3.0 / 100            # Convert percentage to fraction
    size_frac = 0.1

    def init(self):
        """初始化策略並計算指標。"""
        print("--- Strategy Init Start (BrownianMotionStrategy) ---")
        try:
            required_attributes = ['Close', 'High', 'Low', 'index']
            print("  檢查必需屬性:", required_attributes)
            if not all(hasattr(self.data, attr) and getattr(self.data, attr) is not None and len(getattr(self.data, attr)) > 0 for attr in required_attributes):
                 missing = [attr for attr in required_attributes if not hasattr(self.data, attr) or getattr(self.data, attr) is None or len(getattr(self.data, attr)) == 0]
                 print(f"  缺少屬性檢查失敗。缺少/空值: {missing}")
                 raise ValueError(f"數據缺少必需/非空屬性: {', '.join(missing)}")
            print("  必需屬性檢查通過。")

            close_series = pd.Series(self.data.Close, index=self.data.index, name='Close')
            high_series = pd.Series(self.data.High, index=self.data.index, name='High')
            low_series = pd.Series(self.data.Low, index=self.data.index, name='Low')
            print(f"  成功創建 Pandas Series。收盤價頭部: {close_series.head().to_list()}")

            # --- ATR 計算 (用於移動追蹤止損參考) ---
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

        # 初始化上次檢查時間
        self.last_check_time = None
        print("--- Strategy Init End ---")


    def next(self):
        """定義下一根 K 棒的邏輯。"""
        current_bar_idx = len(self.data.Close) - 1
        # 確保 ATR 計算有足夠數據
        if current_bar_idx < self.atr_length + 5:
            return

        current_timestamp = self.data.index[-1] # pandas Timestamp

        # --- 頻率控制：每 5 分鐘檢查一次 ---
        if self.last_check_time is None:
            self.last_check_time = current_timestamp
            return # 第一次運行，僅記錄時間

        time_diff = current_timestamp - self.last_check_time
        if time_diff < timedelta(minutes=5):
            return # 未到 5 分鐘，跳過

        # 更新上次檢查時間
        self.last_check_time = current_timestamp
        # print(f"Idx {current_bar_idx}: 5 分鐘檢查點到達 ({current_timestamp})")

        # --- 進場邏輯：僅在沒有持倉時考慮 ---
        if not self.position:
            # --- 隨機決定是否開單 ---
            if random.random() < self.entry_probability:
                # print(f"Idx {current_bar_idx}: 觸發開單機率。")
                # --- 模擬布朗運動決定方向 ---
                current_price = self.data.Close[-1]
                if pd.isna(current_price) or current_price <= 0:
                    print(f"警告: 在索引 {current_bar_idx} 處價格無效 ({current_price})。跳過。")
                    return

                # 簡單布朗運動模擬 (一步)
                # dS = S * volatility * sqrt(dt) * N(0,1)
                # 我們只關心方向，所以簡化為模擬 dW
                dW = self.brownian_volatility * math.sqrt(self.brownian_dt) * random.normalvariate(0, 1)
                # print(f"Idx {current_bar_idx}: Brownian step dW = {dW:.6f}")

                trade_direction = 'buy' if dW > 0 else 'sell'

                # --- 獲取當前 ATR (用於風險引擎參考) ---
                current_atr = self.atr[-1]
                if pd.isna(current_atr) or current_atr <= 0:
                     print(f"警告: 在索引 {current_bar_idx} ATR 無效 ({current_atr})。無法提供給風險引擎。")
                     # 即使 ATR 無效，也可能繼續下單，但風險引擎無法使用 ATR 調整
                     current_atr = None # 標記為無效

                # --- 驗證並設置倉位大小 ---
                size_value = self.size_frac
                if not (0 < size_value <= 1):
                    print(f"警告: 無效的 size_frac ({self.size_frac})。將預設為 0.1。")
                    size_value = 0.1

                # --- 準備傳遞給風險引擎的止損參數 ---
                # 風險引擎將處理實際的移動追蹤邏輯
                # 策略只需提供配置參數
                stop_loss_params = {
                    'type': 'trailing',
                    'activation_pct': self.ts_activation_pct,
                    'trail_pct': self.ts_trail_pct,
                    'atr_multiplier': self.ts_atr_multiplier,
                    'current_atr': current_atr # 提供當前 ATR 值供參考
                }

                # --- 下單 (注意：backtesting 框架的 sl/tp 是固定的，這裡傳遞參數給 live trader) ---
                # 在 backtesting 中，我們無法直接模擬移動止損，
                # 但可以設置一個初始的、較寬的固定止損，或不設置，依賴 backtester 的全局設置。
                # 這裡的重點是為 live trader 準備好參數。
                # 為了在 backtesting 中有基本的保護，可以設置一個基於 ATR 的初始固定止損。
                initial_sl_distance = (current_atr * self.ts_atr_multiplier * 2) if current_atr else (current_price * 0.05) # 備用 5%
                initial_sl_price = None

                try:
                    if trade_direction == 'buy':
                        initial_sl_price = current_price - initial_sl_distance
                        # 設置固定止盈價格
                        tp_price = current_price * (1 + self.tp_pct)
                        if tp_price <= 0:
                            tp_price = current_price * 1.01  # 如果止盈價異常則設為當前價的101%
                        self.buy(size=size_value, sl=initial_sl_price, tp=tp_price)
                    elif trade_direction == 'sell':
                        initial_sl_price = current_price + initial_sl_distance
                        # 設置固定止盈價格
                        tp_price = current_price * (1 - self.tp_pct)
                        if tp_price <= 0:
                            tp_price = current_price * 0.99  # 如果止盈價低於零則設為當前價的99%
                        self.sell(size=size_value, sl=initial_sl_price, tp=tp_price)
                except Exception as e:
                    print(f"下單錯誤: {e}")
                    traceback.print_exc()
