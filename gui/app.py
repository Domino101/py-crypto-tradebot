# gui/app.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import queue
import pandas as pd
import threading
from datetime import datetime
import os
import importlib
import inspect
import traceback
import sys

# --- Import components from other project modules ---
try:
    from backtest.backtester import BacktestEngine
    from data.binance_utils import fetch_historical_data # Import from utility file
    # Import the strategy loader utility
    from utils.strategy_loader import load_available_strategies
    # Base class for type checking backtest strategies
    from backtesting import Strategy as BacktestingStrategy
    # Import Live Trader components
    from live.trader import LiveTrader
    from strategies.live_rsi_ema import LiveRsiEmaStrategy # Example live strategy
    from analysis.trend_analyzer import TrendAnalyzer
except ImportError as e:
    print(f"模組導入錯誤: {e}")
    raise SystemExit("無法載入必要模組，請檢查依賴項是否安裝完成")

class TradingAppGUI:
    def __init__(self, master):
        self.master = master
        master.title("加密貨幣交易系統 (回測 / 實盤 / 走勢分析)")
        master.geometry("850x800")
        self.strategies_path = './strategies'
        self.data_path = './data'
        self.strategy_classes = {}
        self.current_param_widgets = {}
        self.gui_queue = queue.Queue()
        self.backtest_results = None
        self.backtest_plot_path = None
        self.live_trader_instance = None
        self.mode_var = tk.StringVar(value="backtest")

        # 走勢分析相關變數
        self.trend_analysis_results = None

        # 初始化所有UI組件
        self._setup_main_frames()
        self._setup_ui_elements()
        self._setup_bindings()

        # 設置初始模式
        self.on_mode_change()

        # 設置窗口關閉處理
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 啟動GUI隊列處理
        self.process_gui_queue()

        print("TradingAppGUI 初始化完成。")

    def _setup_main_frames(self):
        """初始化主要框架"""
        # 模式選擇框架
        self.mode_frame = ttk.Frame(self.master)
        self.mode_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky='w')

        # 交易所框架 (實盤模式)
        self.exchange_frame = ttk.LabelFrame(self.master, text="交易所設置")

        # 創建交易所選擇控件
        ttk.Label(self.exchange_frame, text="交易所:").pack(side=tk.LEFT, padx=(5, 5))
        self.exchange_combobox = ttk.Combobox(self.exchange_frame, values=["Alpaca"], state="readonly", width=15)
        self.exchange_combobox.set("Alpaca")  # 默認值
        self.exchange_combobox.pack(side=tk.LEFT, padx=(0, 5))

        # 數據框架 (回測模式)
        self.data_frame = ttk.LabelFrame(self.master, text="數據加載")

        # 實盤參數框架
        self.live_params_frame = ttk.LabelFrame(self.master, text="實盤交易參數")
        self.live_params_frame.columnconfigure(1, weight=1)

        # 創建實盤參數控件
        ttk.Label(self.live_params_frame, text="交易對:").grid(row=0, column=0, padx=5, pady=3, sticky='w')
        self.live_symbol_entry = ttk.Entry(self.live_params_frame, width=15)
        self.live_symbol_entry.grid(row=0, column=1, padx=5, pady=3, sticky='ew')
        self.live_symbol_entry.insert(0, "BTC/USD")  # Alpaca格式

        ttk.Label(self.live_params_frame, text="交易數量:").grid(row=1, column=0, padx=5, pady=3, sticky='w')
        self.live_qty_entry = ttk.Entry(self.live_params_frame, width=15)
        self.live_qty_entry.grid(row=1, column=1, padx=5, pady=3, sticky='ew')
        self.live_qty_entry.insert(0, "0.001")

        ttk.Label(self.live_params_frame, text="時間框架:").grid(row=2, column=0, padx=5, pady=3, sticky='w')
        self.live_interval_combobox = ttk.Combobox(self.live_params_frame, values=['1m', '5m', '15m', '30m', '1h', '4h', '1d'], state="readonly", width=13)
        self.live_interval_combobox.grid(row=2, column=1, padx=5, pady=3, sticky='ew')
        self.live_interval_combobox.set('1h')

        self.paper_trading_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.live_params_frame, text="使用模擬盤", variable=self.paper_trading_var).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # 實盤狀態框架
        self.live_status_frame = ttk.LabelFrame(self.master, text="交易狀態")
        self.live_status_frame.columnconfigure(1, weight=1)

        # 走勢分析框架
        self.trend_analysis_frame = ttk.LabelFrame(self.master, text="走勢分析設置")
        self.trend_analysis_frame.columnconfigure(1, weight=1)

        # 創建狀態顯示控件
        ttk.Label(self.live_status_frame, text="帳戶餘額:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.balance_var = tk.StringVar(value="N/A")
        self.balance_label = ttk.Label(self.live_status_frame, textvariable=self.balance_var, anchor=tk.W)
        self.balance_label.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(self.live_status_frame, text="當前持倉:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.positions_var = tk.StringVar(value="N/A")
        self.positions_label = ttk.Label(self.live_status_frame, textvariable=self.positions_var, anchor=tk.W, wraplength=300)
        self.positions_label.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(self.live_status_frame, text="當前掛單:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.orders_var = tk.StringVar(value="N/A")
        self.orders_label = ttk.Label(self.live_status_frame, textvariable=self.orders_var, anchor=tk.W, wraplength=300)
        self.orders_label.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

        # 參數外部框架
        self.param_outer_frame = ttk.LabelFrame(self.master, text="策略參數")
        self.param_outer_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        # 回測參數框架
        self.backtest_params_frame = ttk.Frame(self.param_outer_frame)

        # 策略參數框架
        self.strategy_params_frame = ttk.Frame(self.param_outer_frame)

        # 結果框架
        self.results_frame = ttk.LabelFrame(self.master, text="結果 / 日誌")
        self.results_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')

        # 按鈕框架
        self.button_frame = ttk.Frame(self.master)
        self.button_frame.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky='ew')

        # 狀態欄
        self.status_var = tk.StringVar(value="準備就緒")
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.status_bar.grid(row=8, column=0, columnspan=2, sticky='ew')

    def _setup_ui_elements(self):
        """初始化UI元素"""
        # 模式選擇
        ttk.Label(self.mode_frame, text="模式:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(self.mode_frame, text="回測", variable=self.mode_var, value="backtest").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.mode_frame, text="實盤交易", variable=self.mode_var, value="live").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.mode_frame, text="走勢分析", variable=self.mode_var, value="trend_analysis").pack(side=tk.LEFT, padx=5)

        # 策略選擇
        ttk.Label(self.master, text="選擇策略:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.strategy_combobox = ttk.Combobox(self.master, state="readonly")
        self.strategy_combobox.grid(row=2, column=1, padx=10, pady=5, sticky='ew')

        # 回測參數
        ttk.Label(self.backtest_params_frame, text="起始本金:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.capital_var = tk.StringVar(value="10000")
        self.capital_entry = ttk.Entry(self.backtest_params_frame, textvariable=self.capital_var, width=10)
        self.capital_entry.grid(row=0, column=1, padx=5, pady=2, sticky='w')

        ttk.Label(self.backtest_params_frame, text="槓桿倍數:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.leverage_var = tk.StringVar(value="1.0")
        self.leverage_entry = ttk.Entry(self.backtest_params_frame, textvariable=self.leverage_var, width=10)
        self.leverage_entry.grid(row=1, column=1, padx=5, pady=2, sticky='w')

        ttk.Label(self.backtest_params_frame, text="進場偏移(%):").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.offset_var = tk.StringVar(value="0.0")
        self.offset_entry = ttk.Entry(self.backtest_params_frame, textvariable=self.offset_var, width=10)
        self.offset_entry.grid(row=2, column=1, padx=5, pady=2, sticky='w')

        # 結果文本框
        self.result_text = tk.Text(self.results_frame, wrap=tk.WORD, height=8)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按鈕
        self.start_button = ttk.Button(self.button_frame, text="開始回測", command=self.start_backtest)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(self.button_frame, text="停止", command=self.stop_live_trading)
        # 停止按鈕在實盤模式下顯示

        self.clear_button = ttk.Button(self.button_frame, text="清除結果", command=self.clear_results)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # 回測結果查看按鈕
        self.view_plot_button = ttk.Button(self.button_frame, text="查看圖表", command=self.view_backtest_plot, state=tk.DISABLED)
        self.view_plot_button.pack(side=tk.LEFT, padx=5)

        self.view_trades_button = ttk.Button(self.button_frame, text="查看交易", command=self.view_trade_records, state=tk.DISABLED)
        self.view_trades_button.pack(side=tk.LEFT, padx=5)

        self.view_order_log_button = ttk.Button(self.button_frame, text="查看訂單日誌", command=self.view_order_log, state=tk.DISABLED)
        self.view_order_log_button.pack(side=tk.LEFT, padx=5)

    def _setup_bindings(self):
        """設置事件綁定"""
        self.mode_var.trace_add("write", lambda *_: self.on_mode_change())
        self.strategy_combobox.bind("<<ComboboxSelected>>", self.on_strategy_selected)

    # --- *** NEW Method: Handle Window Closing *** ---
    def on_closing(self):
        """Handles the event when the user closes the window."""
        print("偵測到視窗關閉請求...")
        if self.live_trader_instance and self.live_trader_instance.running:
            if messagebox.askyesno("確認退出", "實盤交易正在運行中。\n您確定要停止交易並退出嗎？"):
                print("正在停止實盤交易...")
                self.stop_live_trading() # Attempt graceful stop
                # Optional: Add a small delay or check thread status before destroying
                # time.sleep(1) # Simple delay
                print("正在銷毀主視窗...")
                self.master.destroy()
            else:
                print("取消退出。")
                return # Do not close if user cancels
        else:
            print("沒有正在運行的實盤交易，直接退出。")
            self.master.destroy()

    # --- *** NEW Method: Handle Mode Change *** ---
    def on_mode_change(self):
        """Updates the GUI layout and available options based on the selected mode."""
        mode = self.mode_var.get()
        print(f"\n=== 模式切換開始: {mode} ===")
        print(f"當前策略參數框架子組件: {self.strategy_params_frame.winfo_children()}")

        # Clear previous strategy params UI first
        for w in self.strategy_params_frame.winfo_children():
            print(f"移除策略參數組件: {w}")
            w.destroy()

        self.current_param_widgets = {}
        self.strategy_combobox.set('')

        if mode == "backtest":
            print("\n[回測模式] 配置UI...")
            # 隱藏實盤組件
            self.exchange_frame.grid_remove()
            print("隱藏交易所框架")

            # 顯示數據框架
            self.data_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
            print(f"數據框架位置: row=3, column=0")

            # 設置數據框架內容
            self.setup_simplified_data_frame()
            print("已設置數據框架內容")

            self.live_params_frame.grid_remove()
            self.live_status_frame.grid_remove()

            # 參數框架布局
            print("\n配置參數框架:")
            self.backtest_params_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='nw', in_=self.param_outer_frame)
            print(f"回測參數框架pack: side=LEFT, anchor=NW")

            self.strategy_params_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, in_=self.param_outer_frame)
            print(f"策略參數框架pack: side=LEFT, expand=True")

            # 按鈕配置
            self.start_button.config(text="開始回測", state=tk.NORMAL)
            self.stop_button.pack_forget()
            print("顯示開始回測按鈕，隱藏停止按鈕")

        elif mode == "live":
            print("\n[實盤模式] 配置UI...")
            # 交易所框架
            self.exchange_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,5), sticky='w')
            print(f"交易所框架位置: row=1, column=0")

            # 隱藏數據框架
            self.data_frame.grid_remove()
            self.backtest_params_frame.pack_forget()

            # 實盤參數框架
            self.live_params_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
            print(f"實盤參數框架位置: row=3, column=0")

            # 策略參數框架
            self.strategy_params_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, in_=self.param_outer_frame)
            print(f"策略參數框架pack: side=LEFT, expand=True")

            # 狀態框架
            self.live_status_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
            print(f"狀態框架位置: row=5, column=0")

            # 按鈕配置
            self.start_button.config(text="開始實盤", state=tk.NORMAL)
            self.stop_button.pack(side=tk.LEFT, padx=5)
            print("顯示開始實盤和停止按鈕")

        elif mode == "trend_analysis":
            print("\n[走勢分析模式] 配置UI...")
            # 隱藏所有其他組件
            self.exchange_frame.grid_remove()
            self.live_params_frame.grid_remove()
            self.live_status_frame.grid_remove()
            self.backtest_params_frame.pack_forget()
            self.data_frame.grid_remove()  # 隱藏舊的數據框架

            # 只顯示走勢分析框架（N8N工作流UI）
            self.trend_analysis_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='ew')
            print(f"走勢分析框架位置: row=3, column=0")

            # 設置走勢分析框架內容
            self.setup_trend_analysis_frame()
            print("已設置走勢分析框架內容")

            # 隱藏舊的按鈕
            self.start_button.pack_forget()  # 隱藏舊的開始按鈕
            self.stop_button.pack_forget()  # 隱藏停止按鈕
            print("隱藏舊的按鈕，使用N8N工作流按鈕")

        # 後續配置
        print("\n進行後續配置:")
        if mode != "trend_analysis":  # 走勢分析模式不需要載入策略
            self.load_strategies(live_mode=(mode == "live"))
            self.update_strategy_params_ui()

        mode_text = {"backtest": "回測", "live": "實盤交易", "trend_analysis": "走勢分析"}
        self.set_status(f"模式已切換至: {mode_text.get(mode, mode)}")
        print(f"=== 模式切換完成: {mode} ===\n")

        # 強制更新UI
        self.master.update_idletasks()
        print("UI強制更新完成")

    # --- 添加簡化的數據框架設置方法 ---
    def setup_simplified_data_frame(self):
        """設置簡化的數據加載框架"""
        # 清除現有的數據框架內容
        for widget in self.data_frame.winfo_children():
            widget.destroy()

        # 重新配置列權重
        self.data_frame.columnconfigure(0, weight=1)
        self.data_frame.columnconfigure(1, weight=1)

        # 交易對選擇
        ttk.Label(self.data_frame, text="交易對:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.symbol_var = tk.StringVar(value="BTCUSDT")
        self.symbol_entry = ttk.Entry(self.data_frame, textvariable=self.symbol_var)
        self.symbol_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        # 時間框架選擇
        ttk.Label(self.data_frame, text="時間框架:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.interval_var = tk.StringVar(value="1h")
        intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        self.interval_combo = ttk.Combobox(self.data_frame, textvariable=self.interval_var, values=intervals, state="readonly")
        self.interval_combo.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        # 日期選擇
        ttk.Label(self.data_frame, text="開始日期:").grid(row=2, column=0, padx=5, pady=2, sticky='w')

        # 檢查是否已導入 DateEntry
        try:
            from tkcalendar import DateEntry
            self.start_date_picker = DateEntry(self.data_frame, width=12, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
        except ImportError:
            # 如果沒有 tkcalendar，使用簡單的 Entry
            self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
            self.start_date_picker = ttk.Entry(self.data_frame, textvariable=self.start_date_var)

        self.start_date_picker.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(self.data_frame, text="結束日期:").grid(row=3, column=0, padx=5, pady=2, sticky='w')

        try:
            from tkcalendar import DateEntry
            self.end_date_picker = DateEntry(self.data_frame, width=12, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
        except ImportError:
            # 如果沒有 tkcalendar，使用簡單的 Entry
            self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
            self.end_date_picker = ttk.Entry(self.data_frame, textvariable=self.end_date_var)

        self.end_date_picker.grid(row=3, column=1, padx=5, pady=2, sticky='ew')

        # 數據狀態顯示
        ttk.Label(self.data_frame, text="數據狀態:").grid(row=4, column=0, padx=5, pady=2, sticky='w')
        self.data_status_var = tk.StringVar(value="未加載")
        ttk.Label(self.data_frame, textvariable=self.data_status_var).grid(row=4, column=1, padx=5, pady=2, sticky='w')

        # 進度條
        ttk.Label(self.data_frame, text="下載進度:").grid(row=5, column=0, padx=5, pady=2, sticky='w')
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.data_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=1, padx=5, pady=2, sticky='ew')

        # 加載數據按鈕
        self.load_data_btn = ttk.Button(self.data_frame, text="加載數據", command=self.prepare_data)
        self.load_data_btn.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    # --- 修改 prepare_data 方法 ---
    def prepare_data(self):
        """智能準備數據 - 檢查本地數據，必要時下載"""
        # 獲取用戶輸入
        symbol = self.symbol_var.get().strip().upper()
        interval = self.interval_var.get()

        # 獲取日期
        try:
            # 嘗試從 DateEntry 獲取日期
            if hasattr(self.start_date_picker, 'get_date'):
                start_date = self.start_date_picker.get_date()
                end_date = self.end_date_picker.get_date()
            else:
                # 從字符串解析日期
                start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").date()
                end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d").date()
        except Exception as e:
            self.show_message("error", "日期格式錯誤", f"請使用正確的日期格式 (YYYY-MM-DD): {e}")
            return

        # 基本驗證
        if not symbol:
            self.show_message("error", "錯誤", "請輸入交易對符號")
            return

        if start_date > end_date:
            self.show_message("error", "日期錯誤", "開始日期不能晚於結束日期")
            return

        # 設置狀態
        self.set_status(f"正在準備 {symbol} {interval} 數據...")
        self.gui_queue.put(("disable_controls", None))
        self.data_status_var.set("準備中...")
        self.gui_queue.put(("update_progress", 0))  # 重置進度條

        # 創建監控隊列
        monitor_queue = queue.Queue()

        # 創建線程進行數據準備
        prepare_thread = threading.Thread(
            target=self._prepare_data_thread,
            args=(symbol, interval, start_date, end_date, monitor_queue)
        )
        prepare_thread.daemon = True
        prepare_thread.start()

        # 創建監控線程
        monitor_thread = threading.Thread(
            target=self._monitor_data_preparation,
            args=(monitor_queue,)
        )
        monitor_thread.daemon = True
        monitor_thread.start()

    # --- 修改 setup_ui 方法，確保初始化時調用 setup_simplified_data_frame ---
    def setup_ui(self):
        """設置主界面"""
        # ... 現有代碼 ...

        # 在初始化完成後，如果當前模式是回測，設置簡化的數據框架
        if self.mode_var.get() == "backtest":
            self.setup_simplified_data_frame() # Show simplified data loading interface

    def setup_trend_analysis_frame(self):
        """設置走勢分析框架內容 - 完全按照N8N工作流邏輯"""
        # 清除現有內容
        for widget in self.trend_analysis_frame.winfo_children():
            widget.destroy()

        # 標題說明
        title_label = ttk.Label(self.trend_analysis_frame,
                               text="🚀 專業級加密貨幣分析系統 (基於N8N工作流)",
                               font=('Microsoft JhengHei', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, padx=5, pady=10, sticky='w')

        # 說明文字
        desc_label = ttk.Label(self.trend_analysis_frame,
                              text="輸入幣種名稱，系統將自動獲取多時間框架數據並進行專業分析",
                              font=('Microsoft JhengHei', 9), foreground='gray')
        desc_label.grid(row=1, column=0, columnspan=3, padx=5, pady=(0, 15), sticky='w')

        # 幣種輸入 (核心功能)
        symbol_frame = ttk.LabelFrame(self.trend_analysis_frame, text="交易對設置")
        symbol_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky='ew')

        ttk.Label(symbol_frame, text="幣種名稱:").grid(row=0, column=0, padx=10, pady=8, sticky='w')
        self.symbol_entry = ttk.Entry(symbol_frame, width=15, font=('Arial', 11))
        self.symbol_entry.grid(row=0, column=1, padx=5, pady=8, sticky='w')
        self.symbol_entry.insert(0, "BTC")  # 預設值

        ttk.Label(symbol_frame, text="(例: BTC, ETH, ADA)",
                 font=('Arial', 8), foreground='gray').grid(row=0, column=2, padx=5, pady=8, sticky='w')

        # 或者直接輸入完整交易對
        ttk.Label(symbol_frame, text="或完整交易對:").grid(row=1, column=0, padx=10, pady=8, sticky='w')
        self.trading_pair_entry = ttk.Entry(symbol_frame, width=15, font=('Arial', 11))
        self.trading_pair_entry.grid(row=1, column=1, padx=5, pady=8, sticky='w')

        ttk.Label(symbol_frame, text="(例: BTCUSDT, ETHUSDT)",
                 font=('Arial', 8), foreground='gray').grid(row=1, column=2, padx=5, pady=8, sticky='w')

        # API設置 (可選)
        api_frame = ttk.LabelFrame(self.trend_analysis_frame, text="API設置 (可選)")
        api_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky='ew')

        ttk.Label(api_frame, text="Google API 密鑰:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.google_api_key_entry = ttk.Entry(api_frame, width=40, show="*")
        self.google_api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        ttk.Label(api_frame, text="留空使用環境變數，或輸入 'test' 使用測試模式",
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=2, padx=10, pady=2, sticky='w')

        # 分析選項
        options_frame = ttk.LabelFrame(self.trend_analysis_frame, text="分析選項")
        options_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky='ew')

        ttk.Label(options_frame, text="分析詳細程度:").grid(row=0, column=0, padx=10, pady=8, sticky='w')
        self.analysis_detail_var = tk.StringVar(value="標準")
        detail_combobox = ttk.Combobox(options_frame, textvariable=self.analysis_detail_var,
                                     values=["簡要", "標準", "詳細"], state="readonly", width=15)
        detail_combobox.grid(row=0, column=1, padx=5, pady=8, sticky='w')

        # 自動獲取說明
        auto_label = ttk.Label(options_frame,
                              text="✅ 自動獲取 15分鐘、1小時、1天 三個時間框架數據\n✅ 自動分析新聞情緒\n✅ 生成專業交易建議",
                              font=('Arial', 9), foreground='green')
        auto_label.grid(row=1, column=0, columnspan=3, padx=10, pady=8, sticky='w')

        # 分析按鈕
        button_frame = ttk.Frame(self.trend_analysis_frame)
        button_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=15, sticky='ew')

        self.start_analysis_button = ttk.Button(button_frame, text="🚀 開始專業分析",
                                               command=self.start_trend_analysis)
        self.start_analysis_button.pack(side=tk.LEFT, padx=(0, 10))

        # 查看詳細分析按鈕
        self.view_analysis_button = ttk.Button(button_frame, text="📊 查看詳細分析",
                                              command=self.view_last_analysis, state=tk.DISABLED)
        self.view_analysis_button.pack(side=tk.LEFT)

        # 結果顯示區域
        result_frame = ttk.LabelFrame(self.trend_analysis_frame, text="分析結果")
        result_frame.grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky='ew')

        # 創建文本框和滾動條
        text_frame = ttk.Frame(result_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.trend_result_text = tk.Text(text_frame, height=15, wrap=tk.WORD, font=('Microsoft JhengHei', 10))
        self.trend_result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.trend_result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.trend_result_text.config(yscrollcommand=scrollbar.set)

        # 配置列權重
        self.trend_analysis_frame.columnconfigure(1, weight=1)
        symbol_frame.columnconfigure(1, weight=1)
        api_frame.columnconfigure(1, weight=1)

    # --- Helper for ensuring directory and init file ---
    def _ensure_directory_and_init(self, path, name):
        # (Same as previous version)
        ip = os.path.join(path, '__init__.py')
        if not os.path.isdir(path):
            try: os.makedirs(path); print(f"創建 '{path}' ({name})。");
            except OSError as e: messagebox.showerror("錯誤", f"無法創建 {name} 文件夾 '{path}': {e}"); return False
        if os.path.isdir(path) and not os.path.exists(ip):
             try:
                 with open(ip, 'w') as f: f.write(""); print(f"創建空 '{ip}'。") # Ensure empty
             except OSError as e: messagebox.showwarning("文件錯誤", f"無法創建 '{ip}'。"); return False
        elif os.path.exists(ip): # Check if existing is empty
             try:
                 if os.path.getsize(ip) > 0:
                     print(f"警告: '{ip}' 文件不是空的，可能導致問題。正在清空...");
                     with open(ip, 'w') as f: f.write("")
             except Exception as e: print(f"警告: 無法檢查/清空 '{ip}': {e}")
        return True

    # --- GUI 更新與輔助函數 ---
    def process_gui_queue(self):
        """處理GUI更新隊列"""
        try:
            while True:
                action, data = self.gui_queue.get_nowait()

                if action == "disable_controls":
                    self.disable_controls()
                elif action == "enable_controls":
                    self.enable_controls()
                elif action == "update_status":
                    if hasattr(self, 'status_var'):
                        self.status_var.set(data)
                elif action == "update_data_status":
                    self.data_status_var.set(data)
                elif action == "update_progress":
                    if hasattr(self, 'progress_var'):
                        self.progress_var.set(data)
                elif action == "show_error":
                    messagebox.showerror("錯誤", data)
                elif action == "show_info":
                    messagebox.showinfo("信息", data)
                elif action == "messagebox":
                    level, title, message = data
                    if level == "error":
                        messagebox.showerror(title, message)
                    elif level == "warning":
                        messagebox.showwarning(title, message)
                    elif level == "info":
                        messagebox.showinfo(title, message)
                elif action == "result_append":
                    self.result_text.insert(tk.END, data)
                    self.result_text.see(tk.END)
                elif action == "result_clear":
                    self.result_text.delete(1.0, tk.END)
                elif action == "enable_start_button":
                    self.start_button.config(state=tk.NORMAL)
                elif action == "live_trade_started":
                    self.toggle_live_controls(trading=True)
                    # 清除之前的狀態
                    if hasattr(self, 'balance_var'):
                        self.balance_var.set("獲取中...")
                    if hasattr(self, 'positions_var'):
                        self.positions_var.set("獲取中...")
                    if hasattr(self, 'orders_var'):
                        self.orders_var.set("獲取中...")
                elif action == "live_trade_stopped":
                    self.toggle_live_controls(trading=False)
                elif action == "update_live_status":
                    # 期望data是一個字典 {'balance': ..., 'positions': ..., 'orders': ...}
                    if isinstance(data, dict):
                        if hasattr(self, 'balance_var') and 'balance' in data:
                            self.balance_var.set(data['balance'])
                        if hasattr(self, 'positions_var') and 'positions' in data:
                            self.positions_var.set(data['positions'])
                        if hasattr(self, 'orders_var') and 'orders' in data:
                            self.orders_var.set(data['orders'])

                self.gui_queue.task_done()
        except queue.Empty:
            pass
        finally:
            # 每100ms檢查一次隊列
            self.master.after(100, self.process_gui_queue)

    def disable_controls(self):
        """禁用控件"""
        if hasattr(self, 'load_data_btn'):
            self.load_data_btn.configure(state="disabled")
        if hasattr(self, 'start_button'):
            self.start_button.configure(state="disabled")
        if hasattr(self, 'run_button'):
            self.run_button.configure(state="disabled")
        # 禁用其他需要的控件...

    def enable_controls(self):
        """啟用控件 - 使用 toggle_controls 來正確處理所有控件狀態"""
        self.toggle_controls(enabled=True)


    def toggle_controls(self, enabled=True):
        # (Modified to consider mode and live trading state)
        mode = self.mode_var.get()
        st = tk.NORMAL if enabled else tk.DISABLED

        # General controls
        self.clear_button.config(state=st)
        self.strategy_combobox.config(state='readonly' if enabled else tk.DISABLED)
        self.mode_var.set(self.mode_var.get()) # Refresh radio buttons state (might not be needed)

        # Mode-specific controls
        if mode == 'backtest':
            self.start_button.config(state=st)
            # 只配置存在的控件
            if hasattr(self, 'load_data_btn'):
                self.load_data_btn.config(state=st)
            # Enable view buttons only if results exist and contain the relevant data
            st_view_plot = tk.NORMAL if enabled and self.backtest_plot_path else tk.DISABLED
            st_view_trades = tk.NORMAL if enabled and self.backtest_results and 'trades' in self.backtest_results and not self.backtest_results['trades'].empty else tk.DISABLED
            st_view_order_log = tk.NORMAL if enabled and self.backtest_results and '_order_log' in self.backtest_results and self.backtest_results['_order_log'] else tk.DISABLED
            self.view_plot_button.config(state=st_view_plot)
            self.view_trades_button.config(state=st_view_trades)
            self.view_order_log_button.config(state=st_view_order_log)
            # Backtest param entries - 直接配置已知存在的控件
            try:
                self.capital_entry.config(state=st)
                self.leverage_entry.config(state=st)
                self.offset_entry.config(state=st)
            except (AttributeError, tk.TclError):
                pass  # 忽略不存在的控件
            # Hide live controls
            if hasattr(self, 'stop_button'):
                self.stop_button.config(state=tk.DISABLED)


        elif mode == 'live':
            # Live trading controls are handled by toggle_live_controls
            self.toggle_live_controls(trading=(self.live_trader_instance is not None and self.live_trader_instance.running))
            # Disable backtest-specific view buttons
            self.view_plot_button.config(state=tk.DISABLED)
            self.view_trades_button.config(state=tk.DISABLED) # Or adapt later
            self.view_order_log_button.config(state=tk.DISABLED) # Or adapt later

        elif mode == 'trend_analysis':
            # 走勢分析模式控件 - 使用新的N8N工作流按鈕
            if hasattr(self, 'start_analysis_button'):
                self.start_analysis_button.config(state=st)
            # 禁用回測和實盤相關的按鈕
            self.view_plot_button.config(state=tk.DISABLED)
            self.view_trades_button.config(state=tk.DISABLED)
            self.view_order_log_button.config(state=tk.DISABLED)
            if hasattr(self, 'stop_button'):
                self.stop_button.config(state=tk.DISABLED)
            # 隱藏數據載入控件（N8N工作流不需要）
            if hasattr(self, 'load_data_btn'):
                self.load_data_btn.config(state=tk.DISABLED)
            # 查看詳細分析按鈕 - 只有在有分析結果時才啟用
            if hasattr(self, 'view_analysis_button'):
                analysis_available = enabled and hasattr(self, 'trend_analysis_results') and self.trend_analysis_results is not None
                self.view_analysis_button.config(state=tk.NORMAL if analysis_available else tk.DISABLED)


        # Toggle dynamic strategy param widgets
        for widget_tuple in self.current_param_widgets.values():
             widget = widget_tuple[0]
             if widget and widget.winfo_exists(): # Check if widget exists
                 if isinstance(widget, ttk.Combobox): widget.config(state='readonly' if enabled else tk.DISABLED)
                 else: widget.config(state=st)

    def toggle_live_controls(self, trading: bool):
        """Enable/disable controls specifically for live trading state."""
        if self.mode_var.get() != 'live': return # Only applies in live mode

        start_st = tk.DISABLED if trading else tk.NORMAL
        stop_st = tk.NORMAL if trading else tk.DISABLED
        param_st = tk.DISABLED if trading else tk.NORMAL # Disable params while trading

        self.start_button.config(state=start_st)
        self.stop_button.config(state=stop_st)
        self.strategy_combobox.config(state='readonly' if not trading else tk.DISABLED)

        # 只配置存在的實盤控件
        try:
            if hasattr(self, 'exchange_combobox'):
                self.exchange_combobox.config(state='readonly' if not trading else tk.DISABLED)
            if hasattr(self, 'live_symbol_entry'):
                self.live_symbol_entry.config(state=param_st)
            if hasattr(self, 'live_qty_entry'):
                self.live_qty_entry.config(state=param_st)
            # Paper trading checkbox - 安全地檢查
            if hasattr(self, 'live_params_frame') and self.live_params_frame.winfo_children():
                cb = self.live_params_frame.winfo_children()[-1]
                if isinstance(cb, ttk.Checkbutton):
                    cb.config(state=param_st)
        except (AttributeError, tk.TclError):
            pass  # 忽略不存在的控件

        # Strategy params
        for widget_tuple in self.current_param_widgets.values():
             widget = widget_tuple[0]
             if widget and widget.winfo_exists():
                 if isinstance(widget, ttk.Combobox): widget.config(state='readonly' if not trading else tk.DISABLED)
                 else: widget.config(state=param_st)


    def set_status(self, m): self.gui_queue.put(("update_status", m))
    def show_message(self, l, t, m): self.gui_queue.put(("messagebox", (l, t, m)))
    def append_result(self, t): self.gui_queue.put(("result_append", t + "\n")) # Add newline for log clarity
    def clear_results(self):
        self.gui_queue.put(("result_clear", None))
        self.backtest_results = None # Clear stored results
        self.backtest_plot_path = None # Clear plot path
        if self.mode_var.get() == 'backtest':
            self.view_plot_button.config(state=tk.DISABLED) # Disable view buttons
            self.view_trades_button.config(state=tk.DISABLED)
            self.view_order_log_button.config(state=tk.DISABLED)
        self.set_status("日誌已清除")

    # --- 數據處理相關 (Unmodified Backtest Logic) ---
    def toggle_data_source(self):
        if self.data_source_var.get()=="existing": self.new_data_frame.grid_remove(); self.existing_data_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        else: self.existing_data_frame.grid_remove(); self.new_data_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    def load_existing_data_files(self):
        print(">>> load_existing_data_files")
        try:
            if not os.path.exists(self.data_path): self.show_message("warning","數據缺失",f"'{self.data_path}'不存在"); self.existing_data_combobox['values']=[]; self.existing_data_combobox.set(''); return
            dfiles = sorted([f for f in os.listdir(self.data_path) if f.endswith('.csv')]); self.existing_data_combobox['values']=dfiles; self.existing_data_combobox.current(0) if dfiles else self.existing_data_combobox.set(''); self.set_status(f"找到 {len(dfiles)} 個文件")
        except Exception as e: self.show_message("error","錯誤",f"加載數據列表出錯: {e}"); self.existing_data_combobox['values']=[]; self.existing_data_combobox.set('')
        print("<<< load_existing_data_files")

    def _prepare_data_thread(self, symbol, interval, start_date, end_date, monitor_queue):
        """數據準備線程 - 檢查本地數據並下載缺失部分"""
        try:
            # 轉換日期為datetime對象
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            # 檢查是否有現有數據文件
            data_dir = os.path.join("data", "historical")
            os.makedirs(data_dir, exist_ok=True)
            data_file = os.path.join(data_dir, f"{symbol}_{interval}.csv")

            if os.path.exists(data_file):
                # 加載現有數據
                existing_data = pd.read_csv(data_file, index_col=0, parse_dates=True)

                # 檢查是否需要下載額外數據
                need_download = False
                if len(existing_data) > 0:
                    existing_start = existing_data.index[0]
                    existing_end = existing_data.index[-1]

                    if start_dt < existing_start or end_dt > existing_end:
                        need_download = True
                        self.gui_queue.put(("update_status", f"現有數據範圍不足，需要下載完整數據"))
                else:
                    need_download = True
                    self.gui_queue.put(("update_status", f"現有數據為空，需要下載完整數據"))
            else:
                need_download = True
                self.gui_queue.put(("update_status", f"未找到現有數據文件，需要下載"))

            # 如果需要，下載完整數據
            if need_download:
                from data.binance_utils import fetch_historical_data

                self.gui_queue.put(("update_status", f"下載 {symbol} {interval} 數據: {start_dt.date()} 至 {end_dt.date()}"))

                # 轉換為毫秒時間戳
                start_timestamp = int(start_dt.timestamp() * 1000)
                end_timestamp = int(end_dt.timestamp() * 1000)

                # 下載數據
                data = fetch_historical_data(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    output_path=data_file,
                    monitor_queue=monitor_queue
                )
            else:
                # 使用現有數據
                data = existing_data
                # 過濾日期範圍
                data = data[(data.index >= start_dt) & (data.index <= end_dt)]

            # 保存當前數據以供回測使用
            if data is not None and len(data) > 0:
                # 標準化列名（確保策略能正確識別）
                column_mapping = {
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }
                data = data.rename(columns=column_mapping)

                # 確保必要的列存在
                required_columns = ['Open', 'High', 'Low', 'Close']
                missing_columns = [col for col in required_columns if col not in data.columns]
                if missing_columns:
                    self.gui_queue.put(("show_error", f"數據缺少必要列: {', '.join(missing_columns)}"))
                    return

                self.current_data = data
                self.current_data_info = {
                    'symbol': symbol,
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'rows': len(data)
                }
            else:
                self.gui_queue.put(("show_error", "數據下載失敗或數據為空"))
                return

            # 更新GUI
            self.gui_queue.put(("enable_controls", None))
            self.gui_queue.put(("update_data_status", f"已加載: {symbol} {interval}, {len(data)} 行"))
            self.gui_queue.put(("update_progress", 100))  # 設置進度條為100%
            self.set_status(f"已準備 {symbol} {interval} 數據，共 {len(data)} 行")

            # 數據準備完成

        except Exception as e:
            self.gui_queue.put(("show_error", f"準備數據時出錯: {e}"))
            self.gui_queue.put(("enable_controls", None))
            self.gui_queue.put(("update_data_status", "準備失敗"))
            self.gui_queue.put(("update_progress", 0))  # 重置進度條
            self.set_status("數據準備失敗")
            traceback.print_exc()

    def _monitor_data_preparation(self, monitor_queue):
        """監控數據準備進度"""
        while True:
            try:
                update = monitor_queue.get(timeout=0.5)
                # 處理不同類型的更新消息
                if isinstance(update, dict):
                    status = update.get('status', '')
                    progress = update.get('progress', 0)

                    # 更新狀態文字
                    if progress >= 0:
                        self.gui_queue.put(("update_status", f"{status} ({progress}%)"))
                        # 更新進度條
                        self.gui_queue.put(("update_progress", progress))
                    else:
                        self.gui_queue.put(("update_status", status))
                        # 重置進度條
                        self.gui_queue.put(("update_progress", 0))

                elif isinstance(update, str):
                    # 處理字符串消息
                    self.gui_queue.put(("update_status", update))

                monitor_queue.task_done()
            except queue.Empty:
                # 檢查是否應該退出
                if not any(t.name.startswith("Thread-") and t.is_alive() for t in threading.enumerate()):
                    break
                continue
            except Exception as e:
                print(f"監控線程錯誤: {e}")
                break

    # --- *** MODIFIED: load_strategies accepts mode *** ---
    def load_strategies(self, live_mode=False):
        """Load strategies using the utility function based on mode."""
        print(f">>> load_strategies (Live Mode: {live_mode})")
        # TODO: Enhance load_available_strategies or filtering logic
        #       to better distinguish live vs backtest strategies.
        #       Using simple checks for now.

        all_strategies = load_available_strategies(self.strategies_path)
        self.strategy_classes = {} # Reset

        # Load all strategies without filtering
        self.strategy_classes = all_strategies
        strategy_display_names = sorted(self.strategy_classes.keys())
        print(f"Loaded all strategies: {strategy_display_names}")

        if not strategy_display_names:
            self.show_message("warning", "無策略", f"在 '{self.strategies_path}' 中未找到任何策略。")

        self.strategy_combobox['values'] = strategy_display_names
        if strategy_display_names:
            self.strategy_combobox.current(0)
        else:
            self.strategy_combobox.set('')
        print("<<< load_strategies")

    # --- Dynamic Parameter UI Update ---
    def on_strategy_selected(self, event=None):
        print(f"策略選擇: {self.strategy_combobox.get()}")
        self.update_strategy_params_ui()

    def update_strategy_params_ui(self):
        # (Modified to handle potential lack of _params_def in live strategies)
        if not hasattr(self, 'strategy_params_frame') or not self.strategy_params_frame.winfo_exists(): return
        for w in self.strategy_params_frame.winfo_children(): w.destroy()
        self.current_param_widgets={}
        strategy_name = self.strategy_combobox.get()
        if not strategy_name:
            ttk.Label(self.strategy_params_frame, text="請選擇策略").grid(row=0, column=0); return

        strategy_class = self.strategy_classes.get(strategy_name)
        if not strategy_class:
            ttk.Label(self.strategy_params_frame, text="錯誤：找不到策略類別").grid(row=0, column=0); return

        # --- Get parameters definition (Unified approach) ---
        # Always expect _params_def attribute from the strategy class
        params_def = getattr(strategy_class, '_params_def', None)

        if not params_def or not isinstance(params_def, dict):
            # Display message if strategy doesn't define parameters correctly
            ttk.Label(self.strategy_params_frame, text=f"策略 '{strategy_name}'\n未定義參數 (_params_def)").grid(row=0, column=0)
            return

        print(f"更新參數 UI for: {strategy_name} using _params_def"); r=0
        for param_key, definition in params_def.items():
            try:
                # Handle both tuple format and potentially inferred dict format
                if isinstance(definition, tuple) and len(definition) == 4:
                    label_text, param_type, default_value, options_or_range = definition
                elif isinstance(definition, dict): # Handle inferred format if needed
                     label_text = definition.get('label', param_key.title())
                     param_type = definition.get('type', str)
                     default_value = definition.get('default', '')
                     options_or_range = definition.get('options') # Or 'range'
                else: continue # Skip invalid definitions
            except Exception as e:
                print(f"ERR 解析參數 '{param_key}': {e}")
                continue # Skip this parameter if definition is invalid

            lbl = ttk.Label(self.strategy_params_frame, text=f"{label_text}:")
            lbl.grid(row=r, column=0, padx=5, pady=3, sticky='w')
            widget = None
            current_value = str(default_value) # Use default value from definition

            # Create widget based on type and options/range
            if isinstance(options_or_range, list) and param_type is str:
                widget = ttk.Combobox(self.strategy_params_frame, values=options_or_range, state='readonly', width=10)
                if default_value in options_or_range:
                    widget.set(default_value)
                elif options_or_range:
                    widget.current(0)
            else: # Default to Entry widget
                widget = ttk.Entry(self.strategy_params_frame, width=12)
                widget.insert(0, current_value) # Always insert the default value

            if widget:
                widget.grid(row=r, column=1, padx=5, pady=3, sticky='ew')
                # Store widget, type, options/range for later validation
                self.current_param_widgets[param_key] = (widget, param_type, options_or_range, label_text) # Store label too
            r += 1

    # --- *** NEW: Unified Strategy Parameter Validation *** ---
    def _get_validated_strategy_params(self) -> dict:
        """
        Reads strategy parameters from the GUI, validates them based on _params_def,
        and returns a dictionary of validated parameters.

        Raises:
            ValueError: If any parameter fails validation.
            RuntimeError: If there's an issue accessing widgets or definitions.
        """
        strategy_params = {}
        print("讀取並驗證策略參數:")
        if not self.current_param_widgets:
             print("  未找到策略參數控件。")
             return {} # Return empty dict if no params defined/displayed

        for param_key, widget_info in self.current_param_widgets.items():
            try:
                widget, param_type, options_or_range, label_text = widget_info
                value_str = ""
                if isinstance(widget, (ttk.Entry, ttk.Combobox)):
                    value_str = widget.get()
                else:
                     # Should not happen if UI is built correctly
                     print(f"警告: 參數 '{param_key}' 的控件類型未知: {type(widget)}")
                     continue

                print(f"  '{param_key}' ({label_text}): Raw='{value_str}'")
                value = None

                # --- Validation and Type Conversion ---
                if not value_str and param_type is not str:
                    # Generally, non-string parameters cannot be empty unless explicitly allowed
                    # For now, assume required if not string and empty
                    raise ValueError(f"'{label_text}' ({param_key}) 不能為空")

                if param_type is int:
                    try:
                        value = int(value_str)
                    except ValueError:
                        raise ValueError(f"'{label_text}' ({param_key}) 需為整數")
                    # Range validation
                    if isinstance(options_or_range, tuple) and len(options_or_range) == 2:
                        if not (options_or_range[0] <= value <= options_or_range[1]):
                            raise ValueError(f"'{label_text}' ({param_key}) 需介於 {options_or_range[0]} - {options_or_range[1]}")
                    # Implicit validation (e.g., length > 0)
                    elif value <= 0 and ('length' in param_key.lower() or 'period' in param_key.lower() or 'window' in param_key.lower()):
                         raise ValueError(f"'{label_text}' ({param_key}) 需為正整數")

                elif param_type is float:
                    try:
                        value = float(value_str)
                    except ValueError:
                        raise ValueError(f"'{label_text}' ({param_key}) 需為數字")
                    # Range validation
                    if isinstance(options_or_range, tuple) and len(options_or_range) == 2:
                        if not (options_or_range[0] <= value <= options_or_range[1]):
                            raise ValueError(f"'{label_text}' ({param_key}) 需介於 {options_or_range[0]} - {options_or_range[1]}")
                    # Implicit validation (e.g., multiplier > 0)
                    elif value <= 0 and ('multiplier' in param_key.lower() or 'factor' in param_key.lower() or 'frac' in param_key.lower()):
                         raise ValueError(f"'{label_text}' ({param_key}) 需為正數")

                elif param_type is str:
                    # Options validation
                    if isinstance(options_or_range, list) and value_str not in options_or_range:
                        raise ValueError(f"'{label_text}' ({param_key}) 的值 '{value_str}' 無效，請從列表中選擇: {options_or_range}")
                    value = value_str # Assign the string value

                elif param_type is bool:
                     # More robust boolean check
                     if value_str.strip().lower() in ['true', '1', 'yes', 'y', 't']: value = True
                     elif value_str.strip().lower() in ['false', '0', 'no', 'n', 'f']: value = False
                     else: raise ValueError(f"'{label_text}' ({param_key}) 需為布爾值 (True/False, 1/0, Yes/No)")

                else:
                    # Fallback for other types - attempt direct conversion if type is known
                    if callable(param_type):
                         try: value = param_type(value_str)
                         except Exception as conv_err: raise ValueError(f"'{label_text}' ({param_key}) 無法轉換為類型 {param_type.__name__}: {conv_err}")
                    else:
                         print(f"警告: 參數 '{label_text}' ({param_key}) 的類型 {param_type} 未知或無法處理，將使用原始字符串。")
                         value = value_str # Use raw string as fallback

                # Store the validated and converted value
                strategy_params[param_key] = value
                print(f"    '{param_key}': {value} (Type: {param_type})")

            except ValueError as ve:
                # Re-raise validation errors to be caught by the caller
                raise ve
            except Exception as e:
                # Catch unexpected errors during widget access or processing
                traceback.print_exc()
                raise RuntimeError(f"讀取/驗證參數 '{param_key}' ({label_text}) 時發生錯誤: {e}")

        print("策略參數驗證完成。")
        return strategy_params

    # --- Backtest Execution Methods ---
    def start_backtest(self):
        """統一的啟動方法，根據模式調用相應的方法"""
        mode = self.mode_var.get()
        if mode == "backtest":
            self.run_backtest()
        elif mode == "live":
            self.start_live_trading()
        elif mode == "trend_analysis":
            self.start_trend_analysis()
        else:
            self.show_message("error", "模式錯誤", f"未知的模式: {mode}")

    def run_backtest(self):
        """執行回測"""
        # 檢查是否已加載數據
        if not hasattr(self, 'current_data') or self.current_data is None or self.current_data.empty:
            self.show_message("warning", "數據未準備", "請先加載數據")
            return

        # 獲取策略選擇
        sn = self.strategy_combobox.get()
        if not sn:
            self.show_message("warning", "選擇錯誤", "請選擇策略")
            return

        # 獲取策略類
        sc = self.strategy_classes.get(sn)
        if sc is None:
            self.show_message("error", "策略錯誤", f"找不到策略類: {sn}")
            return

        # 獲取回測參數
        try:
            cap = float(self.capital_var.get())
            lev = float(self.leverage_var.get())
            offset_percent = float(self.offset_var.get())
        except ValueError as e:
            self.show_message("error", "參數錯誤", f"無效的數值參數: {e}")
            return

        # 獲取策略參數
        try:
            sp = self._get_validated_strategy_params()
        except (ValueError, RuntimeError) as e:
            self.show_message("warning", "策略參數錯誤", f"檢查策略參數:\n{e}")
            return
        except Exception as e:
            self.show_message("error", "參數讀取錯誤", f"讀取策略參數時發生未知錯誤:\n{e}")
            traceback.print_exc()
            return

        # 開始回測
        self.gui_queue.put(("disable_controls", None))
        self.clear_results()
        self.append_result(f"開始回測: {sn}\n數據: {self.current_data_info['symbol']} {self.current_data_info['interval']}, {self.current_data_info['rows']} 行\n")
        self.append_result(f"回測參數: 本金={cap:,.2f}, 槓桿={lev:.2f}x, 進場偏移={offset_percent:.2f}%\n")
        param_str = ", ".join(f"{k}={v}" for k, v in sp.items()) if sp else "無"
        self.append_result(f"策略參數: {param_str}\n")
        self.append_result("-" * 30)
        self.set_status(f"回測 {sn}...")

        # 啟動回測線程
        threading.Thread(
            target=self._run_backtest_thread,
            args=(self.current_data, sc, sp, cap, lev, offset_percent),
            daemon=True
        ).start()

    def _run_backtest_thread(self, data, strategy_class, strategy_params, capital, leverage, offset_percent):
        """回測執行線程"""
        try:
            self.set_status("初始化回測引擎...")
            engine = BacktestEngine(
                data=data,
                strategy_class=strategy_class,
                strategy_params=strategy_params,
                initial_capital=capital,
                leverage=leverage,
                offset_value=offset_percent
            )

            self.set_status("執行回測...")
            engine.run()

            self.set_status("生成回測報告...")
            results = engine.get_analysis_results()
            self.backtest_results = results

            # 顯示結果摘要
            pm = results.get('performance_metrics', {})
            def get_m(k, f="{:.2f}"):
                v = pm.get(k)
                return 'N/A' if v is None or (isinstance(v, float) and pd.isna(v)) else (f.format(v) if isinstance(v, (int, float)) and f else str(v))

            self.append_result("--- 回測結果摘要 ---")
            self.append_result(f"  時間範圍: {get_m('Start','{}')} - {get_m('End','{}')} ({get_m('Duration','{}')})")
            self.append_result(f"  總回報: {get_m('Return [%]')}%")
            self.append_result(f"  年化回報: {get_m('Return (Ann.) [%]')}%")
            self.append_result(f"  夏普比率: {get_m('Sharpe Ratio')}")
            self.append_result(f"  最大回撤: {get_m('Max. Drawdown [%]')}%")
            self.append_result(f"  勝率: {get_m('Win Rate [%]')}%")
            self.append_result(f"  交易次數: {get_m('# Trades', '{:.0f}')}")

            # 生成圖表
            base_strategy_name = getattr(strategy_class, '__name__', 'UnknownStrategy')
            plot_filename = f"plots/{base_strategy_name}_{datetime.now():%Y%m%d_%H%M%S}.html"
            plot_path = engine.generate_plot(filename=plot_filename)

            if plot_path:
                self.backtest_plot_path = plot_path
                self.append_result(f"圖表已保存至: {os.path.basename(plot_path)}")
                self.set_status("回測完成 (含圖表)")
            else:
                self.append_result("\n錯誤：生成回測圖表失敗。")
                self.set_status("回測完成 (圖表生成失敗)")

        except Exception as e:
            self.show_message("error", "回測錯誤", str(e))
            self.set_status("回測失敗")
            self.append_result(f"\n錯誤: {e}")
            traceback.print_exc()
            self.backtest_results = {'_order_log': engine.order_log if 'engine' in locals() else []}
            self.backtest_plot_path = None
        finally:
            self.gui_queue.put(("enable_controls", None))


    # --- *** NEW Methods for Live Trading *** ---
    def start_live_trading(self):
        """Starts the live trading process."""
        self.clear_results() # Clear log area
        self.append_result("--- 開始實盤交易 ---")
        self.set_status("正在初始化實盤交易...")
        # --- Disable start button immediately ---
        self.start_button.config(state=tk.DISABLED)
        # Also disable other relevant controls synchronously if needed
        self.toggle_live_controls(trading=True) # Use existing toggle logic
        self.master.update_idletasks() # Ensure UI updates immediately

        try:
            # --- Get Live Parameters ---
            exchange = self.exchange_combobox.get()
            symbol = self.live_symbol_entry.get()
            paper_mode = self.paper_trading_var.get()
            try:
                quantity = float(self.live_qty_entry.get())
                if quantity <= 0: raise ValueError("交易數量必須 > 0")
            except ValueError:
                raise ValueError("交易數量必須是有效的數字")

            strategy_name = self.strategy_combobox.get()
            if not strategy_name: raise ValueError("請選擇交易策略")
            strategy_class = self.strategy_classes.get(strategy_name)
            if not strategy_class: raise ValueError(f"找不到策略類別: {strategy_name}")

            # --- Get Strategy Parameters using helper ---
            try:
                strategy_params = self._get_validated_strategy_params()
            except (ValueError, RuntimeError) as e:
                self.show_message("warning", "策略參數錯誤", f"檢查策略參數:\n{e}")
                self.gui_queue.put(("enable_controls", None)) # Re-enable on error
                return
            except Exception as e:
                self.show_message("error", "參數讀取錯誤", f"讀取策略參數時發生未知錯誤:\n{e}")
                traceback.print_exc()
                self.gui_queue.put(("enable_controls", None)) # Re-enable on error
                return

            # --- Get Live Timeframe ---
            live_interval = self.live_interval_combobox.get()
            if not live_interval:
                # This check might be redundant if timeframe becomes a strategy param
                raise ValueError("請選擇實盤交易的時間框架")

            # --- Log parameters ---
            self.append_result(f"交易所: {exchange}")
            self.append_result(f"模式: {'模擬盤' if paper_mode else '實盤'}")
            self.append_result(f"交易對: {symbol}")
            self.append_result(f"時間框架: {live_interval}") # Log timeframe
            self.append_result(f"交易數量: {quantity}")
            self.append_result(f"策略: {strategy_name}")
            param_str = ", ".join(f"{k}={v}" for k, v in (strategy_params or {}).items()) if strategy_params else "無參數"
            self.append_result(f"策略參數: {param_str}")
            self.append_result("-" * 30)

            # --- Initialize and Start LiveTrader ---
            # TODO: Pass the gui_queue to LiveTrader if implemented for logging
            self.live_trader_instance = LiveTrader(
                strategy_class=strategy_class,
                strategy_params=strategy_params,
                symbol=symbol,
                interval=live_interval, # Pass interval to LiveTrader
                trade_quantity=quantity,
                paper_trading=paper_mode,
                gui_queue=self.gui_queue # Pass queue for status updates
                # slippage_tolerance=... # Add if needed
            )
            # Start trader thread
            self.live_trader_thread = threading.Thread(target=self.live_trader_instance.start, daemon=True)
            self.live_trader_thread.start()
            self.set_status(f"實盤交易運行中 ({symbol})...")
            # Note: toggle_live_controls(trading=True) already called above
            # self.gui_queue.put(("live_trade_started", None)) # Queue message might still be useful for other async updates

        except (ValueError, RuntimeError, ConnectionError) as e:
            self.show_message("error", "啟動實盤交易失敗", str(e))
            self.set_status("實盤交易啟動失敗")
            # --- Re-enable controls on failure ---
            self.toggle_live_controls(trading=False) # Use toggle logic
            self.live_trader_instance = None
        except Exception as e:
            error_details = traceback.format_exc()
            self.show_message("error", "未知錯誤", f"啟動實盤交易時發生未預期錯誤: {e}")
            self.set_status("實盤交易啟動異常")
            self.append_result(f"錯誤: {e}\n{error_details}")
            print(f"--- 未知實盤啟動錯誤 ---\n{error_details}")
            # --- Re-enable controls on failure ---
            self.toggle_live_controls(trading=False) # Use toggle logic
            self.live_trader_instance = None


    def stop_live_trading(self):
        """Stops the currently running live trader instance."""
        self.append_result("--- 停止實盤交易 ---")
        self.set_status("正在停止實盤交易...")
        if self.live_trader_instance:
            try:
                # Request stop via the instance method
                self.live_trader_instance.stop()
                # Wait for the trader thread to finish (with a timeout)
                if hasattr(self, 'live_trader_thread') and self.live_trader_thread.is_alive():
                     print("等待實盤交易線程結束...")
                     self.live_trader_thread.join(timeout=10) # Wait up to 10 seconds
                     if self.live_trader_thread.is_alive():
                         print("警告: 實盤交易線程未在超時內結束。")
                         self.append_result("警告: 停止交易可能未完全完成。")
                     else:
                         print("實盤交易線程已結束。")
                         self.append_result("實盤交易已成功停止。")
                         self.set_status("實盤交易已停止")
                else:
                     self.append_result("實盤交易線程未運行或已結束。")
                     self.set_status("實盤交易已停止")
            except Exception as e:
                traceback.print_exc()
                self.show_message("error", "停止交易出錯", f"停止實盤交易時出錯: {e}")
                self.set_status("停止實盤交易時出錯")
                self.append_result(f"錯誤: 停止交易失敗 - {e}")
            finally:
                self.live_trader_instance = None
                # --- Ensure controls are updated after stopping ---
                self.toggle_live_controls(trading=False)
                # self.gui_queue.put(("live_trade_stopped", None)) # Queue message might be redundant now
        else:
            self.append_result("沒有正在運行的實盤交易實例。")
            self.set_status("無實盤交易正在運行")
            # --- Ensure controls are correct even if no instance existed ---
            self.toggle_live_controls(trading=False)


    # --- *** METHODS for Viewing Results (Backtest Only for now) *** ---
    def view_backtest_plot(self):
        """Opens the generated backtest plot HTML file in the default web browser."""
        if self.mode_var.get() != 'backtest':
             self.show_message("info", "功能限制", "查看圖表功能僅在回測模式下可用。")
             return
        if not self.backtest_plot_path or not os.path.exists(self.backtest_plot_path):
            self.show_message("warning", "無圖表文件", "未找到回測圖表文件。\n請先成功執行回測。")
            return
        try:
            import webbrowser
            webbrowser.open('file://' + os.path.abspath(self.backtest_plot_path))
            self.set_status(f"已在瀏覽器中打開圖表: {os.path.basename(self.backtest_plot_path)}")
        except Exception as e:
            self.show_message("error", "打開圖表失敗", f"無法打開圖表文件:\n{e}")
            self.set_status("打開圖表失敗")

    def view_trade_records(self):
        """Displays the trade records from the last backtest in a new window."""
        if self.mode_var.get() != 'backtest':
             self.show_message("info", "功能限制", "查看交易記錄功能僅在回測模式下可用。")
             return
        if not self.backtest_results:
            self.show_message("warning", "無交易記錄", "請先成功執行回測。")
            return
        trades_df = self.backtest_results.get('trades')
        if trades_df is None or not isinstance(trades_df, pd.DataFrame) or trades_df.empty:
            self.show_message("info", "無交易記錄", "本次回測沒有產生任何交易記錄。")
            return
        # (Rest of the display logic is unchanged)
        trade_window = tk.Toplevel(self.master); trade_window.title("交易記錄 (已完成交易)"); trade_window.geometry("900x400")
        tree_frame = ttk.Frame(trade_window); tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical"); vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal"); hsb.pack(side=tk.BOTTOM, fill=tk.X)
        trade_tree = ttk.Treeview(tree_frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set, show='headings'); trade_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=trade_tree.yview); hsb.config(command=trade_tree.xview)
        trade_tree["columns"] = list(trades_df.columns)
        for col in trades_df.columns: trade_tree.heading(col, text=col); col_width = max(len(col) * 10, 80); trade_tree.column(col, width=col_width, anchor=tk.W, stretch=tk.NO)
        for index, row in trades_df.iterrows():
            formatted_row = []
            for item in row:
                if isinstance(item, float): formatted_row.append(f"{item:,.4f}")
                elif isinstance(item, pd.Timestamp): formatted_row.append(item.strftime('%Y-%m-%d %H:%M:%S'))
                else: formatted_row.append(str(item))
            trade_tree.insert("", tk.END, values=formatted_row)
        self.set_status("已顯示交易記錄窗口")

    def view_order_log(self):
        """Displays the detailed order log from the last backtest in a new window."""
        if self.mode_var.get() != 'backtest':
             self.show_message("info", "功能限制", "查看訂單日誌功能僅在回測模式下可用。")
             return
        if not self.backtest_results or '_order_log' not in self.backtest_results:
            self.show_message("warning", "無訂單日誌", "請先成功執行回測。\n(未找到 '_order_log')")
            return
        order_log = self.backtest_results.get('_order_log')
        if not order_log or not isinstance(order_log, list):
            self.show_message("info", "無訂單日誌", "本次回測沒有產生任何訂單日誌記錄。")
            return
        # (Rest of the display logic is unchanged)
        log_window = tk.Toplevel(self.master); log_window.title("訂單操作日誌"); log_window.geometry("950x550")
        stats_frame = ttk.Frame(log_window); stats_frame.pack(fill=tk.X, padx=10, pady=10)
        trades_df = self.backtest_results.get('trades', pd.DataFrame())
        if not trades_df.empty and 'Size' in trades_df.columns and 'ReturnPct' in trades_df.columns:
            long_trades = trades_df[trades_df['Size'] > 0]; long_total = len(long_trades); long_profit = len(long_trades[long_trades['ReturnPct'] > 0]); long_win_rate = (long_profit / long_total * 100) if long_total > 0 else 0
            short_trades = trades_df[trades_df['Size'] < 0]; short_total = len(short_trades); short_profit = len(short_trades[short_trades['ReturnPct'] > 0]); short_win_rate = (short_profit / short_total * 100) if short_total > 0 else 0
            stats_text = (f"多單: {long_total} 張 (盈利 {long_profit} 張, 勝率 {long_win_rate:.1f}%) | 空單: {short_total} 張 (盈利 {short_profit} 張, 勝率 {short_win_rate:.1f}%)")
            ttk.Label(stats_frame, text=stats_text, font=('Arial', 10, 'bold')).pack()
        else: ttk.Label(stats_frame, text="無交易記錄", font=('Arial', 10)).pack()
        tree_frame = ttk.Frame(log_window); tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical"); vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal"); hsb.pack(side=tk.BOTTOM, fill=tk.X)
        log_tree = ttk.Treeview(tree_frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set, show='headings'); log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=log_tree.yview); hsb.config(command=log_tree.xview)
        if order_log:
            all_keys = set(); [all_keys.update(entry.keys()) for entry in order_log if isinstance(entry, dict)]
            preferred_order = ['Timestamp', 'Event', 'Size', 'Limit', 'CalculatedLimit (Buy Offset)', 'CalculatedLimit (Sell Offset)', 'OriginalSignalPrice', 'Stop', 'SL', 'TP', 'Portion', 'Tag']
            sorted_columns = [key for key in preferred_order if key in all_keys] + sorted([key for key in all_keys if key not in preferred_order])
        else: sorted_columns = []
        log_tree["columns"] = sorted_columns
        for col in sorted_columns: log_tree.heading(col, text=col); col_width = max(len(col) * 9, 70); log_tree.column(col, width=col_width, anchor=tk.W, stretch=tk.NO)
        for entry in order_log:
            if not isinstance(entry, dict): continue
            formatted_row = []
            for col in sorted_columns:
                item = entry.get(col, '')
                if isinstance(item, float): formatted_row.append(f"{item:,.4f}")
                elif isinstance(item, datetime) or isinstance(item, pd.Timestamp): item = item.tz_localize('UTC') if item.tzinfo is None else item; formatted_row.append(item.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + ' ' + str(item.tzinfo))
                else: formatted_row.append(str(item))
            log_tree.insert("", tk.END, values=formatted_row)
        self.set_status("已顯示訂單日誌窗口")

    # --- 走勢分析方法 ---
    def start_trend_analysis(self):
        """開始走勢分析 - 完全按照N8N工作流邏輯"""
        try:
            # 獲取幣種名稱或交易對
            symbol_input = self.symbol_entry.get().strip().upper()
            trading_pair_input = self.trading_pair_entry.get().strip().upper()

            # 確定最終的交易對
            if trading_pair_input:
                # 如果用戶輸入了完整交易對，直接使用
                final_symbol = trading_pair_input
                self.append_result(f"✅ 使用完整交易對: {final_symbol}")
            elif symbol_input:
                # 如果用戶只輸入了幣種名稱，自動轉換為USDT交易對
                final_symbol = f"{symbol_input}USDT"
                self.append_result(f"✅ 自動轉換交易對: {symbol_input} → {final_symbol}")
            else:
                self.show_message("warning", "輸入缺失", "請輸入幣種名稱或完整交易對")
                return

            # 檢查Google API設置
            api_key = self.google_api_key_entry.get().strip()

            # 檢查是否使用測試模式
            if api_key.lower() == "test":
                self.append_result("🧪 使用測試模式進行分析")
                api_key = "test"
            else:
                # 如果沒有API密鑰，嘗試從環境變數讀取
                if not api_key:
                    import os
                    from dotenv import load_dotenv
                    load_dotenv()
                    api_key = os.environ.get("GOOGLE_API_KEY", "")
                    if api_key:
                        self.append_result(f"✅ 使用環境變數中的API密鑰: {api_key[:10]}...")
                    else:
                        self.append_result("❌ 未找到API密鑰")

            # 檢查是否有有效的配置
            if not api_key:
                self.append_result("❌ 未找到任何有效的Google AI配置")
                self.append_result("請檢查以下選項：")
                self.append_result("1. 在API密鑰欄位輸入您的Google API密鑰")
                self.append_result("2. 或者輸入 'test' 使用測試模式")
                self.append_result("3. 或者確認.env文件中的GOOGLE_API_KEY設置正確")
                self.show_message("warning", "配置缺失",
                                "未找到Google AI配置。\n\n請：\n1. 輸入API密鑰，或\n2. 輸入 'test' 使用測試模式，或\n3. 檢查.env文件配置")
                return

            # 獲取分析詳細程度
            detail_level = self.analysis_detail_var.get()

            # 清除結果並開始分析
            self.clear_results()
            self.append_result("🚀 開始N8N工作流分析")
            self.append_result(f"交易對: {final_symbol}")
            self.append_result(f"分析詳細程度: {detail_level}")
            self.append_result("自動獲取多時間框架數據: 15m, 1h, 1d")
            self.append_result("-" * 40)
            self.set_status("正在進行專業走勢分析...")

            # 禁用控件
            self.start_analysis_button.config(state=tk.DISABLED)

            # 啟動分析線程 - 使用N8N工作流邏輯
            threading.Thread(
                target=self._run_n8n_analysis_thread,
                args=(final_symbol, api_key, detail_level),
                daemon=True
            ).start()

        except Exception as e:
            self.show_message("error", "分析啟動失敗", f"啟動走勢分析時發生錯誤: {str(e)}")
            self.set_status("走勢分析啟動失敗")
            if hasattr(self, 'start_analysis_button'):
                self.start_analysis_button.config(state=tk.NORMAL)

    def _run_n8n_analysis_thread(self, symbol, api_key, detail_level):
        """N8N工作流分析執行線程 - 完全按照N8N邏輯"""
        try:
            from analysis.trend_analyzer import TrendAnalyzer

            self.set_status("初始化N8N工作流分析器...")
            analyzer = TrendAnalyzer(api_key=api_key)

            self.set_status("正在執行N8N工作流分析...")
            self.append_result("正在調用Google Gemini AI進行專業分析...")

            # 執行N8N工作流分析 - 不需要預先加載的數據
            analysis_result = analyzer.analyze_trend(
                data=None,  # N8N工作流會自動獲取數據
                symbol=symbol,
                timeframe="多時間框架",  # N8N工作流使用多時間框架
                detail_level=detail_level
            )

            # 儲存結果
            self.trend_analysis_results = analysis_result

            # 顯示結果
            self.append_result("--- N8N工作流分析結果 ---")
            self.append_result(f"分析時間: {analysis_result['generated_at']}")
            self.append_result(f"分析狀態: {analysis_result.get('status', '未知')}")
            if 'word_count' in analysis_result:
                self.append_result(f"分析字數: {analysis_result['word_count']} 字")
            self.append_result("-" * 40)

            # 在主結果區域顯示簡要信息
            preview_text = analysis_result['analysis_text'][:200] + "..." if len(analysis_result['analysis_text']) > 200 else analysis_result['analysis_text']
            self.append_result(f"分析預覽: {preview_text}")
            self.append_result("-" * 40)
            self.append_result("✅ 專業分析完成！點擊 '查看詳細分析' 按鈕查看完整報告")

            # 顯示詳細結果窗口
            self._show_trend_analysis_result_window(analysis_result)

            # 啟用查看詳細分析按鈕
            if hasattr(self, 'view_analysis_button'):
                self.view_analysis_button.config(state=tk.NORMAL)

            self.set_status("N8N工作流分析完成")

        except ImportError as e:
            self.append_result(f"錯誤: 無法導入分析模組 - {str(e)}")
            self.set_status("分析失敗: 模組導入錯誤")
        except Exception as e:
            self.append_result(f"分析過程中發生錯誤: {str(e)}")
            self.set_status("N8N工作流分析失敗")
            import traceback
            traceback.print_exc()
        finally:
            # 重新啟用控件
            if hasattr(self, 'start_analysis_button'):
                self.gui_queue.put(("enable_controls", None))

    def _run_trend_analysis_thread(self, data, api_key, project_id, detail_level):
        """走勢分析執行線程"""
        try:
            from analysis.trend_analyzer import TrendAnalyzer

            self.set_status("初始化分析器...")
            analyzer = TrendAnalyzer(api_key=api_key, project_id=project_id)

            # 從數據信息中提取符號和時間框架
            symbol = self.current_data_info.get('symbol', 'Unknown')
            timeframe = self.current_data_info.get('interval', 'Unknown')

            self.set_status("正在分析走勢...")
            self.append_result("正在調用Google Gemini AI進行分析...")

            # 執行分析
            analysis_result = analyzer.analyze_trend(data, symbol, timeframe, detail_level)

            # 儲存結果
            self.trend_analysis_results = analysis_result

            # 顯示結果
            self.append_result("--- 走勢分析結果 ---")
            self.append_result(f"分析時間: {analysis_result['generated_at']}")
            self.append_result(f"分析狀態: {analysis_result.get('status', '未知')}")
            if 'word_count' in analysis_result:
                self.append_result(f"分析字數: {analysis_result['word_count']} 字")
            self.append_result("-" * 30)

            # 在主結果區域顯示簡要信息
            preview_text = analysis_result['analysis_text'][:200] + "..." if len(analysis_result['analysis_text']) > 200 else analysis_result['analysis_text']
            self.append_result(f"分析預覽: {preview_text}")
            self.append_result("-" * 30)
            self.append_result("✅ 分析完成！點擊 '查看詳細分析' 按鈕查看完整報告")

            # 顯示詳細結果窗口
            self._show_trend_analysis_result_window(analysis_result)

            # 啟用查看詳細分析按鈕
            if hasattr(self, 'view_analysis_button'):
                self.view_analysis_button.config(state=tk.NORMAL)

            self.set_status("走勢分析完成")

        except ImportError as e:
            self.append_result(f"錯誤: 無法導入分析模組 - {str(e)}")
            self.set_status("分析失敗: 模組導入錯誤")
        except Exception as e:
            self.append_result(f"分析過程中發生錯誤: {str(e)}")
            self.set_status("走勢分析失敗")
            import traceback
            traceback.print_exc()
        finally:
            # 重新啟用控件
            self.gui_queue.put(("enable_start_button", None))

    def view_last_analysis(self):
        """查看最後一次的走勢分析結果"""
        if not self.trend_analysis_results:
            self.show_message("info", "無分析結果", "尚未執行走勢分析，或上次分析失敗。")
            return

        # 顯示最後一次的分析結果
        self._show_trend_analysis_result_window(self.trend_analysis_results)

    def _show_trend_analysis_result_window(self, analysis_result):
        """顯示走勢分析結果的專門窗口"""
        try:
            # 創建新窗口
            result_window = tk.Toplevel(self.master)
            result_window.title(f"走勢分析報告 - {analysis_result.get('symbol', '未知')} {analysis_result.get('timeframe', '')}")
            result_window.geometry("900x700")
            result_window.resizable(True, True)

            # 創建主框架
            main_frame = ttk.Frame(result_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # 頂部信息框架
            info_frame = ttk.LabelFrame(main_frame, text="分析信息")
            info_frame.pack(fill=tk.X, pady=(0, 10))

            # 分析信息
            info_text = f"""
分析時間: {analysis_result.get('generated_at', '未知')}
交易對: {analysis_result.get('symbol', '未知')}
時間框架: {analysis_result.get('timeframe', '未知')}
分析狀態: {analysis_result.get('status', '未知')}
分析字數: {analysis_result.get('word_count', 0)} 字
"""
            info_label = ttk.Label(info_frame, text=info_text.strip(), font=('Arial', 10))
            info_label.pack(anchor='w', padx=10, pady=5)

            # 分析結果框架
            result_frame = ttk.LabelFrame(main_frame, text="詳細分析報告")
            result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            # 創建文本框和滾動條
            text_frame = ttk.Frame(result_frame)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # 文本框
            result_text = tk.Text(text_frame, wrap=tk.WORD, font=('Microsoft JhengHei', 11),
                                bg='white', fg='black', relief=tk.FLAT, bd=1)
            result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # 垂直滾動條
            v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=result_text.yview)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            result_text.config(yscrollcommand=v_scrollbar.set)

            # 水平滾動條
            h_scrollbar = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=result_text.xview)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            result_text.config(xscrollcommand=h_scrollbar.set)

            # 插入分析結果
            analysis_text = analysis_result.get('analysis_text', '無分析結果')
            result_text.insert(tk.END, analysis_text)
            result_text.config(state=tk.DISABLED)  # 設為只讀

            # 按鈕框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)

            # 保存按鈕
            save_button = ttk.Button(button_frame, text="保存報告",
                                   command=lambda: self._save_analysis_report(analysis_result))
            save_button.pack(side=tk.LEFT, padx=(0, 10))

            # 複製按鈕
            copy_button = ttk.Button(button_frame, text="複製到剪貼板",
                                   command=lambda: self._copy_to_clipboard(analysis_text))
            copy_button.pack(side=tk.LEFT, padx=(0, 10))

            # 關閉按鈕
            close_button = ttk.Button(button_frame, text="關閉", command=result_window.destroy)
            close_button.pack(side=tk.RIGHT)

            # 設置窗口圖標和焦點
            result_window.focus_set()

            print("走勢分析結果窗口已顯示")

        except Exception as e:
            print(f"顯示結果窗口時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            self.show_message("error", "顯示錯誤", f"無法顯示分析結果窗口: {str(e)}")

    def _save_analysis_report(self, analysis_result):
        """保存分析報告到文件"""
        try:
            from tkinter import filedialog

            # 生成默認文件名
            symbol = analysis_result.get('symbol', 'Unknown')
            timeframe = analysis_result.get('timeframe', 'Unknown')
            timestamp = analysis_result.get('generated_at', datetime.now().strftime("%Y%m%d_%H%M%S"))
            timestamp_clean = timestamp.replace(':', '').replace('-', '').replace(' ', '_')

            default_filename = f"走勢分析_{symbol}_{timeframe}_{timestamp_clean}.txt"

            # 選擇保存位置
            file_path = filedialog.asksaveasfilename(
                title="保存走勢分析報告",
                defaultextension=".txt",
                initialname=default_filename,
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("Markdown文件", "*.md"),
                    ("所有文件", "*.*")
                ]
            )

            if file_path:
                # 準備報告內容
                report_content = f"""# 走勢分析報告

## 基本信息
- 分析時間: {analysis_result.get('generated_at', '未知')}
- 交易對: {analysis_result.get('symbol', '未知')}
- 時間框架: {analysis_result.get('timeframe', '未知')}
- 分析狀態: {analysis_result.get('status', '未知')}
- 分析字數: {analysis_result.get('word_count', 0)} 字

## 詳細分析

{analysis_result.get('analysis_text', '無分析結果')}

---
報告生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
生成工具: 加密貨幣交易系統 - 走勢分析模組
"""

                # 保存文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                self.show_message("info", "保存成功", f"分析報告已保存至:\n{file_path}")
                print(f"分析報告已保存: {file_path}")

        except Exception as e:
            print(f"保存報告時發生錯誤: {e}")
            self.show_message("error", "保存失敗", f"無法保存分析報告: {str(e)}")

    def _copy_to_clipboard(self, text):
        """複製文本到剪貼板"""
        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(text)
            self.master.update()  # 確保剪貼板更新
            self.show_message("info", "複製成功", "分析結果已複製到剪貼板")
            print("分析結果已複製到剪貼板")
        except Exception as e:
            print(f"複製到剪貼板時發生錯誤: {e}")
            self.show_message("error", "複製失敗", f"無法複製到剪貼板: {str(e)}")

# --- Main Entry Point ---
if __name__ == "__main__":
    print("初始化 GUI...")
    root = tk.Tk()
    # Optional Theming (keep commented out unless ttkthemes is installed)
    # try:
    #     from ttkthemes import ThemedTk
    #     root = ThemedTk(theme="arc")
    # except ImportError:
    #     print("ttkthemes 未安裝, 使用默認 Tk 主題。")
    #     pass # Use standard tk.Tk

    class TradingAppGUI:
        def __init__(self, master):
            self.master = master
            # 初始化所有GUI組件

    app = TradingAppGUI(root) # Use renamed class
    root.mainloop()
    print("GUI 已關閉。")
