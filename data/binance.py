# gui/app.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import threading
from datetime import datetime
import os
import importlib
import queue
import inspect
import traceback
import sys

# --- Import components from other project modules ---
try:
    from backtest.backtester import BacktestEngine
    # Import the strategy loader utility
    from utils.strategy_loader import load_available_strategies
    # Base class for type checking backtest strategies
    from backtesting import Strategy as BacktestingStrategy
    # Import Live Trader components
    from live.trader import LiveTrader
    from strategies.live_rsi_ema import LiveRsiEmaStrategy # Example live strategy
    # Import dotenv to load API keys from .env for live trading
    from dotenv import load_dotenv
    load_dotenv() # Load .env file at the start
except ImportError as e:
    # Handle missing local modules or backtesting lib
    print(f"FATAL: Error importing required modules for GUI: {e}")
    print("Ensure backtest, data, utils, live, strategies modules and libraries (backtesting, dotenv) are accessible.")
    # Cannot proceed without these, maybe raise or exit
    raise # Re-raise to stop execution if core components missing

# Helper (could also be in utils if used elsewhere)
def get_metric(perf_metrics, key, fmt="{:.2f}"):
    """Safely retrieves and formats a metric from the results dictionary."""
    val = perf_metrics.get(key)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 'N/A'
    try:
        if isinstance(val, (int, float)) and fmt: return fmt.format(val)
        else: return str(val)
    except: return str(val)


class TradingAppGUI: # Renamed class for clarity
    def __init__(self, master):
        self.master = master
        master.title("加密貨幣交易系統 (回測 / 實盤)") # Updated title
        master.geometry("850x700") # Increased height slightly for new widgets
        self.strategies_path = './strategies' # Relative path to strategies
        self.data_path = './data'             # Relative path to data (for backtest)
        self.strategy_classes = {}            # Stores display name -> strategy class (active mode)
        self.current_param_widgets = {}       # Stores param_key -> (widget, type, options/range)
        self.gui_queue = queue.Queue()
        self.backtest_results = None          # Stores the full results dict after a backtest
        self.backtest_plot_path = None        # Stores the path to the generated plot HTML
        self.live_trader_instance = None      # Stores the active LiveTrader instance

        # Ensure directories exist (helper function below)
        self._ensure_directory_and_init(self.strategies_path, "策略")
        self._ensure_directory_and_init(self.data_path, "數據")
        self._ensure_directory_and_init('./plots', "圖表") # Ensure plots dir exists

        # ----- GUI Element Creation -----

        # --- Mode Selection ---
        mode_frame = ttk.Frame(master); mode_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky='ew')
        ttk.Label(mode_frame, text="操作模式:").pack(side=tk.LEFT, padx=(0, 10))
        self.mode_var = tk.StringVar(value="backtest") # Default to backtest
        ttk.Radiobutton(mode_frame, text="回測", variable=self.mode_var, value="backtest", command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="實盤交易", variable=self.mode_var, value="live", command=self.on_mode_change).pack(side=tk.LEFT, padx=5)

        # --- Exchange Selection (Live Mode Only) ---
        self.exchange_frame = ttk.Frame(master) # Will be placed later by on_mode_change
        ttk.Label(self.exchange_frame, text="交易所:").pack(side=tk.LEFT, padx=(0, 5))
        self.exchange_combobox = ttk.Combobox(self.exchange_frame, values=["Alpaca"], state="readonly", width=15) # Add more exchanges later if needed
        self.exchange_combobox.set("Alpaca") # Default
        self.exchange_combobox.pack(side=tk.LEFT)
        # Grid placement handled by on_mode_change

        # --- Strategy Selection ---
        strategy_frame = ttk.Frame(master); strategy_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 5), sticky='ew') # Row changed to 2
        ttk.Label(strategy_frame, text="交易策略:").pack(side=tk.LEFT, padx=(0, 5))
        self.strategy_combobox = ttk.Combobox(strategy_frame, state="readonly", width=35); self.strategy_combobox.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.strategy_combobox.bind('<<ComboboxSelected>>', self.on_strategy_selected)


        # --- Data Loading Section (Backtest Mode Only) ---
        self.data_frame = ttk.LabelFrame(master, text="數據加載 (回測模式)") # Label updated
        # Grid placement handled by on_mode_change
        self.data_frame.columnconfigure(0, weight=1); self.data_frame.columnconfigure(1, weight=1)
        self.data_source_var = tk.StringVar(value="existing")
        ttk.Radiobutton(self.data_frame, text="使用現有數據", variable=self.data_source_var, value="existing", command=self.toggle_data_source).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        ttk.Radiobutton(self.data_frame, text="下載新數據 (Binance)", variable=self.data_source_var, value="new", command=self.toggle_data_source).grid(row=0, column=1, padx=5, pady=2, sticky='w') # Clarified source
        self.existing_data_frame = ttk.Frame(self.data_frame); self.existing_data_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        self.existing_data_combobox = ttk.Combobox(self.existing_data_frame, state="readonly"); self.existing_data_combobox.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.refresh_data_button = ttk.Button(self.existing_data_frame, text="刷新", command=self.load_existing_data_files, width=5); self.refresh_data_button.pack(side=tk.LEFT)
        self.load_existing_data_files() # Load data files list initially
        self.new_data_frame = ttk.Frame(self.data_frame); self.new_data_frame.columnconfigure(1, weight=1)
        ttk.Label(self.new_data_frame, text="交易對:").grid(row=0, column=0, sticky='w', padx=(0,5), pady=2); self.symbol_entry = ttk.Entry(self.new_data_frame, width=20); self.symbol_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew'); self.symbol_entry.insert(0, "BTCUSDT")
        ttk.Label(self.new_data_frame, text="時間框架:").grid(row=1, column=0, sticky='w', padx=(0,5), pady=2)
        self.valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        self.interval_combobox = ttk.Combobox(self.new_data_frame, values=self.valid_intervals, state="readonly", width=18)
        self.interval_combobox.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        self.interval_combobox.set('1h') # Default to 1 hour
        ttk.Label(self.new_data_frame, text="開始時間:").grid(row=2, column=0, sticky='w', padx=(0,5), pady=2); self.start_entry = ttk.Entry(self.new_data_frame, width=20); self.start_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew'); self.start_entry.insert(0, (datetime.now() - pd.Timedelta(days=365)).strftime("%Y/%m/%d 00:00"))
        ttk.Label(self.new_data_frame, text="結束時間:").grid(row=3, column=0, sticky='w', padx=(0,5), pady=2); self.end_entry = ttk.Entry(self.new_data_frame, width=20); self.end_entry.grid(row=3, column=1, padx=5, pady=2, sticky='ew'); self.end_entry.insert(0, datetime.now().strftime("%Y/%m/%d %H:%M"))
        self.download_button = ttk.Button(self.new_data_frame, text="下載數據", command=self.download_data); self.download_button.grid(row=4, column=0, columnspan=2, pady=(10, 2))
        self.download_status_label = ttk.Label(self.new_data_frame, text=""); self.download_status_label.grid(row=5, column=0, columnspan=2, pady=2)
        # --- NEW: Binance Fetch Status Display ---
        self.binance_fetch_status_label = ttk.Label(self.new_data_frame, text="", foreground="grey", wraplength=300); self.binance_fetch_status_label.grid(row=6, column=0, columnspan=2, pady=(2, 5), sticky='w')


        # --- Live Trading Parameters Frame (Live Mode Only) ---
        self.live_params_frame = ttk.LabelFrame(master, text="實盤參數") # Will be placed by on_mode_change
        self.live_params_frame.columnconfigure(1, weight=1)
        ttk.Label(self.live_params_frame, text="交易對 (Symbol):").grid(row=0, column=0, padx=5, pady=3, sticky='w')
        self.live_symbol_entry = ttk.Entry(self.live_params_frame, width=15); self.live_symbol_entry.grid(row=0, column=1, padx=5, pady=3, sticky='ew'); self.live_symbol_entry.insert(0, "BTC/USD") # Alpaca crypto format
        ttk.Label(self.live_params_frame, text="交易數量 (Qty):").grid(row=1, column=0, padx=5, pady=3, sticky='w')
        self.live_qty_entry = ttk.Entry(self.live_params_frame, width=15); self.live_qty_entry.grid(row=1, column=1, padx=5, pady=3, sticky='ew'); self.live_qty_entry.insert(0, "0.001")
        # Add Timeframe selection for Live mode
        ttk.Label(self.live_params_frame, text="時間框架:").grid(row=2, column=0, padx=5, pady=3, sticky='w')
        # Use the same valid intervals as backtest for consistency (defined in __init__)
        self.live_interval_combobox = ttk.Combobox(self.live_params_frame, values=self.valid_intervals, state="readonly", width=13)
        self.live_interval_combobox.grid(row=2, column=1, padx=5, pady=3, sticky='ew')
        self.live_interval_combobox.set('1h') # Default to 1 hour for live trading
        # Adjust paper trading checkbox row
        self.paper_trading_var = tk.BooleanVar(value=True) # Default to paper trading
        ttk.Checkbutton(self.live_params_frame, text="使用模擬盤 (Paper Trading)", variable=self.paper_trading_var).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='w')


        # --- Parameter Settings Section (Combined Backtest/Strategy) ---
        # Row changed to 4
        self.param_outer_frame = ttk.Frame(master); self.param_outer_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky='nsew') # Changed to self.param_outer_frame
        # Backtest Params (Backtest Mode Only)
        self.backtest_params_frame = ttk.LabelFrame(self.param_outer_frame, text="回測參數") # Use self.param_outer_frame
        self.backtest_params_frame.columnconfigure(1, weight=1)
        ttk.Label(self.backtest_params_frame, text="起始本金 (USDT):").grid(row=0, column=0, padx=5, pady=3, sticky='w'); self.capital_entry = ttk.Entry(self.backtest_params_frame, width=12); self.capital_entry.grid(row=0, column=1, padx=5, pady=3, sticky='ew'); self.capital_entry.insert(0, "100000")
        ttk.Label(self.backtest_params_frame, text="投入淨值比例:").grid(row=1, column=0, padx=5, pady=3, sticky='w'); self.size_frac_entry = ttk.Entry(self.backtest_params_frame, width=12); self.size_frac_entry.grid(row=1, column=1, padx=5, pady=3, sticky='ew'); self.size_frac_entry.insert(0, "0.1")
        ttk.Label(self.backtest_params_frame, text="槓桿倍數:").grid(row=2, column=0, padx=5, pady=3, sticky='w'); self.leverage_entry = ttk.Entry(self.backtest_params_frame, width=12); self.leverage_entry.grid(row=2, column=1, padx=5, pady=3, sticky='ew'); self.leverage_entry.insert(0, "1.0")
        ttk.Label(self.backtest_params_frame, text="進場偏移 (%)(可小數):").grid(row=3, column=0, padx=5, pady=3, sticky='w'); self.offset_entry = ttk.Entry(self.backtest_params_frame, width=12); self.offset_entry.grid(row=3, column=1, padx=5, pady=3, sticky='ew'); self.offset_entry.insert(0, "0.0")

        # Strategy Params (Both Modes)
        self.strategy_params_frame = ttk.LabelFrame(self.param_outer_frame, text="策略參數") # Use self.param_outer_frame
        self.strategy_params_frame.columnconfigure(0, weight=0, pad=5); self.strategy_params_frame.columnconfigure(1, weight=1, pad=5)
        # Packing order handled by on_mode_change

        # --- *** NEW: Live Status Display (Live Mode Only) *** ---
        # Row 5
        self.live_status_frame = ttk.LabelFrame(master, text="實時狀態")
        # Grid placement handled by on_mode_change
        self.live_status_frame.columnconfigure(1, weight=1) # Allow value labels to expand

        ttk.Label(self.live_status_frame, text="帳戶餘額:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.balance_var = tk.StringVar(value="N/A")
        self.balance_label = ttk.Label(self.live_status_frame, textvariable=self.balance_var, anchor=tk.W)
        self.balance_label.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(self.live_status_frame, text="當前持倉:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.positions_var = tk.StringVar(value="N/A")
        self.positions_label = ttk.Label(self.live_status_frame, textvariable=self.positions_var, anchor=tk.W, wraplength=300) # Allow wrapping
        self.positions_label.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(self.live_status_frame, text="當前掛單:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.orders_var = tk.StringVar(value="N/A")
        self.orders_label = ttk.Label(self.live_status_frame, textvariable=self.orders_var, anchor=tk.W, wraplength=300) # Allow wrapping
        self.orders_label.grid(row=2, column=1, padx=5, pady=2, sticky='ew')


        # --- Results / Log Display ---
        # Row changed to 6
        result_frame = ttk.LabelFrame(master, text="結果 / 日誌"); result_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')
        result_frame.rowconfigure(0, weight=1); result_frame.columnconfigure(0, weight=1)
        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD, relief=tk.FLAT, bd=0); self.result_text.grid(row=0, column=0, sticky='nsew', padx=1, pady=1) # Reduced height slightly
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview); scrollbar.grid(row=0, column=1, sticky='ns')
        self.result_text['yscrollcommand'] = scrollbar.set

        # --- Control Buttons ---
        # Row changed to 7
        self.control_frame = ttk.Frame(master); self.control_frame.grid(row=7, column=0, columnspan=2, pady=(0, 10))
        self.control_frame.columnconfigure(0, weight=1)
        button_inner_frame = ttk.Frame(self.control_frame); button_inner_frame.grid(row=0, column=0)
        # Start/Stop buttons will be managed by on_mode_change
        self.start_button = ttk.Button(button_inner_frame, text="開始回測", command=self.start_backtest) # Initial text/command
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_inner_frame, text="停止交易", command=self.stop_live_trading, state=tk.DISABLED) # Initially hidden/disabled
        # self.stop_button packing handled by on_mode_change
        self.clear_button = ttk.Button(button_inner_frame, text="清除日誌", command=self.clear_results); self.clear_button.pack(side=tk.LEFT, padx=5)
        # View buttons remain, but might be disabled in live mode or show different things
        self.view_plot_button = ttk.Button(button_inner_frame, text="查看回測圖表", command=self.view_backtest_plot, state=tk.DISABLED); self.view_plot_button.pack(side=tk.LEFT, padx=5)
        self.view_trades_button = ttk.Button(button_inner_frame, text="查看交易記錄", command=self.view_trade_records, state=tk.DISABLED); self.view_trades_button.pack(side=tk.LEFT, padx=5)
        self.view_order_log_button = ttk.Button(button_inner_frame, text="查看訂單日誌", command=self.view_order_log, state=tk.DISABLED); self.view_order_log_button.pack(side=tk.LEFT, padx=5)

        # --- Status Bar ---
        # Row changed to 8
        self.status_bar = ttk.Label(master, text="準備就緒", relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2)); self.status_bar.grid(row=8, column=0, columnspan=3, sticky='ew')

        # --- Final Layout & Start ---
        master.columnconfigure(0, weight=1); master.columnconfigure(1, weight=1)
        master.rowconfigure(6, weight=1) # Row 6 (results/log) should expand

        # Initial UI state based on default mode (backtest)
        self.on_mode_change() # Call this to set initial visibility and load strategies

        print("強制更新 UI..."); master.update_idletasks(); master.update(); print("UI 更新完成。")
        self.process_gui_queue()
        # --- Add window close handler ---
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        print("TradingAppGUI 初始化完成。")

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
        print(f"模式切換: {mode}")

        # Clear previous strategy params UI first
        for w in self.strategy_params_frame.winfo_children(): w.destroy()
        self.current_param_widgets = {}
        self.strategy_combobox.set('') # Clear strategy selection

        if mode == "backtest":
            # Show Backtest related frames, hide Live frames
            self.exchange_frame.grid_remove()
            self.data_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='ew') # Place data frame
            self.live_params_frame.grid_remove()
            self.live_status_frame.grid_remove() # Hide live status frame
            # Ensure param_outer_frame children are packed correctly
            self.backtest_params_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='nw', in_=self.param_outer_frame) # Pack backtest params
            self.strategy_params_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, in_=self.param_outer_frame) # Pack strategy params next to it

            # Configure buttons for Backtest
            self.start_button.config(text="開始回測", command=self.start_backtest, state=tk.NORMAL)
            self.stop_button.pack_forget() # Hide stop button
            self.view_plot_button.config(state=tk.DISABLED) # Reset view buttons
            self.view_trades_button.config(state=tk.DISABLED)
            self.view_order_log_button.config(state=tk.DISABLED)
            self.clear_button.config(text="清除結果") # Reset clear button text

            # Load backtest strategies
            self.load_strategies(live_mode=False)
            self.toggle_data_source() # Ensure correct data source view is shown

        elif mode == "live":
            # Show Live Trading related frames, hide Backtest frames
            self.exchange_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,5), sticky='w') # Place exchange frame
            self.data_frame.grid_remove() # Hide data loading
            self.backtest_params_frame.pack_forget() # Hide backtest params
            self.live_params_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky='ew') # Place live params frame
            # Ensure strategy params frame is packed correctly (alone in outer frame)
            self.strategy_params_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, in_=self.param_outer_frame)
            # Show live status frame
            self.live_status_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky='ew') # Place live status frame

            # Configure buttons for Live Trading
            self.start_button.config(text="開始交易", command=self.start_live_trading, state=tk.NORMAL)
            self.stop_button.pack(side=tk.LEFT, padx=5) # Show stop button
            self.stop_button.config(state=tk.DISABLED) # Initially disabled until trading starts
            self.view_plot_button.config(state=tk.DISABLED) # Disable backtest-specific views
            self.view_trades_button.config(state=tk.DISABLED) # Could potentially show live trades later
            self.view_order_log_button.config(state=tk.DISABLED) # Could potentially show live order log later
            self.clear_button.config(text="清除日誌") # Update clear button text

            # Load live strategies
            self.load_strategies(live_mode=True)

        # Update params UI after loading strategies for the new mode
        self.update_strategy_params_ui()
        self.set_status(f"模式已切換至: {'回測' if mode == 'backtest' else '實盤交易'}")


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
        # (Modified to handle live trader updates)
        try:
            while True:
                msg_type, data = self.gui_queue.get_nowait()
                if msg_type == "messagebox":
                    level, title, message = data
                    if level == "error": messagebox.showerror(title, message)
                    elif level == "warning": messagebox.showwarning(title, message)
                    else: messagebox.showinfo(title, message)
                elif msg_type == "status": self.status_bar.config(text=data)
                elif msg_type == "download_status": self.download_status_label.config(text=data)
                elif msg_type == "result_append": self.result_text.insert(tk.END, data); self.result_text.see(tk.END)
                elif msg_type == "result_clear": self.result_text.delete(1.0, tk.END)
                elif msg_type == "enable_controls": self.toggle_controls(True)
                elif msg_type == "disable_controls": self.toggle_controls(False)
                elif msg_type == "reload_data_files": self.load_existing_data_files()
                elif msg_type == "live_trade_started": 
                    self.toggle_live_controls(trading=True)
                    # Clear previous status on start
                    self.balance_var.set("獲取中...")
                    self.positions_var.set("獲取中...")
                    self.orders_var.set("獲取中...")
                elif msg_type == "live_trade_stopped": 
                    self.toggle_live_controls(trading=False)
                    # Optionally clear status on stop, or leave last known
                    # self.balance_var.set("N/A")
                    # self.positions_var.set("N/A")
                    # self.orders_var.set("N/A")
                elif msg_type == "update_live_status":
                    # Expect data to be a dictionary {'balance': ..., 'positions': ..., 'orders': ...}
                    if isinstance(data, dict):
                        self.balance_var.set(data.get('balance', self.balance_var.get()))
                        self.positions_var.set(data.get('positions', self.positions_var.get()))
                        self.orders_var.set(data.get('orders', self.orders_var.get()))
                elif msg_type == "binance_fetch_status":
                    # --- NEW: Handle Binance fetch status updates ---
                    if isinstance(data, dict):
                        status_text = f"Binance ({data.get('symbol', '?')}) 下載: "
                        status_text += f"嘗試 {data.get('total_attempts', 0)} 次 "
                        status_text += f"(成功 {data.get('successful_attempts', 0)}, "
                        status_text += f"失敗 {data.get('failed_attempts', 0)}). "
                        last_err = data.get('last_error')
                        if last_err:
                            err_time = last_err.get('timestamp', datetime.now()).strftime('%H:%M:%S')
                            status_text += f"\n最後錯誤 ({err_time}): {last_err.get('error_type', 'Unknown')} - {last_err.get('message', 'N/A')}"
                        else:
                            if data.get('successful_attempts', 0) > 0:
                                status_text += "下載成功。"
                        
                        # Update the dedicated label
                        if hasattr(self, 'binance_fetch_status_label') and self.binance_fetch_status_label.winfo_exists():
                            self.binance_fetch_status_label.config(text=status_text)

        except queue.Empty: pass
        finally: self.master.after(100, self.process_gui_queue) # Check queue every 100ms

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
            self.download_button.config(state=st)
            self.refresh_data_button.config(state=st)
            self.existing_data_combobox.config(state='readonly' if enabled else tk.DISABLED)
            # Enable view buttons only if results exist and contain the relevant data
            st_view_plot = tk.NORMAL if enabled and self.backtest_plot_path else tk.DISABLED
            st_view_trades = tk.NORMAL if enabled and self.backtest_results and 'trades' in self.backtest_results and not self.backtest_results['trades'].empty else tk.DISABLED
            st_view_order_log = tk.NORMAL if enabled and self.backtest_results and '_order_log' in self.backtest_results and self.backtest_results['_order_log'] else tk.DISABLED
            self.view_plot_button.config(state=st_view_plot)
            self.view_trades_button.config(state=st_view_trades)
            self.view_order_log_button.config(state=st_view_order_log)
            # Backtest param entries
            for e in [self.capital_entry, self.size_frac_entry, self.leverage_entry, self.offset_entry]:
                 if e and e.winfo_exists(): e.config(state=st)
            # Hide live controls
            self.stop_button.config(state=tk.DISABLED)


        elif mode == 'live':
            # Live trading controls are handled by toggle_live_controls
            self.toggle_live_controls(trading=(self.live_trader_instance is not None and self.live_trader_instance.running))
            # Disable backtest-specific view buttons
            self.view_plot_button.config(state=tk.DISABLED)
            self.view_trades_button.config(state=tk.DISABLED) # Or adapt later
            self.view_order_log_button.config(state=tk.DISABLED) # Or adapt later


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
        self.exchange_combobox.config(state='readonly' if not trading else tk.DISABLED)
        self.strategy_combobox.config(state='readonly' if not trading else tk.DISABLED)

        # Live param entries
        for e in [self.live_symbol_entry, self.live_qty_entry]:
             if e and e.winfo_exists(): e.config(state=param_st)
        # Paper trading checkbox
        cb = self.live_params_frame.winfo_children()[-1] # Assuming checkbox is last
        if isinstance(cb, ttk.Checkbutton): cb.config(state=param_st)

        # Strategy params
        for widget_tuple in self.current_param_widgets.values():
             widget = widget_tuple[0]
             if widget and widget.winfo_exists():
                 if isinstance(widget, ttk.Combobox): widget.config(state='readonly' if not trading else tk.DISABLED)
                 else: widget.config(state=param_st)


    def set_status(self, m): self.gui_queue.put(("status", m))
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

    def download_data(self):
        # (Unmodified - still downloads Binance data for backtesting)
        sym=self.symbol_entry.get().replace('/','').upper(); s=self.start_entry.get(); e=self.end_entry.get()
        interval = self.interval_combobox.get() # Get selected interval

        if not sym: self.show_message("warning","輸入錯誤","請輸入交易對"); return
        if not interval or interval not in self.valid_intervals: # Validate interval
            self.show_message("warning", "輸入錯誤", "請選擇有效的時間框架"); return

        try:
            sd=datetime.strptime(s,"%Y/%m/%d %H:%M"); ed=datetime.strptime(e,"%Y/%m/%d %H:%M")
            if sd>=ed: self.show_message("warning","輸入錯誤","開始需早於結束"); return
            fn=f"{sym}_{sd:%Y%m%d%H%M}_{ed:%Y%m%d%H%M}_{interval}.csv"; fp=os.path.join(self.data_path,fn)
            self.gui_queue.put(("disable_controls",None)); self.gui_queue.put(("download_status",f"下載 {sym} ({interval})...")); self.set_status(f"下載 {sym} ({interval})...")
            # --- Pass gui_queue to the download thread ---
            threading.Thread(target=self._d_thread, args=(sym, interval, sd, ed, fp, self.gui_queue), daemon=True).start()
        except ValueError: self.show_message("error","格式錯誤","時間格式需為 YYYY/MM/DD HH:MM")
        except Exception as e: self.show_message("error","錯誤",f"準備下載時出錯: {e}"); self.gui_queue.put(("enable_controls",None)); self.gui_queue.put(("download_status","失敗")); self.set_status("下載失敗")

    def _d_thread(self, sym, interval, sd, ed, fp, monitor_queue):
        # --- Pass monitor_queue to fetch_historical_data ---
        try:
            if 'fetch_historical_data' not in globals(): raise RuntimeError("fetch func missing")
            fetch_historical_data(
                symbol=sym,
                interval=interval,
                start_time=int(sd.timestamp()*1000),
                end_time=int(ed.timestamp()*1000),
                output_path=fp,
                monitor_queue=monitor_queue # Pass the queue here
            )
            # --- Success messages ---
            self.gui_queue.put(("reload_data_files",None))
            self.show_message("info","完成",f"下載至\n{fp}")
            self.gui_queue.put(("download_status",f"{os.path.basename(fp)} 完成"))
            self.set_status("下載完成")
        except Exception as e:
            # --- Error messages (monitor queue already handled errors inside fetch_historical_data) ---
            self.show_message("error","下載錯誤",f"下載 {sym} ({interval}) 最終失敗: {e}")
            self.gui_queue.put(("download_status",f"{sym} ({interval}) 失敗"))
            self.set_status(f"{sym} ({interval}) 下載失敗")
            # Print traceback for debugging
            traceback.print_exc()
        finally:
            # --- Always re-enable controls ---
            self.gui_queue.put(("enable_controls",None))

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

    # --- Backtest Execution (Modified to use helper) ---
    def start_backtest(self):
        sn = self.strategy_combobox.get()
        if not sn: self.show_message("warning", "選擇錯誤", "請選擇策略"); return

        # --- Get Backtest Parameters ---
        try:
            cap = float(self.capital_entry.get())
            # size_frac is now a strategy parameter, remove from here
            # size_frac = float(self.size_frac_entry.get())
            lev = float(self.leverage_entry.get())
            offset_percent = float(self.offset_entry.get())
            if not (cap > 0): raise ValueError("起始本金必須 > 0")
            # if not (0 < size_frac <= 1): raise ValueError("投入淨值比例必須介於 0 和 1 之間 (不含 0)") # Moved to strategy params
            if not (lev > 0): raise ValueError("槓桿倍數必須 > 0")
            if not (offset_percent >= 0): raise ValueError("進場偏移百分比必須 >= 0")
        except ValueError as e: self.show_message("warning", "回測參數錯誤", f"檢查回測參數:\n{e}"); return
        except Exception as e: self.show_message("error", "參數讀取錯誤", f"讀取回測參數時發生未知錯誤:\n{e}"); traceback.print_exc(); return

        # --- Get Strategy Parameters using helper ---
        try:
            sp = self._get_validated_strategy_params()
            sc = self.strategy_classes.get(sn) # Get strategy class
            if not sc: raise RuntimeError(f"找不到策略類別: {sn}")
        except (ValueError, RuntimeError) as e:
            self.show_message("warning", "策略參數錯誤", f"檢查策略參數:\n{e}")
            return
        except Exception as e:
            self.show_message("error", "參數讀取錯誤", f"讀取策略參數時發生未知錯誤:\n{e}")
            traceback.print_exc()
            return

        # --- Get Data File ---
        if self.data_source_var.get() == "existing":
            cf = self.existing_data_combobox.get()
            if not cf: self.show_message("warning","選擇錯誤","請選擇數據文件"); return
            if not cf: self.show_message("warning", "選擇錯誤", "請選擇數據文件"); return
            cp = os.path.join(self.data_path, cf)
            if not os.path.exists(cp): self.show_message("error", "文件錯誤", f"數據文件不存在:\n{cp}"); return
        else:
            self.show_message("info", "提示", "請切換到 '使用現有數據' 並選擇已下載的文件。")
            return

        # --- Start Backtest Thread ---
        self.gui_queue.put(("disable_controls", None))
        self.clear_results()
        self.append_result(f"開始回測: {sn}\n數據: {os.path.basename(cp)}\n")
        # Removed size_frac from backtest params log, it's now in strategy params
        self.append_result(f"回測參數: 本金={cap:,.2f}, 槓桿={lev:.2f}x, 進場偏移={offset_percent:.2f}%\n")
        param_str = ", ".join(f"{k}={v}" for k, v in sp.items()) if sp else "無"
        self.append_result(f"策略參數: {param_str}\n")
        self.append_result("-" * 30)
        self.set_status(f"回測 {sn}...")
        # Pass validated strategy params (sp) to the thread
        threading.Thread(target=self._run_backtest_thread, args=(cp, sc, sp, cap, lev, offset_percent), daemon=True).start()


    # --- Backtest Thread (Renamed) ---
    def _run_backtest_thread(self, csv_path, strategy_class, strategy_params, capital, leverage, offset_percent):
        # (Logic remains the same as _run_thread in previous version)
        try:
            self.set_status("加載數據..."); data = None
            try: # Data loading and preprocessing...
                data = pd.read_csv(csv_path)
                timestamp_col = None; common_ts = ['timestamp','open_time','Date','time','datetime']
                for c in common_ts:
                    if c in data.columns: timestamp_col = c; break
                if timestamp_col is None: raise ValueError("找不到時間戳列 (例如 'timestamp', 'Date', 'open_time')")
                try:
                    if pd.api.types.is_numeric_dtype(data[timestamp_col]):
                        if data[timestamp_col].max() > 2_000_000_000: data['ts_dt'] = pd.to_datetime(data[timestamp_col], unit='ms', utc=True, errors='coerce')
                        else: data['ts_dt'] = pd.to_datetime(data[timestamp_col], unit='s', utc=True, errors='coerce')
                    else: data['ts_dt'] = pd.to_datetime(data[timestamp_col], utc=True, errors='coerce')
                except Exception as parse_err: raise ValueError(f"無法解析時間戳列 '{timestamp_col}': {parse_err}")
                data.dropna(subset=['ts_dt'], inplace=True)
                if data.empty: raise ValueError("數據中無有效時間戳")
                data.set_index('ts_dt', inplace=True); data.sort_index(inplace=True)
                if data.index.has_duplicates: print(f"警告: 數據索引中有 {data.index.duplicated().sum()} 個重複項，將保留第一個。"); data = data[~data.index.duplicated(keep='first')]
                remap = {'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume','open_price':'Open','high_price':'High','low_price':'Low','close_price':'Close'}
                data.columns = [remap.get(c.lower(), c) for c in data.columns]
                req = ['Open','High','Low','Close']
                missing_cols = [c for c in req if c not in data.columns]
                if missing_cols: raise ValueError(f"數據缺少必要列: {', '.join(missing_cols)}")
                for c in req + (['Volume'] if 'Volume' in data.columns else []):
                    if c in data.columns: data[c] = pd.to_numeric(data[c], errors='coerce')
                if 'Volume' not in data.columns: print("警告: 數據缺少 'Volume' 列，將以 0 填充。"); data['Volume'] = 0.0
                else: vol_na_count = data['Volume'].isna().sum(); data['Volume'].fillna(0.0, inplace=True)
                ohlc_na_count = data[req].isna().any(axis=1).sum()
                if ohlc_na_count > 0: print(f"警告: OHLC 列有 {ohlc_na_count} 行包含缺失值，將被移除。"); data.dropna(subset=req, inplace=True)
                data = data[req + ['Volume']]
                if data.empty: raise ValueError("數據預處理後為空。")
                print(f"數據加載完成. Shape: {data.shape}. 時間範圍: {data.index[0]} 到 {data.index[-1]}")
            except Exception as e: print(f"數據處理錯誤: {e}"); self.show_message("error","數據錯誤",f"處理數據文件 '{os.path.basename(csv_path)}' 時出錯:\n{e}"); self.set_status("數據處理失敗"); self.gui_queue.put(("enable_controls",None)); traceback.print_exc(); return

            self.set_status("初始化回測引擎...")
            engine = BacktestEngine(data=data, strategy_class=strategy_class, strategy_params=strategy_params, initial_capital=capital, leverage=leverage, offset_value=offset_percent) # Use offset_value, let offset_type/basis use defaults
            self.set_status("執行回測...")
            engine.run()
            self.set_status("生成回測報告...")
            results = engine.get_analysis_results()
            self.backtest_results = results
            pm = results.get('performance_metrics', {})
            def get_m(k, f="{:.2f}"): v=pm.get(k); return 'N/A' if v is None or (isinstance(v,float) and pd.isna(v)) else (f.format(v) if isinstance(v,(int,float)) and f else str(v))
            self.append_result("--- 回測結果摘要 ---")
            self.append_result(f"  時間範圍: {get_m('Start','{}')} - {get_m('End','{}')} ({get_m('Duration','{}')})")
            self.append_result(f"  最終權益: {get_m('Equity Final [$]','{:,.2f}')} (峰值: {get_m('Equity Peak [$]','{:,.2f}')})")
            self.append_result(f"  總收益率: {get_m('Return [%]')}% (年化: {get_m('Return (Ann.) [%]')}%)\n  買入持有收益率: {get_m('Buy & Hold Return [%]')}%")
            self.append_result(f"  最大回撤: {get_m('Max. Drawdown [%]')}% (平均: {get_m('Avg. Drawdown [%]')}%)\n  夏普比率: {get_m('Sharpe Ratio')} | 索提諾比率: {get_m('Sortino Ratio')}")
            self.append_result(f"  交易次數: {get_m('# Trades','{}')} | 勝率: {get_m('Win Rate [%]')}% | 盈虧比: {get_m('Profit Factor')}")
            self.append_result(f"  平均交易收益: {get_m('Avg. Trade [%]')}% (最佳: {get_m('Best Trade [%]')}% / 最差: {get_m('Worst Trade [%]')}%)\n" + "-" * 25)
            self.set_status("生成回測圖表...")
            base_strategy_name = getattr(strategy_class, '__name__', 'UnknownStrategy')
            plot_filename = f"plots/{base_strategy_name}_{datetime.now():%Y%m%d_%H%M%S}.html"
            plot_path = engine.generate_plot(filename=plot_filename)
            if plot_path: self.backtest_plot_path = plot_path; self.append_result(f"圖表已保存至: {os.path.basename(plot_path)}"); self.set_status("回測完成 (含圖表)")
            else: self.append_result("\n錯誤：生成回測圖表失敗。"); self.set_status("回測完成 (圖表生成失敗)")
        except (FileNotFoundError, ValueError, RuntimeError) as e: self.show_message("error","回測錯誤",str(e)); self.set_status("回測失敗"); self.append_result(f"\n錯誤: {e}"); traceback.print_exc(); self.backtest_results = {'_order_log': engine.order_log if 'engine' in locals() else []}; self.backtest_plot_path = None
        except Exception as e: error_details=traceback.format_exc(); self.show_message("error","未知錯誤",f"回測過程中發生未預期的錯誤: {e}\n詳情請查看控制台輸出。"); self.set_status("回測異常終止"); self.append_result(f"\n未知錯誤: {e}\n{error_details}"); print(f"--- 未知回測錯誤 ---\n{error_details}"); self.backtest_results = {'_order_log': engine.order_log if 'engine' in locals() else []}; self.backtest_plot_path = None
        finally: self.gui_queue.put(("enable_controls", None))


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

    app = TradingAppGUI(root) # Use renamed class
    root.mainloop()
    print("GUI 已關閉。")