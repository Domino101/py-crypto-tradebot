# gui/trend_analysis_ui.py
"""
走勢分析UI管理器 - 專門處理N8N工作流分析界面
"""

import tkinter as tk
from tkinter import ttk
import threading
from .base_ui import BaseUIComponent

class TrendAnalysisUI(BaseUIComponent):
    """走勢分析UI管理器 - 100%移植N8N工作流"""

    def __init__(self, base_manager):
        super().__init__(base_manager)
        self.trend_analysis_results = None

    def show_ui(self, parent_frame):
        """顯示N8N工作流分析UI"""
        # 創建主框架
        self.main_frame = ttk.Frame(parent_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 設置N8N工作流UI
        self._setup_n8n_workflow_ui()

    def _setup_n8n_workflow_ui(self):
        """設置N8N工作流UI - 完全按照原始邏輯"""
        # 標題說明
        title_label = ttk.Label(self.main_frame,
                               text="🚀 專業級加密貨幣分析系統 (基於N8N工作流)",
                               font=('Microsoft JhengHei', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, padx=5, pady=10, sticky='w')

        # 說明文字
        desc_label = ttk.Label(self.main_frame,
                              text="輸入幣種名稱，系統將自動獲取多時間框架數據並進行專業分析",
                              font=('Microsoft JhengHei', 9), foreground='gray')
        desc_label.grid(row=1, column=0, columnspan=3, padx=5, pady=(0, 15), sticky='w')

        # 幣種輸入 (核心功能)
        symbol_frame = ttk.LabelFrame(self.main_frame, text="交易對設置")
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
        api_frame = ttk.LabelFrame(self.main_frame, text="API設置 (可選)")
        api_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky='ew')

        ttk.Label(api_frame, text="Google API 密鑰:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.google_api_key_entry = ttk.Entry(api_frame, width=40, show="*")
        self.google_api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        ttk.Label(api_frame, text="留空使用環境變數，或輸入 'test' 使用測試模式",
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=2, padx=10, pady=2, sticky='w')

        # 分析選項
        options_frame = ttk.LabelFrame(self.main_frame, text="分析選項")
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
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=15, sticky='ew')

        self.start_analysis_button = ttk.Button(button_frame, text="🚀 開始專業分析",
                                               command=self.start_trend_analysis)
        self.start_analysis_button.pack(side=tk.LEFT, padx=(0, 10))

        # 查看詳細分析按鈕
        self.view_analysis_button = ttk.Button(button_frame, text="📊 查看詳細分析",
                                              command=self.view_detailed_analysis, state=tk.DISABLED)
        self.view_analysis_button.pack(side=tk.LEFT)

        # 結果顯示區域
        result_frame = ttk.LabelFrame(self.main_frame, text="分析結果")
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
        self.main_frame.columnconfigure(1, weight=1)
        symbol_frame.columnconfigure(1, weight=1)
        api_frame.columnconfigure(1, weight=1)

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
                self.append_trend_result(f"✅ 使用完整交易對: {final_symbol}")
            elif symbol_input:
                # 如果用戶只輸入了幣種名稱，自動轉換為USDT交易對
                final_symbol = f"{symbol_input}USDT"
                self.append_trend_result(f"✅ 自動轉換交易對: {symbol_input} → {final_symbol}")
            else:
                self.show_message("warning", "輸入缺失", "請輸入幣種名稱或完整交易對")
                return

            # 檢查Google API設置
            api_key = self.google_api_key_entry.get().strip()

            # 檢查是否使用測試模式
            if api_key.lower() == "test":
                self.append_trend_result("🧪 使用測試模式進行分析")
                api_key = "test"
            else:
                # 如果沒有API密鑰，嘗試從環境變數讀取
                if not api_key:
                    import os
                    try:
                        from dotenv import load_dotenv
                        load_dotenv()
                    except ImportError:
                        print("dotenv 模塊未安裝，跳過 .env 文件加載")

                    api_key = os.environ.get("GOOGLE_API_KEY", "")
                    if api_key:
                        self.append_trend_result(f"✅ 使用環境變數中的API密鑰: {api_key[:10]}...")
                    else:
                        self.append_trend_result("❌ 未找到API密鑰")

            # 檢查是否有有效的配置
            if not api_key:
                self.append_trend_result("❌ 未找到任何有效的Google AI配置")
                self.append_trend_result("請檢查以下選項：")
                self.append_trend_result("1. 在API密鑰欄位輸入您的Google API密鑰")
                self.append_trend_result("2. 或者輸入 'test' 使用測試模式")
                self.append_trend_result("3. 或者確認.env文件中的GOOGLE_API_KEY設置正確")
                self.show_message("warning", "配置缺失",
                                "未找到Google AI配置。\n\n請：\n1. 輸入API密鑰，或\n2. 輸入 'test' 使用測試模式，或\n3. 檢查.env文件配置")
                return

            # 獲取分析詳細程度
            detail_level = self.analysis_detail_var.get()

            # 清除結果並開始分析
            self.clear_trend_results()
            self.append_trend_result("🚀 開始N8N工作流分析")
            self.append_trend_result(f"交易對: {final_symbol}")
            self.append_trend_result(f"分析詳細程度: {detail_level}")
            self.append_trend_result("自動獲取多時間框架數據: 15m, 1h, 1d")
            self.append_trend_result("-" * 40)
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
        """N8N工作流分析執行線程"""
        try:
            import sys
            import os

            # 確保項目根目錄在路徑中
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from analysis.trend_analyzer import TrendAnalyzer

            self.set_status("初始化N8N工作流分析器...")
            analyzer = TrendAnalyzer(api_key=api_key)

            self.set_status("正在執行N8N工作流分析...")
            self.append_trend_result("正在調用Google Gemini AI進行專業分析...")

            # 執行N8N工作流分析
            analysis_result = analyzer.analyze_trend(
                data=None,  # N8N工作流會自動獲取數據
                symbol=symbol,
                timeframe="多時間框架",
                detail_level=detail_level
            )

            # 儲存結果
            self.trend_analysis_results = analysis_result

            # 顯示結果
            self.append_trend_result("--- N8N工作流分析結果 ---")
            self.append_trend_result(f"分析時間: {analysis_result['generated_at']}")
            self.append_trend_result(f"分析狀態: {analysis_result.get('status', '未知')}")
            if 'word_count' in analysis_result:
                self.append_trend_result(f"分析字數: {analysis_result['word_count']} 字")
            self.append_trend_result("-" * 40)

            # 在主結果區域顯示簡要信息
            preview_text = analysis_result['analysis_text'][:200] + "..." if len(analysis_result['analysis_text']) > 200 else analysis_result['analysis_text']
            self.append_trend_result(f"分析預覽: {preview_text}")
            self.append_trend_result("-" * 40)
            self.append_trend_result("✅ 專業分析完成！點擊 '查看詳細分析' 按鈕查看完整報告")

            # 啟用查看詳細分析按鈕
            self.view_analysis_button.config(state=tk.NORMAL)

            self.set_status("N8N工作流分析完成")

        except Exception as e:
            self.append_trend_result(f"分析過程中發生錯誤: {str(e)}")
            self.set_status("N8N工作流分析失敗")
            import traceback
            traceback.print_exc()
        finally:
            # 重新啟用控件
            if hasattr(self, 'start_analysis_button'):
                self.start_analysis_button.config(state=tk.NORMAL)

    def view_detailed_analysis(self):
        """查看詳細分析結果"""
        if not self.trend_analysis_results:
            self.show_message("warning", "無分析結果", "請先進行走勢分析")
            return

        # 創建詳細分析窗口
        self._show_detailed_analysis_window(self.trend_analysis_results)

    def _show_detailed_analysis_window(self, analysis_result):
        """顯示詳細分析窗口"""
        detail_window = tk.Toplevel(self.main_frame)
        detail_window.title("詳細走勢分析報告")
        detail_window.geometry("800x600")

        # 創建文本框和滾動條
        text_frame = ttk.Frame(detail_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Microsoft JhengHei', 10))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        # 插入分析結果
        text_widget.insert(tk.END, analysis_result['analysis_text'])
        text_widget.config(state=tk.DISABLED)

    def append_trend_result(self, text: str):
        """添加走勢分析結果"""
        self.trend_result_text.insert(tk.END, text + "\n")
        self.trend_result_text.see(tk.END)

    def clear_trend_results(self):
        """清除走勢分析結果"""
        self.trend_result_text.delete(1.0, tk.END)
