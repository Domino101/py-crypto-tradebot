# gui/base_ui.py
"""
基礎UI管理器 - 負責主窗口和模式切換邏輯
"""

import tkinter as tk
from tkinter import ttk
import queue
from typing import Dict, Any

class BaseUIManager:
    """基礎UI管理器 - 處理主窗口和模式切換"""
    
    def __init__(self, master):
        self.master = master
        self.master.title("加密貨幣交易系統 (回測 / 實盤 / 走勢分析)")
        self.master.geometry("850x800")
        
        # 模式管理
        self.mode_var = tk.StringVar(value="backtest")
        self.current_mode = None
        
        # UI管理器字典
        self.ui_managers = {}
        
        # 通用組件
        self.gui_queue = queue.Queue()
        
        # 初始化主框架
        self._setup_main_layout()
        
    def _setup_main_layout(self):
        """設置主要布局框架"""
        # 模式選擇框架
        self.mode_frame = ttk.Frame(self.master)
        self.mode_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky='w')
        
        # 模式選擇按鈕
        ttk.Label(self.mode_frame, text="模式:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(self.mode_frame, text="回測", variable=self.mode_var, value="backtest").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.mode_frame, text="實盤交易", variable=self.mode_var, value="live").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.mode_frame, text="走勢分析", variable=self.mode_var, value="trend_analysis").pack(side=tk.LEFT, padx=5)
        
        # 主內容區域
        self.content_frame = ttk.Frame(self.master)
        self.content_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')
        
        # 結果框架
        self.results_frame = ttk.LabelFrame(self.master, text="結果 / 日誌")
        self.results_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='nsew')
        
        # 結果文本框
        self.result_text = tk.Text(self.results_frame, wrap=tk.WORD, height=8)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 狀態欄
        self.status_var = tk.StringVar(value="準備就緒")
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky='ew')
        
        # 配置權重
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=1)
        self.master.rowconfigure(2, weight=1)
        
        # 綁定模式切換事件
        self.mode_var.trace_add("write", lambda *_: self.on_mode_change())
        
    def register_ui_manager(self, mode: str, ui_manager):
        """註冊UI管理器"""
        self.ui_managers[mode] = ui_manager
        
    def on_mode_change(self):
        """處理模式切換"""
        new_mode = self.mode_var.get()
        
        if new_mode == self.current_mode:
            return
            
        print(f"\n=== 模式切換: {self.current_mode} -> {new_mode} ===")
        
        # 隱藏當前模式的UI
        if self.current_mode and self.current_mode in self.ui_managers:
            self.ui_managers[self.current_mode].hide_ui()
            
        # 清空內容框架
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # 顯示新模式的UI
        if new_mode in self.ui_managers:
            self.ui_managers[new_mode].show_ui(self.content_frame)
            
        self.current_mode = new_mode
        
        # 更新狀態
        mode_text = {"backtest": "回測", "live": "實盤交易", "trend_analysis": "走勢分析"}
        self.set_status(f"模式已切換至: {mode_text.get(new_mode, new_mode)}")
        
        print(f"=== 模式切換完成: {new_mode} ===\n")
        
        # 強制更新UI
        self.master.update_idletasks()
        
    def set_status(self, message: str):
        """設置狀態欄消息"""
        self.status_var.set(message)
        
    def append_result(self, text: str):
        """添加結果文本"""
        self.result_text.insert(tk.END, text + "\n")
        self.result_text.see(tk.END)
        
    def clear_results(self):
        """清除結果"""
        self.result_text.delete(1.0, tk.END)
        
    def show_message(self, level: str, title: str, message: str):
        """顯示消息框"""
        from tkinter import messagebox
        if level == "error":
            messagebox.showerror(title, message)
        elif level == "warning":
            messagebox.showwarning(title, message)
        elif level == "info":
            messagebox.showinfo(title, message)
            
    def process_gui_queue(self):
        """處理GUI更新隊列"""
        try:
            while True:
                action, data = self.gui_queue.get_nowait()
                
                if action == "update_status":
                    self.set_status(data)
                elif action == "result_append":
                    self.append_result(data)
                elif action == "result_clear":
                    self.clear_results()
                elif action == "show_message":
                    level, title, message = data
                    self.show_message(level, title, message)
                    
                self.gui_queue.task_done()
        except queue.Empty:
            pass
        finally:
            # 每100ms檢查一次隊列
            self.master.after(100, self.process_gui_queue)


class BaseUIComponent:
    """基礎UI組件類"""
    
    def __init__(self, base_manager: BaseUIManager):
        self.base_manager = base_manager
        self.main_frame = None
        
    def show_ui(self, parent_frame):
        """顯示UI - 子類必須實現"""
        raise NotImplementedError("子類必須實現 show_ui 方法")
        
    def hide_ui(self):
        """隱藏UI"""
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None
            
    def set_status(self, message: str):
        """設置狀態"""
        self.base_manager.set_status(message)
        
    def append_result(self, text: str):
        """添加結果"""
        self.base_manager.append_result(text)
        
    def clear_results(self):
        """清除結果"""
        self.base_manager.clear_results()
        
    def show_message(self, level: str, title: str, message: str):
        """顯示消息"""
        self.base_manager.show_message(level, title, message)
