#!/usr/bin/env python3
"""
測試結果展示功能
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

def test_result_window():
    """測試結果展示窗口"""
    
    # 創建模擬的分析結果
    mock_analysis_result = {
        "analysis_text": """# BTCUSDT 技術分析報告

## 📊 整體趨勢判斷
基於當前數據分析，BTCUSDT 在 1h 時間框架下呈現**震盪整理**的走勢特徵。價格在關鍵支撐和阻力位之間波動，市場情緒相對中性。

## 🎯 關鍵支撐和阻力位分析
- **主要阻力位**: $52,000 - $54,000（前期高點區域）
- **次要阻力位**: $50,000 - $51,000（心理阻力位）
- **主要支撐位**: $48,000 - $49,000（重要技術支撐）  
- **關鍵支撐位**: $45,000（強力支撐位）

## 📈 技術指標解讀
- **移動平均線**: 短期均線與長期均線呈現交織狀態，顯示趨勢不明確
- **相對強弱指數(RSI)**: 當前RSI為55.2，處於中性區域，無明顯超買超賣信號
- **成交量**: 成交量呈現溫和放大趨勢，顯示市場參與度逐步提升
- **波動率**: 當前波動率為2.13%，處於正常範圍內

## ⚠️ 風險評估
- **市場風險**: 當前市場處於不確定狀態，需要密切關注突破方向
- **技術風險**: 關鍵支撐位破位可能引發進一步下跌
- **流動性風險**: 注意成交量變化對價格的影響
- **宏觀風險**: 關注全球經濟環境對加密貨幣市場的影響

## 🔮 短期展望 (1-7天)
短期內預計價格將在$48,000-$52,000區間內震盪，等待明確的方向性突破。投資者應關注：
- 關鍵技術位的突破情況
- 成交量的配合程度
- 市場整體情緒變化
- 重要經濟數據發布

## 💡 交易建議 (僅供參考)
- **謹慎觀望**: 等待明確的趨勢信號出現
- **分批操作**: 如有操作需求，建議分批進行，控制風險
- **嚴格止損**: 設置合理的止損位，保護資金安全
- **關注突破**: 密切關注關鍵位的突破情況，及時調整策略

---
**⚠️ 重要提醒**: 
- 本分析僅供參考，不構成投資建議
- 投資有風險，決策需謹慎
- 建議結合多種分析方法進行判斷
- 請根據自身風險承受能力進行投資

**📝 分析說明**: 這是一個完整的技術分析報告，展示了走勢分析功能的完整輸出格式。""",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "status": "success",
        "word_count": 456
    }
    
    # 創建主窗口
    root = tk.Tk()
    root.title("結果展示功能測試")
    root.geometry("400x300")
    
    # 創建測試按鈕
    def show_result_window():
        """顯示結果窗口"""
        # 創建新窗口
        result_window = tk.Toplevel(root)
        result_window.title(f"走勢分析報告 - {mock_analysis_result.get('symbol', '未知')} {mock_analysis_result.get('timeframe', '')}")
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
分析時間: {mock_analysis_result.get('generated_at', '未知')}
交易對: {mock_analysis_result.get('symbol', '未知')}
時間框架: {mock_analysis_result.get('timeframe', '未知')}
分析狀態: {mock_analysis_result.get('status', '未知')}
分析字數: {mock_analysis_result.get('word_count', 0)} 字
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
        analysis_text = mock_analysis_result.get('analysis_text', '無分析結果')
        result_text.insert(tk.END, analysis_text)
        result_text.config(state=tk.DISABLED)  # 設為只讀
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 保存按鈕
        def save_report():
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                title="保存走勢分析報告",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(analysis_text)
                print(f"報告已保存至: {file_path}")
        
        save_button = ttk.Button(button_frame, text="保存報告", command=save_report)
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 複製按鈕
        def copy_to_clipboard():
            root.clipboard_clear()
            root.clipboard_append(analysis_text)
            root.update()
            print("分析結果已複製到剪貼板")
        
        copy_button = ttk.Button(button_frame, text="複製到剪貼板", command=copy_to_clipboard)
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 關閉按鈕
        close_button = ttk.Button(button_frame, text="關閉", command=result_window.destroy)
        close_button.pack(side=tk.RIGHT)
        
        # 設置焦點
        result_window.focus_set()
    
    # 創建測試界面
    ttk.Label(root, text="結果展示功能測試", font=('Arial', 16, 'bold')).pack(pady=20)
    
    ttk.Button(root, text="顯示分析結果窗口", command=show_result_window).pack(pady=10)
    
    ttk.Label(root, text="這個測試展示了新的結果展示窗口功能", 
              font=('Arial', 10)).pack(pady=10)
    
    # 運行測試
    root.mainloop()

if __name__ == "__main__":
    test_result_window()
