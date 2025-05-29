#!/usr/bin/env python3
"""
深度診斷策略邏輯問題
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

def debug_rsi_ema_logic():
    """調試RSI+EMA策略邏輯"""
    print("=== 深度調試策略邏輯 ===")
    
    # 讀取真實數據
    data = pd.read_csv('data/BTCUSDT_202204080000_202504080108_1h.csv', index_col=0, parse_dates=True)
    
    # 標準化列名
    column_mapping = {
        'open': 'Open',
        'high': 'High', 
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }
    data = data.rename(columns=column_mapping)
    
    # 取最近1000個數據點
    test_data = data.iloc[-1000:].copy()
    print(f"測試數據: {len(test_data)} 行")
    print(f"價格範圍: {test_data['Close'].min():.2f} - {test_data['Close'].max():.2f}")
    
    # 策略參數
    rsi_length = 14
    ema_length = 20
    rsi_long_entry = 40.0
    rsi_long_exit = 60.0
    rsi_short_entry = 60.0
    rsi_short_exit = 40.0
    
    print(f"\n策略參數:")
    print(f"- RSI長度: {rsi_length}")
    print(f"- EMA長度: {ema_length}")
    print(f"- RSI多單進場: < {rsi_long_entry}")
    print(f"- RSI多單出場: > {rsi_long_exit}")
    print(f"- RSI空單進場: > {rsi_short_entry}")
    print(f"- RSI空單出場: < {rsi_short_exit}")
    
    # 計算指標
    close_series = test_data['Close']
    
    # 計算RSI
    rsi = ta.rsi(close_series, length=rsi_length)
    print(f"\nRSI計算結果:")
    print(f"- RSI範圍: {rsi.min():.2f} - {rsi.max():.2f}")
    print(f"- RSI平均值: {rsi.mean():.2f}")
    print(f"- 有效RSI值數量: {rsi.dropna().shape[0]}")
    
    # 計算EMA
    ema = ta.ema(close_series, length=ema_length)
    print(f"\nEMA計算結果:")
    print(f"- EMA範圍: {ema.min():.2f} - {ema.max():.2f}")
    print(f"- 有效EMA值數量: {ema.dropna().shape[0]}")
    
    # 檢查條件觸發情況
    print(f"\n=== 條件觸發分析 ===")
    
    # 多單進場條件: RSI < 40 AND Close > EMA
    long_rsi_condition = rsi < rsi_long_entry
    long_ema_condition = close_series > ema
    long_entry_condition = long_rsi_condition & long_ema_condition
    
    print(f"多單進場條件分析:")
    print(f"- RSI < {rsi_long_entry}: {long_rsi_condition.sum()} 次")
    print(f"- Close > EMA: {long_ema_condition.sum()} 次")
    print(f"- 兩個條件同時滿足: {long_entry_condition.sum()} 次")
    
    # 空單進場條件: RSI > 60 AND Close < EMA
    short_rsi_condition = rsi > rsi_short_entry
    short_ema_condition = close_series < ema
    short_entry_condition = short_rsi_condition & short_ema_condition
    
    print(f"\n空單進場條件分析:")
    print(f"- RSI > {rsi_short_entry}: {short_rsi_condition.sum()} 次")
    print(f"- Close < EMA: {short_ema_condition.sum()} 次")
    print(f"- 兩個條件同時滿足: {short_entry_condition.sum()} 次")
    
    # 檢查具體的觸發點
    if long_entry_condition.sum() > 0:
        print(f"\n多單進場觸發點:")
        trigger_points = test_data[long_entry_condition].head(5)
        for i, (timestamp, row) in enumerate(trigger_points.iterrows()):
            rsi_val = rsi.loc[timestamp]
            ema_val = ema.loc[timestamp]
            print(f"  {i+1}. {timestamp}: Close={row['Close']:.2f}, RSI={rsi_val:.2f}, EMA={ema_val:.2f}")
    
    if short_entry_condition.sum() > 0:
        print(f"\n空單進場觸發點:")
        trigger_points = test_data[short_entry_condition].head(5)
        for i, (timestamp, row) in enumerate(trigger_points.iterrows()):
            rsi_val = rsi.loc[timestamp]
            ema_val = ema.loc[timestamp]
            print(f"  {i+1}. {timestamp}: Close={row['Close']:.2f}, RSI={rsi_val:.2f}, EMA={ema_val:.2f}")
    
    # 檢查RSI和EMA的關係
    print(f"\n=== RSI和價格關係分析 ===")
    
    # RSI分布
    rsi_valid = rsi.dropna()
    print(f"RSI分布:")
    print(f"- < 30 (超賣): {(rsi_valid < 30).sum()} 次 ({(rsi_valid < 30).mean()*100:.1f}%)")
    print(f"- 30-40: {((rsi_valid >= 30) & (rsi_valid < 40)).sum()} 次")
    print(f"- 40-60: {((rsi_valid >= 40) & (rsi_valid < 60)).sum()} 次")
    print(f"- 60-70: {((rsi_valid >= 60) & (rsi_valid < 70)).sum()} 次")
    print(f"- > 70 (超買): {(rsi_valid > 70).sum()} 次 ({(rsi_valid > 70).mean()*100:.1f}%)")
    
    # 價格相對於EMA的位置
    price_above_ema = (close_series > ema).sum()
    price_below_ema = (close_series < ema).sum()
    print(f"\n價格相對於EMA:")
    print(f"- 價格 > EMA: {price_above_ema} 次 ({price_above_ema/len(close_series)*100:.1f}%)")
    print(f"- 價格 < EMA: {price_below_ema} 次 ({price_below_ema/len(close_series)*100:.1f}%)")
    
    # 建議調整參數
    print(f"\n=== 參數調整建議 ===")
    
    # 如果沒有觸發，建議放寬條件
    if long_entry_condition.sum() == 0 and short_entry_condition.sum() == 0:
        print("沒有任何交易觸發，建議:")
        print("1. 放寬RSI閾值 (例如: 多單 < 50, 空單 > 50)")
        print("2. 使用更短的EMA (例如: 10或15)")
        print("3. 移除EMA條件，只使用RSI")
        print("4. 檢查數據是否在趨勢市場中")
        
        # 測試更寬鬆的條件
        print(f"\n測試更寬鬆的條件:")
        loose_long = rsi < 50
        loose_short = rsi > 50
        print(f"- RSI < 50: {loose_long.sum()} 次")
        print(f"- RSI > 50: {loose_short.sum()} 次")

def test_simple_strategy():
    """測試一個簡單的策略"""
    print(f"\n=== 測試簡化策略 ===")
    
    # 讀取數據
    data = pd.read_csv('data/BTCUSDT_202204080000_202504080108_1h.csv', index_col=0, parse_dates=True)
    data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
    
    # 取最近500個數據點
    test_data = data.iloc[-500:].copy()
    
    # 計算簡單移動平均
    test_data['SMA_20'] = test_data['Close'].rolling(20).mean()
    test_data['SMA_50'] = test_data['Close'].rolling(50).mean()
    
    # 簡單的金叉死叉策略
    test_data['Signal'] = 0
    test_data.loc[test_data['SMA_20'] > test_data['SMA_50'], 'Signal'] = 1  # 多頭
    test_data.loc[test_data['SMA_20'] < test_data['SMA_50'], 'Signal'] = -1  # 空頭
    
    # 找到信號變化點
    test_data['Signal_Change'] = test_data['Signal'].diff()
    
    buy_signals = test_data[test_data['Signal_Change'] == 2]  # 從-1變為1
    sell_signals = test_data[test_data['Signal_Change'] == -2]  # 從1變為-1
    
    print(f"簡單SMA策略結果:")
    print(f"- 買入信號: {len(buy_signals)} 次")
    print(f"- 賣出信號: {len(sell_signals)} 次")
    
    if len(buy_signals) > 0:
        print(f"最近的買入信號:")
        for i, (timestamp, row) in enumerate(buy_signals.tail(3).iterrows()):
            print(f"  {timestamp}: Close={row['Close']:.2f}, SMA20={row['SMA_20']:.2f}, SMA50={row['SMA_50']:.2f}")

if __name__ == "__main__":
    debug_rsi_ema_logic()
    test_simple_strategy()
