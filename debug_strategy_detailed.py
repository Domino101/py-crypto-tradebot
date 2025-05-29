#!/usr/bin/env python3
"""
詳細調試策略內部執行情況
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from backtest.backtester import BacktestEngine
from strategies.rsi_ema_strategy import RsiEmaStrategy

def test_strategy_step_by_step():
    """逐步測試策略執行"""
    print("=== 逐步調試策略執行 ===")
    
    # 讀取數據
    data = pd.read_csv('data/BTCUSDT_202204080000_202504080108_1h.csv', index_col=0, parse_dates=True)
    data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
    
    # 取一個小的數據集進行詳細分析
    test_data = data.iloc[-200:].copy()  # 最近200個數據點
    print(f"測試數據: {len(test_data)} 行")
    print(f"價格範圍: {test_data['Close'].min():.2f} - {test_data['Close'].max():.2f}")
    
    # 手動計算指標
    close_series = test_data['Close']
    rsi = ta.rsi(close_series, length=14)
    ema = ta.ema(close_series, length=50)
    
    print(f"\n指標計算結果:")
    print(f"- RSI有效值: {rsi.dropna().shape[0]}")
    print(f"- EMA有效值: {ema.dropna().shape[0]}")
    print(f"- RSI範圍: {rsi.min():.2f} - {rsi.max():.2f}")
    
    # 檢查策略條件
    rsi_long_entry = 30.0
    rsi_long_exit = 70.0
    rsi_short_entry = 70.0
    rsi_short_exit = 30.0
    
    # 找到滿足條件的點
    long_entry_points = test_data[rsi < rsi_long_entry]
    long_exit_points = test_data[rsi > rsi_long_exit]
    short_entry_points = test_data[rsi > rsi_short_entry]
    short_exit_points = test_data[rsi < rsi_short_exit]
    
    print(f"\n條件滿足情況:")
    print(f"- 多單進場 (RSI < 30): {len(long_entry_points)} 次")
    print(f"- 多單出場 (RSI > 70): {len(long_exit_points)} 次")
    print(f"- 空單進場 (RSI > 70): {len(short_entry_points)} 次")
    print(f"- 空單出場 (RSI < 30): {len(short_exit_points)} 次")
    
    if len(long_entry_points) > 0:
        print(f"\n多單進場點詳情:")
        for i, (timestamp, row) in enumerate(long_entry_points.head(3).iterrows()):
            rsi_val = rsi.loc[timestamp]
            print(f"  {i+1}. {timestamp}: Close={row['Close']:.2f}, RSI={rsi_val:.2f}")
    
    if len(short_entry_points) > 0:
        print(f"\n空單進場點詳情:")
        for i, (timestamp, row) in enumerate(short_entry_points.head(3).iterrows()):
            rsi_val = rsi.loc[timestamp]
            print(f"  {i+1}. {timestamp}: Close={row['Close']:.2f}, RSI={rsi_val:.2f}")
    
    # 現在用回測引擎測試
    print(f"\n=== 使用回測引擎測試 ===")
    
    strategy_params = {
        'rsi_length': 14,
        'ema_length': 50,
        'rsi_long_entry': 30.0,
        'rsi_long_exit': 70.0,
        'rsi_short_entry': 70.0,
        'rsi_short_exit': 30.0,
        'size_frac': 0.1
    }
    
    # 使用更高的初始資金
    initial_capital = 10000000  # 1000萬
    
    engine = BacktestEngine(
        data=test_data,
        strategy_class=RsiEmaStrategy,
        strategy_params=strategy_params,
        initial_capital=initial_capital,
        leverage=1.0,
        offset_value=0.0
    )
    
    print("執行回測...")
    engine.run()
    
    results = engine.get_analysis_results()
    
    print(f"\n回測結果:")
    metrics = results.get('performance_metrics', {})
    print(f"- 總交易次數: {metrics.get('# Trades', 'N/A')}")
    print(f"- 勝率: {metrics.get('Win Rate [%]', 'N/A')}%")
    print(f"- 總回報: {metrics.get('Return [%]', 'N/A')}%")
    
    trades_df = results.get('trades', pd.DataFrame())
    print(f"- 交易記錄: {trades_df.shape[0]} 筆")
    
    if not trades_df.empty:
        print(f"\n交易詳情:")
        for i, (_, trade) in enumerate(trades_df.iterrows()):
            print(f"  交易 {i+1}:")
            print(f"    進場: {trade['EntryTime']} @ {trade['EntryPrice']:.2f}")
            print(f"    出場: {trade['ExitTime']} @ {trade['ExitPrice']:.2f}")
            print(f"    大小: {trade['Size']:.4f}")
            print(f"    盈虧: {trade['PnL']:.2f}")
            print(f"    回報: {trade['ReturnPct']:.4f}")
    
    # 檢查訂單日誌
    order_log = results.get('_order_log', [])
    print(f"\n訂單日誌: {len(order_log)} 條")
    
    if order_log:
        print("最近的訂單:")
        for i, entry in enumerate(order_log[-5:]):
            print(f"  {i+1}. {entry}")

def test_simple_rsi_strategy():
    """測試一個極簡的RSI策略"""
    print(f"\n=== 測試極簡RSI策略 ===")
    
    # 創建一個非常簡單的測試數據
    dates = pd.date_range('2024-01-01', periods=100, freq='h')
    
    # 創建一個有明顯RSI信號的價格序列
    base_price = 50000
    # 創建一個先下跌再上漲的價格序列，確保RSI會觸發信號
    price_changes = []
    for i in range(100):
        if i < 30:
            price_changes.append(-100)  # 下跌，RSI會變低
        elif i < 50:
            price_changes.append(50)    # 小幅上漲
        elif i < 70:
            price_changes.append(200)   # 大幅上漲，RSI會變高
        else:
            price_changes.append(-50)   # 回調
    
    prices = [base_price]
    for change in price_changes:
        prices.append(prices[-1] + change + np.random.normal(0, 20))
    
    prices = prices[1:]  # 移除第一個元素
    
    test_data = pd.DataFrame({
        'Open': prices,
        'High': [p + abs(np.random.normal(0, 50)) for p in prices],
        'Low': [p - abs(np.random.normal(0, 50)) for p in prices],
        'Close': prices,
        'Volume': [1000] * 100
    }, index=dates)
    
    # 確保OHLC邏輯正確
    test_data['High'] = np.maximum(test_data['High'], np.maximum(test_data['Open'], test_data['Close']))
    test_data['Low'] = np.minimum(test_data['Low'], np.minimum(test_data['Open'], test_data['Close']))
    
    print(f"測試數據: {len(test_data)} 行")
    print(f"價格範圍: {test_data['Close'].min():.2f} - {test_data['Close'].max():.2f}")
    
    # 計算RSI
    rsi = ta.rsi(test_data['Close'], length=14)
    print(f"RSI範圍: {rsi.min():.2f} - {rsi.max():.2f}")
    
    # 檢查RSI條件
    rsi_low = (rsi < 30).sum()
    rsi_high = (rsi > 70).sum()
    print(f"RSI < 30: {rsi_low} 次")
    print(f"RSI > 70: {rsi_high} 次")
    
    # 回測
    strategy_params = {
        'rsi_length': 14,
        'ema_length': 50,
        'rsi_long_entry': 30.0,
        'rsi_long_exit': 70.0,
        'rsi_short_entry': 70.0,
        'rsi_short_exit': 30.0,
        'size_frac': 0.1
    }
    
    engine = BacktestEngine(
        data=test_data,
        strategy_class=RsiEmaStrategy,
        strategy_params=strategy_params,
        initial_capital=1000000,
        leverage=1.0,
        offset_value=0.0
    )
    
    print("\n執行極簡策略回測...")
    engine.run()
    
    results = engine.get_analysis_results()
    
    print(f"\n極簡策略結果:")
    metrics = results.get('performance_metrics', {})
    print(f"- 總交易次數: {metrics.get('# Trades', 'N/A')}")
    
    trades_df = results.get('trades', pd.DataFrame())
    print(f"- 交易記錄: {trades_df.shape[0]} 筆")
    
    if not trades_df.empty:
        print(f"成功！策略產生了交易。")
        for i, (_, trade) in enumerate(trades_df.head(3).iterrows()):
            print(f"  交易 {i+1}: {trade['EntryTime']} -> {trade['ExitTime']}, 盈虧: {trade['PnL']:.2f}")
    else:
        print("仍然沒有交易產生，可能是策略代碼本身有問題。")

if __name__ == "__main__":
    test_strategy_step_by_step()
    test_simple_rsi_strategy()
