#!/usr/bin/env python3
"""
最終測試腳本 - 驗證所有修復
"""

import pandas as pd
import numpy as np
from backtest.backtester import BacktestEngine
from strategies.rsi_ema_strategy import RsiEmaStrategy

def test_complete_workflow():
    """測試完整的工作流程"""
    print("=== 完整工作流程測試 ===")
    
    # 1. 讀取真實數據並標準化列名
    print("1. 讀取和標準化數據...")
    data = pd.read_csv('data/BTCUSDT_202204080000_202504080108_1h.csv', index_col=0, parse_dates=True)
    
    # 標準化列名（模擬GUI中的處理）
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
    print(f"   數據形狀: {test_data.shape}")
    print(f"   列名: {list(test_data.columns)}")
    print(f"   價格範圍: {test_data['Close'].min():.2f} - {test_data['Close'].max():.2f}")
    
    # 2. 設置策略參數
    print("\n2. 設置策略參數...")
    strategy_params = {
        'rsi_length': 14,
        'ema_length': 50,
        'rsi_long_entry': 30.0,
        'rsi_long_exit': 70.0,
        'rsi_short_entry': 70.0,
        'rsi_short_exit': 30.0,
        'size_frac': 0.1
    }
    print(f"   策略參數: {strategy_params}")
    
    # 3. 創建回測引擎
    print("\n3. 創建回測引擎...")
    engine = BacktestEngine(
        data=test_data,
        strategy_class=RsiEmaStrategy,
        strategy_params=strategy_params,
        initial_capital=1000000,  # 使用高初始資金避免警告
        leverage=1.0,
        offset_value=0.0
    )
    
    # 4. 執行回測
    print("\n4. 執行回測...")
    engine.run()
    
    # 5. 獲取和分析結果
    print("\n5. 分析結果...")
    results = engine.get_analysis_results()
    
    # 性能指標
    metrics = results.get('performance_metrics', {})
    print(f"\n=== 性能指標 ===")
    print(f"總交易次數: {metrics.get('# Trades', 'N/A')}")
    print(f"勝率: {metrics.get('Win Rate [%]', 'N/A')}%")
    print(f"總回報: {metrics.get('Return [%]', 'N/A')}%")
    print(f"夏普比率: {metrics.get('Sharpe Ratio', 'N/A')}")
    print(f"最大回撤: {metrics.get('Max. Drawdown [%]', 'N/A')}%")
    
    # 交易記錄
    trades_df = results.get('trades', pd.DataFrame())
    print(f"\n=== 交易記錄 ===")
    print(f"交易記錄數量: {len(trades_df)}")
    
    if not trades_df.empty:
        print(f"交易記錄列名: {list(trades_df.columns)}")
        print(f"\n前3筆交易:")
        for i, (_, trade) in enumerate(trades_df.head(3).iterrows()):
            print(f"  交易 {i+1}:")
            print(f"    進場時間: {trade['EntryTime']}")
            print(f"    出場時間: {trade['ExitTime']}")
            print(f"    進場價格: {trade['EntryPrice']:.2f}")
            print(f"    出場價格: {trade['ExitPrice']:.2f}")
            print(f"    交易大小: {trade['Size']:.4f}")
            print(f"    盈虧: {trade['PnL']:.2f}")
            print(f"    回報率: {trade['ReturnPct']:.4f}")
            print(f"    標籤: {trade.get('Tag', 'N/A')}")
        
        # 驗證數值合理性
        print(f"\n=== 數值驗證 ===")
        print(f"進場價格範圍: {trades_df['EntryPrice'].min():.2f} - {trades_df['EntryPrice'].max():.2f}")
        print(f"出場價格範圍: {trades_df['ExitPrice'].min():.2f} - {trades_df['ExitPrice'].max():.2f}")
        print(f"盈虧範圍: {trades_df['PnL'].min():.2f} - {trades_df['PnL'].max():.2f}")
        print(f"回報率範圍: {trades_df['ReturnPct'].min():.4f} - {trades_df['ReturnPct'].max():.4f}")
        
        # 檢查異常值
        invalid_entries = trades_df[trades_df['EntryPrice'] <= 0]
        invalid_exits = trades_df[trades_df['ExitPrice'] <= 0]
        invalid_sizes = trades_df[trades_df['Size'] == 0]
        
        print(f"\n=== 異常值檢查 ===")
        print(f"無效進場價格: {len(invalid_entries)} 筆")
        print(f"無效出場價格: {len(invalid_exits)} 筆")
        print(f"無效交易大小: {len(invalid_sizes)} 筆")
        
        if len(invalid_entries) == 0 and len(invalid_exits) == 0 and len(invalid_sizes) == 0:
            print("✅ 所有交易記錄數值正常")
        else:
            print("❌ 發現異常交易記錄")
    
    # 訂單日誌
    order_log = results.get('_order_log', [])
    print(f"\n=== 訂單日誌 ===")
    print(f"訂單日誌條目數: {len(order_log)}")
    
    if order_log:
        print(f"最近5個訂單:")
        for i, entry in enumerate(order_log[-5:]):
            print(f"  {i+1}. {entry}")
    
    # 6. 測試結果
    print(f"\n=== 測試結果總結 ===")
    
    success_criteria = [
        ("策略執行", len(order_log) > 0),
        ("交易產生", len(trades_df) > 0),
        ("數值正確", len(trades_df) == 0 or (
            trades_df['EntryPrice'].min() > 0 and 
            trades_df['ExitPrice'].min() > 0 and
            trades_df['Size'].abs().min() > 0
        )),
        ("性能指標", metrics.get('# Trades', 0) == len(trades_df))
    ]
    
    all_passed = True
    for criterion, passed in success_criteria:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{criterion}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 所有測試通過！交易記錄問題已修復！")
        print("現在您可以正常使用GUI進行回測，查看交易記錄、圖表和訂單日誌。")
    else:
        print("❌ 仍有問題需要解決")
    print(f"{'='*50}")
    
    return results

if __name__ == "__main__":
    test_complete_workflow()
