# gui/backtest_ui.py
"""
回測UI管理器 - 專門處理回測相關界面
"""

import tkinter as tk
from tkinter import ttk
import threading
from datetime import datetime
from .base_ui import BaseUIComponent

class BacktestUI(BaseUIComponent):
    """回測UI管理器"""

    def __init__(self, base_manager):
        super().__init__(base_manager)
        self.backtest_results = None
        self.backtest_plot_path = None
        self.current_data = None
        self.current_data_info = {}
        self.strategy_classes = {}
        self.current_param_widgets = {}

    def show_ui(self, parent_frame):
        """顯示回測UI"""
        # 創建主框架
        self.main_frame = ttk.Frame(parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 設置回測UI
        self._setup_backtest_ui()

        # 加載策略
        self._load_strategies()

    def _setup_backtest_ui(self):
        """設置回測UI"""
        # 策略選擇
        strategy_frame = ttk.LabelFrame(self.main_frame, text="策略選擇")
        strategy_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        ttk.Label(strategy_frame, text="選擇策略:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.strategy_combobox = ttk.Combobox(strategy_frame, state="readonly")
        self.strategy_combobox.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.strategy_combobox.bind("<<ComboboxSelected>>", self.on_strategy_selected)

        # 數據加載框架
        data_frame = ttk.LabelFrame(self.main_frame, text="數據加載")
        data_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        # 交易對選擇
        ttk.Label(data_frame, text="交易對:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.symbol_var = tk.StringVar(value="BTCUSDT")
        self.symbol_entry = ttk.Entry(data_frame, textvariable=self.symbol_var)
        self.symbol_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        # 時間框架選擇
        ttk.Label(data_frame, text="時間框架:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.interval_var = tk.StringVar(value="1h")
        intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        self.interval_combo = ttk.Combobox(data_frame, textvariable=self.interval_var, values=intervals, state="readonly")
        self.interval_combo.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        # 日期選擇
        ttk.Label(data_frame, text="開始日期:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.start_date_entry = ttk.Entry(data_frame, textvariable=self.start_date_var)
        self.start_date_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(data_frame, text="結束日期:").grid(row=3, column=0, padx=5, pady=2, sticky='w')
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.end_date_entry = ttk.Entry(data_frame, textvariable=self.end_date_var)
        self.end_date_entry.grid(row=3, column=1, padx=5, pady=2, sticky='ew')

        # 數據狀態顯示
        ttk.Label(data_frame, text="數據狀態:").grid(row=4, column=0, padx=5, pady=2, sticky='w')
        self.data_status_var = tk.StringVar(value="未加載")
        ttk.Label(data_frame, textvariable=self.data_status_var).grid(row=4, column=1, padx=5, pady=2, sticky='w')

        # 加載數據按鈕
        self.load_data_btn = ttk.Button(data_frame, text="加載數據", command=self.prepare_data)
        self.load_data_btn.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        # 參數框架
        param_frame = ttk.LabelFrame(self.main_frame, text="參數設置")
        param_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        # 回測參數
        backtest_params_frame = ttk.Frame(param_frame)
        backtest_params_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='nw')

        ttk.Label(backtest_params_frame, text="起始本金:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.capital_var = tk.StringVar(value="10000")
        self.capital_entry = ttk.Entry(backtest_params_frame, textvariable=self.capital_var, width=10)
        self.capital_entry.grid(row=0, column=1, padx=5, pady=2, sticky='w')

        ttk.Label(backtest_params_frame, text="槓桿倍數:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.leverage_var = tk.StringVar(value="1.0")
        self.leverage_entry = ttk.Entry(backtest_params_frame, textvariable=self.leverage_var, width=10)
        self.leverage_entry.grid(row=1, column=1, padx=5, pady=2, sticky='w')

        ttk.Label(backtest_params_frame, text="進場偏移(%):").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.offset_var = tk.StringVar(value="0.0")
        self.offset_entry = ttk.Entry(backtest_params_frame, textvariable=self.offset_var, width=10)
        self.offset_entry.grid(row=2, column=1, padx=5, pady=2, sticky='w')

        # 策略參數框架
        self.strategy_params_frame = ttk.Frame(param_frame)
        self.strategy_params_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # 按鈕框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky='ew')

        self.start_button = ttk.Button(button_frame, text="開始回測", command=self.start_backtest)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(button_frame, text="清除結果", command=self.clear_results)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # 回測結果查看按鈕
        self.view_plot_button = ttk.Button(button_frame, text="查看圖表", command=self.view_backtest_plot, state=tk.DISABLED)
        self.view_plot_button.pack(side=tk.LEFT, padx=5)

        self.view_trades_button = ttk.Button(button_frame, text="查看交易", command=self.view_trade_records, state=tk.DISABLED)
        self.view_trades_button.pack(side=tk.LEFT, padx=5)

        self.view_order_log_button = ttk.Button(button_frame, text="查看訂單日誌", command=self.view_order_log, state=tk.DISABLED)
        self.view_order_log_button.pack(side=tk.LEFT, padx=5)

        # 配置權重
        self.main_frame.columnconfigure(0, weight=1)
        strategy_frame.columnconfigure(1, weight=1)
        data_frame.columnconfigure(1, weight=1)

    def _load_strategies(self):
        """加載策略"""
        try:
            import sys
            import os

            # 確保項目根目錄在路徑中
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from utils.strategy_loader import load_available_strategies

            # 使用絕對路徑
            strategies_path = os.path.join(project_root, 'strategies')
            self.strategy_classes = load_available_strategies(strategies_path)
            strategy_names = list(self.strategy_classes.keys())
            self.strategy_combobox['values'] = strategy_names
            if strategy_names:
                self.strategy_combobox.set(strategy_names[0])
                self.update_strategy_params_ui()
                print(f"成功加載 {len(strategy_names)} 個回測策略")
            else:
                print("未找到任何回測策略")
        except Exception as e:
            error_msg = f"無法加載策略: {str(e)}"
            print(f"策略加載錯誤: {error_msg}")
            self.show_message("error", "策略加載失敗", error_msg)
            import traceback
            traceback.print_exc()

    def on_strategy_selected(self, event=None):
        """策略選擇事件"""
        self.update_strategy_params_ui()

    def update_strategy_params_ui(self):
        """更新策略參數UI"""
        # 清除現有參數控件
        for widget in self.strategy_params_frame.winfo_children():
            widget.destroy()
        self.current_param_widgets = {}

        strategy_name = self.strategy_combobox.get()
        if not strategy_name or strategy_name not in self.strategy_classes:
            return

        strategy_class = self.strategy_classes[strategy_name]

        # 檢查策略是否有參數定義
        if hasattr(strategy_class, '_params_def'):
            params_def = strategy_class._params_def

            ttk.Label(self.strategy_params_frame, text=f"{strategy_name} 參數:",
                     font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='w')

            row = 1
            for param_name, param_info in params_def.items():
                # 參數標籤
                ttk.Label(self.strategy_params_frame, text=f"{param_name}:").grid(row=row, column=0, padx=5, pady=2, sticky='w')

                # 解析參數信息 - 支持tuple格式
                if isinstance(param_info, tuple) and len(param_info) >= 3:
                    # 格式: (description, type, default, range_or_choices)
                    param_type = param_info[1]
                    default_value = param_info[2]

                    # 檢查是否有選擇列表
                    if len(param_info) > 3 and isinstance(param_info[3], list):
                        # 下拉選擇
                        var = tk.StringVar(value=str(default_value))
                        widget = ttk.Combobox(self.strategy_params_frame, textvariable=var,
                                            values=param_info[3], state="readonly", width=15)
                    else:
                        # 文本輸入
                        var = tk.StringVar(value=str(default_value))
                        widget = ttk.Entry(self.strategy_params_frame, textvariable=var, width=15)
                elif isinstance(param_info, dict):
                    # 字典格式
                    if param_info.get('type') == 'choice':
                        # 下拉選擇
                        var = tk.StringVar(value=str(param_info.get('default', '')))
                        widget = ttk.Combobox(self.strategy_params_frame, textvariable=var,
                                            values=param_info.get('choices', []), state="readonly", width=15)
                    else:
                        # 文本輸入
                        var = tk.StringVar(value=str(param_info.get('default', '')))
                        widget = ttk.Entry(self.strategy_params_frame, textvariable=var, width=15)
                else:
                    # 未知格式，使用默認
                    var = tk.StringVar(value=str(param_info))
                    widget = ttk.Entry(self.strategy_params_frame, textvariable=var, width=15)

                widget.grid(row=row, column=1, padx=5, pady=2, sticky='w')
                self.current_param_widgets[param_name] = (var, widget)
                row += 1

    def prepare_data(self):
        """準備數據"""
        # 這裡實現數據加載邏輯
        symbol = self.symbol_var.get().strip().upper()
        interval = self.interval_var.get()

        if not symbol:
            self.show_message("error", "錯誤", "請輸入交易對符號")
            return

        self.set_status(f"正在準備 {symbol} {interval} 數據...")
        self.data_status_var.set("準備中...")

        # 這裡可以添加實際的數據加載邏輯
        # 暫時設置為已加載狀態
        self.data_status_var.set("已加載")
        self.current_data = True  # 模擬數據已加載
        self.set_status("數據準備完成")

    def start_backtest(self):
        """開始回測"""
        if not self.current_data:
            self.show_message("warning", "數據缺失", "請先加載數據")
            return

        strategy_name = self.strategy_combobox.get()
        if not strategy_name:
            self.show_message("warning", "策略缺失", "請選擇策略")
            return

        self.set_status("正在進行回測...")
        self.append_result("開始回測...")

        # 這裡實現回測邏輯
        # 暫時顯示完成消息
        self.append_result("回測完成！")
        self.set_status("回測完成")

    def view_backtest_plot(self):
        """查看回測圖表"""
        self.show_message("info", "功能開發中", "圖表查看功能正在開發中")

    def view_trade_records(self):
        """查看交易記錄"""
        self.show_message("info", "功能開發中", "交易記錄查看功能正在開發中")

    def view_order_log(self):
        """查看訂單日誌"""
        self.show_message("info", "功能開發中", "訂單日誌查看功能正在開發中")
