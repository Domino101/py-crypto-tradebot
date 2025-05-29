#!/usr/bin/env python3
"""
測試實盤交易UI功能
"""

import tkinter as tk
import time
import threading
from gui.app import TradingAppGUI

def test_live_trading_ui():
    """測試實盤交易UI"""
    print("開始測試實盤交易UI...")
    
    # 創建GUI
    root = tk.Tk()
    app = TradingAppGUI(root)
    
    def test_ui_components():
        """測試UI組件"""
        time.sleep(2)  # 等待GUI完全初始化
        
        print("\n=== 測試UI組件 ===")
        
        # 切換到實盤模式
        print("1. 切換到實盤模式...")
        app.mode_var.set("live")
        app.on_mode_change()
        
        # 檢查實盤控件是否存在
        print("2. 檢查實盤控件...")
        
        controls_to_check = [
            ('exchange_combobox', '交易所選擇'),
            ('live_symbol_entry', '交易對輸入'),
            ('live_qty_entry', '交易數量輸入'),
            ('live_interval_combobox', '時間框架選擇'),
            ('paper_trading_var', '模擬盤選項'),
            ('balance_var', '帳戶餘額顯示'),
            ('positions_var', '持倉顯示'),
            ('orders_var', '訂單顯示')
        ]
        
        all_controls_exist = True
        for control_name, description in controls_to_check:
            if hasattr(app, control_name):
                print(f"   ✅ {description} ({control_name}) - 存在")
                
                # 測試控件值
                if control_name == 'exchange_combobox':
                    print(f"      當前值: {app.exchange_combobox.get()}")
                elif control_name == 'live_symbol_entry':
                    print(f"      當前值: {app.live_symbol_entry.get()}")
                elif control_name == 'live_qty_entry':
                    print(f"      當前值: {app.live_qty_entry.get()}")
                elif control_name == 'live_interval_combobox':
                    print(f"      當前值: {app.live_interval_combobox.get()}")
                elif control_name == 'paper_trading_var':
                    print(f"      當前值: {app.paper_trading_var.get()}")
                elif control_name.endswith('_var'):
                    var = getattr(app, control_name)
                    print(f"      當前值: {var.get()}")
            else:
                print(f"   ❌ {description} ({control_name}) - 不存在")
                all_controls_exist = False
        
        # 測試按鈕狀態
        print("\n3. 檢查按鈕狀態...")
        print(f"   開始按鈕文字: {app.start_button['text']}")
        print(f"   開始按鈕狀態: {app.start_button['state']}")
        
        if hasattr(app, 'stop_button'):
            print(f"   停止按鈕狀態: {app.stop_button['state']}")
        
        # 測試策略選擇
        print("\n4. 檢查策略選擇...")
        strategies = app.strategy_combobox['values']
        print(f"   可用策略: {list(strategies)}")
        
        if strategies:
            app.strategy_combobox.set(strategies[0])
            print(f"   選擇策略: {strategies[0]}")
            app.update_strategy_params_ui()
            print("   策略參數UI已更新")
        
        # 測試參數驗證（不實際啟動交易）
        print("\n5. 測試參數驗證...")
        try:
            # 設置測試參數
            app.exchange_combobox.set("Alpaca")
            app.live_symbol_entry.delete(0, tk.END)
            app.live_symbol_entry.insert(0, "BTC/USD")
            app.live_qty_entry.delete(0, tk.END)
            app.live_qty_entry.insert(0, "0.001")
            app.live_interval_combobox.set("1h")
            app.paper_trading_var.set(True)
            
            print("   測試參數已設置:")
            print(f"     交易所: {app.exchange_combobox.get()}")
            print(f"     交易對: {app.live_symbol_entry.get()}")
            print(f"     數量: {app.live_qty_entry.get()}")
            print(f"     時間框架: {app.live_interval_combobox.get()}")
            print(f"     模擬盤: {app.paper_trading_var.get()}")
            
            # 測試參數讀取（不啟動交易）
            exchange = app.exchange_combobox.get()
            symbol = app.live_symbol_entry.get()
            quantity = float(app.live_qty_entry.get())
            interval = app.live_interval_combobox.get()
            paper_mode = app.paper_trading_var.get()
            
            print("   參數讀取成功:")
            print(f"     交易所: {exchange}")
            print(f"     交易對: {symbol}")
            print(f"     數量: {quantity}")
            print(f"     時間框架: {interval}")
            print(f"     模擬盤: {paper_mode}")
            
        except Exception as e:
            print(f"   ❌ 參數驗證失敗: {e}")
            all_controls_exist = False
        
        # 測試結果
        print(f"\n=== 測試結果 ===")
        if all_controls_exist:
            print("✅ 所有實盤交易UI組件都正常工作！")
            print("現在可以嘗試啟動實盤交易功能。")
        else:
            print("❌ 部分UI組件有問題，需要進一步修復。")
        
        # 測試完成，關閉GUI
        print("\n測試完成！")
        root.after(2000, root.quit)  # 2秒後關閉
    
    # 在後台線程中運行測試
    test_thread = threading.Thread(target=test_ui_components, daemon=True)
    test_thread.start()
    
    # 啟動GUI
    root.mainloop()

if __name__ == "__main__":
    test_live_trading_ui()
