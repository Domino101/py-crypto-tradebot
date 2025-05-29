# gui/live_trading_ui.py
"""
實盤交易UI管理器 - 專門處理實盤交易相關界面
"""

import tkinter as tk
from tkinter import ttk
import threading
from .base_ui import BaseUIComponent

class LiveTradingUI(BaseUIComponent):
    """實盤交易UI管理器"""

    def __init__(self, base_manager):
        super().__init__(base_manager)
        self.live_trader_instance = None
        self.strategy_classes = {}
        self.current_param_widgets = {}

    def show_ui(self, parent_frame):
        """顯示實盤交易UI"""
        # 創建主框架
        self.main_frame = ttk.Frame(parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 設置實盤交易UI
        self._setup_live_trading_ui()

        # 加載策略
        self._load_strategies()

    def _setup_live_trading_ui(self):
        """設置實盤交易UI"""
        # 交易所設置
        exchange_frame = ttk.LabelFrame(self.main_frame, text="交易所設置")
        exchange_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        ttk.Label(exchange_frame, text="交易所:").pack(side=tk.LEFT, padx=(5, 5))
        self.exchange_combobox = ttk.Combobox(exchange_frame, values=["Alpaca"], state="readonly", width=15)
        self.exchange_combobox.set("Alpaca")
        self.exchange_combobox.pack(side=tk.LEFT, padx=(0, 5))

        # 策略選擇
        strategy_frame = ttk.LabelFrame(self.main_frame, text="策略選擇")
        strategy_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        ttk.Label(strategy_frame, text="選擇策略:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.strategy_combobox = ttk.Combobox(strategy_frame, state="readonly")
        self.strategy_combobox.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.strategy_combobox.bind("<<ComboboxSelected>>", self.on_strategy_selected)

        # 實盤參數框架
        params_frame = ttk.LabelFrame(self.main_frame, text="交易參數")
        params_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        # 基本參數
        basic_params_frame = ttk.Frame(params_frame)
        basic_params_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='nw')

        ttk.Label(basic_params_frame, text="交易對:").grid(row=0, column=0, padx=5, pady=3, sticky='w')
        self.live_symbol_entry = ttk.Entry(basic_params_frame, width=15)
        self.live_symbol_entry.grid(row=0, column=1, padx=5, pady=3, sticky='ew')
        self.live_symbol_entry.insert(0, "BTC/USD")  # Alpaca格式

        ttk.Label(basic_params_frame, text="交易數量:").grid(row=1, column=0, padx=5, pady=3, sticky='w')
        self.live_qty_entry = ttk.Entry(basic_params_frame, width=15)
        self.live_qty_entry.grid(row=1, column=1, padx=5, pady=3, sticky='ew')
        self.live_qty_entry.insert(0, "0.001")

        ttk.Label(basic_params_frame, text="時間框架:").grid(row=2, column=0, padx=5, pady=3, sticky='w')
        self.live_interval_combobox = ttk.Combobox(basic_params_frame, values=['1m', '5m', '15m', '30m', '1h', '4h', '1d'], state="readonly", width=13)
        self.live_interval_combobox.grid(row=2, column=1, padx=5, pady=3, sticky='ew')
        self.live_interval_combobox.set('1h')

        self.paper_trading_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(basic_params_frame, text="使用模擬盤", variable=self.paper_trading_var).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # 策略參數框架
        self.strategy_params_frame = ttk.Frame(params_frame)
        self.strategy_params_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # 交易狀態框架
        status_frame = ttk.LabelFrame(self.main_frame, text="交易狀態")
        status_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        # 創建狀態顯示控件
        ttk.Label(status_frame, text="帳戶餘額:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.balance_var = tk.StringVar(value="N/A")
        self.balance_label = ttk.Label(status_frame, textvariable=self.balance_var, anchor=tk.W)
        self.balance_label.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(status_frame, text="當前持倉:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.positions_var = tk.StringVar(value="N/A")
        self.positions_label = ttk.Label(status_frame, textvariable=self.positions_var, anchor=tk.W, wraplength=300)
        self.positions_label.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(status_frame, text="當前掛單:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.orders_var = tk.StringVar(value="N/A")
        self.orders_label = ttk.Label(status_frame, textvariable=self.orders_var, anchor=tk.W, wraplength=300)
        self.orders_label.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

        # 按鈕框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=10, sticky='ew')

        self.start_button = ttk.Button(button_frame, text="開始實盤", command=self.start_live_trading)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_live_trading)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(button_frame, text="清除結果", command=self.clear_results)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # 配置權重
        self.main_frame.columnconfigure(0, weight=1)
        strategy_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(1, weight=1)

    def _load_strategies(self):
        """加載實盤策略"""
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
                print(f"成功加載 {len(strategy_names)} 個實盤策略")
            else:
                print("未找到任何實盤策略")
        except Exception as e:
            error_msg = f"無法加載實盤策略: {str(e)}"
            print(f"實盤策略加載錯誤: {error_msg}")
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

    def start_live_trading(self):
        """開始實盤交易"""
        strategy_name = self.strategy_combobox.get()
        if not strategy_name:
            self.show_message("warning", "策略缺失", "請選擇策略")
            return

        symbol = self.live_symbol_entry.get().strip()
        if not symbol:
            self.show_message("warning", "交易對缺失", "請輸入交易對")
            return

        self.set_status("正在啟動實盤交易...")
        self.append_result("開始實盤交易...")

        # 這裡實現實盤交易邏輯
        # 暫時顯示啟動消息
        self.append_result("實盤交易已啟動！")
        self.set_status("實盤交易運行中")

        # 更新按鈕狀態
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_live_trading(self):
        """停止實盤交易"""
        self.set_status("正在停止實盤交易...")
        self.append_result("停止實盤交易...")

        # 這裡實現停止邏輯
        # 暫時顯示停止消息
        self.append_result("實盤交易已停止！")
        self.set_status("實盤交易已停止")

        # 更新按鈕狀態
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        # 重置狀態顯示
        self.balance_var.set("N/A")
        self.positions_var.set("N/A")
        self.orders_var.set("N/A")
