#!/usr/bin/env python3
"""
診斷交易記錄問題的腳本
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtest.backtester import BacktestEngine
from strategies.rsi_ema_strategy import RsiEmaStrategy

def create_test_data():
    """創建測試數據"""
    # 創建一個簡單的趨勢數據，確保會觸發交易
    dates = pd.date_range('2024-01-01', periods=1000, freq='H')

    # 創建一個有明顯趨勢的價格序列
    base_price = 50000
    trend = np.linspace(0, 5000, 1000)  # 上升趨勢
    noise = np.random.normal(0, 100, 1000)  # 噪音

    close_prices = base_price + trend + noise

    # 確保 OHLC 數據的邏輯性
    data = pd.DataFrame({
        'Open': close_prices + np.random.normal(0, 50, 1000),
        'High': close_prices + np.abs(np.random.normal(50, 25, 1000)),
        'Low': close_prices - np.abs(np.random.normal(50, 25, 1000)),
        'Close': close_prices,
        'Volume': np.random.randint(1000, 10000, 1000)
    }, index=dates)

    # 確保 High >= max(Open, Close) 和 Low <= min(Open, Close)
    data['High'] = np.maximum(data['High'], np.maximum(data['Open'], data['Close']))
    data['Low'] = np.minimum(data['Low'], np.minimum(data['Open'], data['Close']))

    return data

def analyze_strategy_behavior():
    """分析策略行為"""
    print("=== 策略行為分析 ===")

    # 創建測試數據
    data = create_test_data()
    print(f"測試數據: {len(data)} 行，時間範圍: {data.index[0]} 到 {data.index[-1]}")
    print(f"價格範圍: {data['Close'].min():.2f} - {data['Close'].max():.2f}")

    # 設置策略參數
    strategy_params = {
        'rsi_length': 14,
        'ema_length': 50,  # 使用較短的EMA以便更容易觸發交易
        'rsi_long_entry': 30.0,
        'rsi_long_exit': 70.0,
        'rsi_short_entry': 70.0,
        'rsi_short_exit': 30.0,
        'size_frac': 0.1
    }

    print(f"策略參數: {strategy_params}")

    # 創建回測引擎
    engine = BacktestEngine(
        data=data,
        strategy_class=RsiEmaStrategy,
        strategy_params=strategy_params,
        initial_capital=10000,
        leverage=1.0,
        offset_value=0.0
    )

    print("\n=== 執行回測 ===")
    engine.run()

    # 獲取結果
    results = engine.get_analysis_results()

    print("\n=== 回測結果分析 ===")

    # 檢查性能指標
    metrics = results.get('performance_metrics', {})
    print(f"總交易次數: {metrics.get('# Trades', 'N/A')}")
    print(f"勝率: {metrics.get('Win Rate [%]', 'N/A')}%")
    print(f"總回報: {metrics.get('Return [%]', 'N/A')}%")

    # 檢查交易記錄
    trades_df = results.get('trades', pd.DataFrame())
    print(f"\n=== 交易記錄詳情 ===")
    print(f"交易記錄 DataFrame 形狀: {trades_df.shape}")

    if not trades_df.empty:
        print(f"交易記錄列名: {list(trades_df.columns)}")
        print("\n前5筆交易:")
        print(trades_df.head())

        print("\n交易記錄統計:")
        print(f"- 多單數量: {len(trades_df[trades_df['Size'] > 0])}")
        print(f"- 空單數量: {len(trades_df[trades_df['Size'] < 0])}")

        # 檢查數值是否合理
        print(f"\n數值範圍檢查:")
        print(f"- 進場價格範圍: {trades_df['EntryPrice'].min():.2f} - {trades_df['EntryPrice'].max():.2f}")
        print(f"- 出場價格範圍: {trades_df['ExitPrice'].min():.2f} - {trades_df['ExitPrice'].max():.2f}")
        print(f"- 盈虧範圍: {trades_df['PnL'].min():.2f} - {trades_df['PnL'].max():.2f}")
        print(f"- 回報率範圍: {trades_df['ReturnPct'].min():.4f} - {trades_df['ReturnPct'].max():.4f}")

        # 檢查是否有異常值
        print(f"\n異常值檢查:")
        print(f"- 進場價格為0或負數: {len(trades_df[trades_df['EntryPrice'] <= 0])}")
        print(f"- 出場價格為0或負數: {len(trades_df[trades_df['ExitPrice'] <= 0])}")
        print(f"- Size為0: {len(trades_df[trades_df['Size'] == 0])}")

        # 檢查時間邏輯
        print(f"\n時間邏輯檢查:")
        invalid_time = trades_df[trades_df['ExitTime'] <= trades_df['EntryTime']]
        print(f"- 出場時間早於或等於進場時間的交易: {len(invalid_time)}")

    else:
        print("沒有交易記錄！")

    # 檢查訂單日誌
    order_log = results.get('_order_log', [])
    print(f"\n=== 訂單日誌分析 ===")
    print(f"訂單日誌條目數: {len(order_log)}")

    if order_log:
        print("前5個訂單日誌條目:")
        for i, entry in enumerate(order_log[:5]):
            print(f"{i+1}. {entry}")

        # 統計訂單類型
        buy_orders = [e for e in order_log if e.get('Event') == 'BUY_PLACED']
        sell_orders = [e for e in order_log if e.get('Event') == 'SELL_PLACED']
        close_orders = [e for e in order_log if e.get('Event') == 'CLOSE_ORDER_PLACED']

        print(f"\n訂單統計:")
        print(f"- BUY_PLACED: {len(buy_orders)}")
        print(f"- SELL_PLACED: {len(sell_orders)}")
        print(f"- CLOSE_ORDER_PLACED: {len(close_orders)}")

    return results

def check_data_integrity():
    """檢查數據完整性"""
    print("\n=== 數據完整性檢查 ===")

    # 檢查現有數據文件
    import os
    data_files = [f for f in os.listdir('data') if f.endswith('.csv')]
    print(f"可用數據文件: {data_files}")

    if data_files:
        # 檢查第一個數據文件
        data_file = data_files[0]
        print(f"\n檢查文件: {data_file}")

        try:
            data = pd.read_csv(f'data/{data_file}', index_col=0, parse_dates=True)
            print(f"數據形狀: {data.shape}")
            print(f"列名: {list(data.columns)}")
            print(f"時間範圍: {data.index[0]} 到 {data.index[-1]}")

            # 標準化列名（轉換為大寫）
            column_mapping = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }

            # 重命名列
            data = data.rename(columns=column_mapping)
            print(f"標準化後列名: {list(data.columns)}")

            if 'Close' in data.columns:
                print(f"價格範圍: {data['Close'].min():.2f} - {data['Close'].max():.2f}")

            # 檢查是否有缺失值
            print(f"\n缺失值檢查:")
            for col in data.columns:
                missing = data[col].isna().sum()
                print(f"- {col}: {missing} 個缺失值")

            return data  # 返回標準化的數據

        except Exception as e:
            print(f"讀取數據文件時出錯: {e}")
            return None

def test_with_real_data():
    """使用真實數據測試"""
    print("\n=== 使用真實數據測試 ===")

    # 獲取真實數據
    real_data = check_data_integrity()
    if real_data is None:
        print("無法獲取真實數據，跳過測試")
        return

    # 取一個較小的數據子集進行測試
    test_data = real_data.iloc[-2000:].copy()  # 最近2000個數據點
    print(f"測試數據: {len(test_data)} 行")
    print(f"價格範圍: {test_data['Close'].min():.2f} - {test_data['Close'].max():.2f}")

    # 調整策略參數以更容易觸發交易
    strategy_params = {
        'rsi_length': 14,
        'ema_length': 20,  # 更短的EMA
        'rsi_long_entry': 40.0,  # 更寬鬆的進場條件
        'rsi_long_exit': 60.0,
        'rsi_short_entry': 60.0,
        'rsi_short_exit': 40.0,
        'size_frac': 0.1
    }

    print(f"調整後策略參數: {strategy_params}")

    # 使用更高的初始資金以避免價格過高警告
    initial_capital = 1000000  # 100萬

    # 創建回測引擎
    engine = BacktestEngine(
        data=test_data,
        strategy_class=RsiEmaStrategy,
        strategy_params=strategy_params,
        initial_capital=initial_capital,
        leverage=1.0,
        offset_value=0.0
    )

    print("\n執行真實數據回測...")
    engine.run()

    # 獲取結果
    results = engine.get_analysis_results()

    print("\n=== 真實數據回測結果 ===")

    # 檢查性能指標
    metrics = results.get('performance_metrics', {})
    print(f"總交易次數: {metrics.get('# Trades', 'N/A')}")
    print(f"勝率: {metrics.get('Win Rate [%]', 'N/A')}%")
    print(f"總回報: {metrics.get('Return [%]', 'N/A')}%")

    # 檢查交易記錄
    trades_df = results.get('trades', pd.DataFrame())
    print(f"\n交易記錄: {trades_df.shape[0]} 筆交易")

    if not trades_df.empty:
        print("\n前3筆交易詳情:")
        for i, (_, trade) in enumerate(trades_df.head(3).iterrows()):
            print(f"交易 {i+1}:")
            print(f"  進場時間: {trade['EntryTime']}")
            print(f"  出場時間: {trade['ExitTime']}")
            print(f"  進場價格: {trade['EntryPrice']:.2f}")
            print(f"  出場價格: {trade['ExitPrice']:.2f}")
            print(f"  交易大小: {trade['Size']:.4f}")
            print(f"  盈虧: {trade['PnL']:.2f}")
            print(f"  回報率: {trade['ReturnPct']:.4f}")
            print(f"  標籤: {trade.get('Tag', 'N/A')}")
            print()

    return results

if __name__ == "__main__":
    print("開始診斷交易記錄問題...")

    # 檢查數據完整性
    check_data_integrity()

    # 分析策略行為（使用模擬數據）
    print("\n" + "="*50)
    results1 = analyze_strategy_behavior()

    # 使用真實數據測試
    print("\n" + "="*50)
    results2 = test_with_real_data()

    print("\n=== 診斷完成 ===")
    print("如果交易記錄顯示異常，可能的原因包括:")
    print("1. 策略參數設置導致很少或沒有交易觸發")
    print("2. 數據質量問題（缺失值、異常值等）")
    print("3. 策略邏輯問題")
    print("4. 回測引擎的計算問題")
    print("5. 顯示格式化問題")
    print("6. 數據列名不匹配（小寫 vs 大寫）")
