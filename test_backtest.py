#!/usr/bin/env python3
"""
測試回測功能和按鈕狀態的腳本
"""

import tkinter as tk
import time
import threading
from gui.app import TradingAppGUI

def test_backtest_buttons():
    """測試回測按鈕狀態"""
    print("開始測試回測按鈕狀態...")
    
    # 創建GUI
    root = tk.Tk()
    app = TradingAppGUI(root)
    
    def check_button_states():
        """檢查按鈕狀態"""
        time.sleep(2)  # 等待GUI完全初始化
        
        print("\n=== 初始按鈕狀態 ===")
        print(f"查看圖表按鈕狀態: {app.view_plot_button['state']}")
        print(f"查看交易按鈕狀態: {app.view_trades_button['state']}")
        print(f"查看訂單日誌按鈕狀態: {app.view_order_log_button['state']}")
        
        # 模擬加載數據
        print("\n=== 模擬加載數據 ===")
        app.symbol_var.set("BTCUSDT")
        app.interval_var.set("1h")
        
        # 模擬數據準備完成
        import pandas as pd
        import numpy as np
        
        # 創建模擬數據
        dates = pd.date_range('2024-01-01', periods=1000, freq='H')
        data = pd.DataFrame({
            'Open': np.random.randn(1000).cumsum() + 50000,
            'High': np.random.randn(1000).cumsum() + 50100,
            'Low': np.random.randn(1000).cumsum() + 49900,
            'Close': np.random.randn(1000).cumsum() + 50000,
            'Volume': np.random.randint(100, 1000, 1000)
        }, index=dates)
        
        app.current_data = data
        app.current_data_info = {
            'symbol': 'BTCUSDT',
            'interval': '1h',
            'start_date': dates[0].date(),
            'end_date': dates[-1].date(),
            'rows': len(data)
        }
        
        print("數據已準備完成")
        
        # 檢查數據準備後的按鈕狀態
        print("\n=== 數據準備後按鈕狀態 ===")
        print(f"查看圖表按鈕狀態: {app.view_plot_button['state']}")
        print(f"查看交易按鈕狀態: {app.view_trades_button['state']}")
        print(f"查看訂單日誌按鈕狀態: {app.view_order_log_button['state']}")
        
        # 模擬回測完成
        print("\n=== 模擬回測完成 ===")
        app.backtest_results = {
            'trades': pd.DataFrame({
                'EntryTime': [dates[100], dates[200]],
                'ExitTime': [dates[150], dates[250]],
                'Size': [1.0, -1.0],
                'ReturnPct': [0.05, -0.02]
            }),
            '_order_log': [
                {'Timestamp': dates[100], 'Event': 'Buy', 'Size': 1.0},
                {'Timestamp': dates[150], 'Event': 'Sell', 'Size': -1.0}
            ],
            'performance_metrics': {
                'Return [%]': 5.0,
                'Sharpe Ratio': 1.2,
                'Max. Drawdown [%]': -2.0
            }
        }
        app.backtest_plot_path = "plots/test_plot.html"
        
        # 手動調用 toggle_controls 來更新按鈕狀態
        app.toggle_controls(enabled=True)
        
        print("\n=== 回測完成後按鈕狀態 ===")
        print(f"查看圖表按鈕狀態: {app.view_plot_button['state']}")
        print(f"查看交易按鈕狀態: {app.view_trades_button['state']}")
        print(f"查看訂單日誌按鈕狀態: {app.view_order_log_button['state']}")
        
        # 測試完成，關閉GUI
        print("\n測試完成！")
        root.after(1000, root.quit)
    
    # 在後台線程中運行測試
    test_thread = threading.Thread(target=check_button_states, daemon=True)
    test_thread.start()
    
    # 啟動GUI
    root.mainloop()

if __name__ == "__main__":
    test_backtest_buttons()
