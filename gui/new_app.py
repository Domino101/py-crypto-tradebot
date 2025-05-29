# gui/new_app.py
"""
重構後的主應用程序 - 模塊化架構
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.base_ui import BaseUIManager
from gui.backtest_ui import BacktestUI
from gui.live_trading_ui import LiveTradingUI
from gui.trend_analysis_ui import TrendAnalysisUI

class ModularTradingApp:
    """模塊化交易應用程序"""

    def __init__(self):
        # 創建主窗口
        self.root = tk.Tk()

        # 初始化基礎UI管理器
        self.base_manager = BaseUIManager(self.root)

        # 初始化各模式的UI管理器
        self.backtest_ui = BacktestUI(self.base_manager)
        self.live_trading_ui = LiveTradingUI(self.base_manager)
        self.trend_analysis_ui = TrendAnalysisUI(self.base_manager)

        # 註冊UI管理器
        self.base_manager.register_ui_manager("backtest", self.backtest_ui)
        self.base_manager.register_ui_manager("live", self.live_trading_ui)
        self.base_manager.register_ui_manager("trend_analysis", self.trend_analysis_ui)

        # 設置窗口關閉處理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 啟動GUI隊列處理
        self.base_manager.process_gui_queue()

        # 初始化顯示第一個模式
        self.base_manager.on_mode_change()

        print("模塊化交易應用程序初始化完成")

    def on_closing(self):
        """處理窗口關閉事件"""
        print("偵測到視窗關閉請求...")

        # 檢查是否有實盤交易在運行
        if (hasattr(self.live_trading_ui, 'live_trader_instance') and
            self.live_trading_ui.live_trader_instance and
            getattr(self.live_trading_ui.live_trader_instance, 'running', False)):

            if messagebox.askyesno("確認退出", "實盤交易正在運行中。\n您確定要停止交易並退出嗎？"):
                print("正在停止實盤交易...")
                self.live_trading_ui.stop_live_trading()
                print("正在銷毀主視窗...")
                self.root.destroy()
            else:
                print("取消退出。")
                return
        else:
            print("沒有正在運行的實盤交易，直接退出。")
            self.root.destroy()

    def run(self):
        """運行應用程序"""
        print("啟動模塊化交易應用程序...")
        self.root.mainloop()
        print("應用程序已退出。")

def main():
    """主函數"""
    try:
        print("正在啟動模塊化交易應用程序...")
        app = ModularTradingApp()
        app.run()
    except Exception as e:
        print(f"應用程序啟動失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
