# test_new_gui.py
"""
測試新的模塊化GUI
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("正在測試新的模塊化GUI...")

try:
    print("導入基礎UI管理器...")
    from gui.base_ui import BaseUIManager
    print("✅ 基礎UI管理器導入成功")
    
    print("導入回測UI...")
    from gui.backtest_ui import BacktestUI
    print("✅ 回測UI導入成功")
    
    print("導入實盤交易UI...")
    from gui.live_trading_ui import LiveTradingUI
    print("✅ 實盤交易UI導入成功")
    
    print("導入走勢分析UI...")
    from gui.trend_analysis_ui import TrendAnalysisUI
    print("✅ 走勢分析UI導入成功")
    
    print("創建主窗口...")
    root = tk.Tk()
    
    print("初始化基礎UI管理器...")
    base_manager = BaseUIManager(root)
    
    print("初始化各模式UI管理器...")
    backtest_ui = BacktestUI(base_manager)
    live_trading_ui = LiveTradingUI(base_manager)
    trend_analysis_ui = TrendAnalysisUI(base_manager)
    
    print("註冊UI管理器...")
    base_manager.register_ui_manager("backtest", backtest_ui)
    base_manager.register_ui_manager("live", live_trading_ui)
    base_manager.register_ui_manager("trend_analysis", trend_analysis_ui)
    
    print("啟動GUI隊列處理...")
    base_manager.process_gui_queue()
    
    print("初始化顯示...")
    base_manager.on_mode_change()
    
    print("✅ 模塊化GUI初始化完成！")
    print("啟動主循環...")
    
    root.mainloop()
    print("GUI已退出")
    
except Exception as e:
    print(f"❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()
