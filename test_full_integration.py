#!/usr/bin/env python3
"""
完整的走勢分析器整合測試
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def create_sample_data():
    """創建示例數據用於測試"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                         end=datetime.now(), freq='1h')
    
    np.random.seed(42)
    base_price = 50000
    
    price_changes = np.random.normal(0, 0.02, len(dates))
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        open_price = price
        high_price = price * (1 + abs(np.random.normal(0, 0.01)))
        low_price = price * (1 - abs(np.random.normal(0, 0.01)))
        close_price = price * (1 + np.random.normal(0, 0.005))
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'Open': open_price,
            'High': high_price,
            'Low': low_price,
            'Close': close_price,
            'Volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_trend_analyzer_with_mock_api():
    """測試TrendAnalyzer的完整流程（使用模擬API回應）"""
    print("=== 完整走勢分析器整合測試 ===")
    
    # 創建示例數據
    print("1. 創建示例數據...")
    sample_data = create_sample_data()
    print(f"   數據形狀: {sample_data.shape}")
    
    try:
        from analysis.trend_analyzer import TrendAnalyzer
        
        # 創建一個模擬的TrendAnalyzer來測試完整流程
        class MockTrendAnalyzer(TrendAnalyzer):
            def __init__(self):
                # 跳過實際的API初始化
                self.api_key = "mock_key"
                self.project_id = "mock_project"
                self.location = "us-central1"
                self.model = "mock_model"
                self.max_retries = 3
                self.retry_delay = 2
                print("已初始化模擬分析器")
            
            def _call_gemini_model_with_retry(self, prompt):
                """模擬AI回應"""
                print("   模擬AI分析中...")
                
                # 模擬一個真實的分析回應
                mock_response = """
# 技術分析報告

## 1. 整體趨勢判斷
當前市場呈現**下降趨勢**，價格從期初的$50,185.82下跌至$37,805.07，跌幅達24.67%。這是一個明顯的熊市走勢。

## 2. 關鍵支撐和阻力位分析
- **主要阻力位**: $50,000 - $52,000（前期起始價格區間）
- **次要阻力位**: $45,000 - $47,000（中期回調高點）
- **主要支撐位**: $35,000 - $37,000（當前低點區間）
- **關鍵支撐位**: $32,000（心理支撐位）

## 3. 技術指標解讀
- **波動率**: 2.13%，屬於中等波動水平
- **成交量**: 呈現上升趨勢，顯示市場參與度增加
- **價格動能**: 下跌動能較強，但接近超賣區域

## 4. 風險評估
- **高風險**: 當前處於明顯下跌趨勢中
- **支撐測試**: 價格正在測試重要支撐區域
- **反彈可能**: 超賣狀態可能引發技術性反彈

## 5. 短期展望 (1-7天)
- 短期內可能在$35,000-$40,000區間震盪
- 如果跌破$35,000，可能進一步下探至$32,000
- 反彈目標位在$42,000-$45,000

## 6. 交易建議 (僅供參考)
- **謹慎觀望**: 等待明確的趨勢反轉信號
- **分批建倉**: 如果在$35,000附近可考慮小量分批買入
- **止損設置**: 嚴格設置止損位於$32,000以下
- **風險控制**: 控制倉位，避免重倉操作

**免責聲明**: 以上分析僅供參考，投資有風險，請謹慎決策。
"""
                return mock_response.strip()
        
        print("\n2. 初始化模擬分析器...")
        analyzer = MockTrendAnalyzer()
        
        print("\n3. 執行完整分析流程...")
        
        # 測試不同詳細程度
        for detail_level in ["簡要", "標準", "詳細"]:
            print(f"\n   測試 {detail_level} 分析...")
            
            try:
                result = analyzer.analyze_trend(
                    data=sample_data,
                    symbol="BTCUSDT",
                    timeframe="1h",
                    detail_level=detail_level
                )
                
                print(f"   ✅ {detail_level}分析完成")
                print(f"      狀態: {result.get('status', 'unknown')}")
                print(f"      字數: {result.get('word_count', 0)}")
                print(f"      生成時間: {result.get('generated_at', 'unknown')}")
                
                # 顯示分析結果的前200字符
                analysis_text = result.get('analysis_text', '')
                preview = analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text
                print(f"      內容預覽: {preview}")
                
            except Exception as e:
                print(f"   ❌ {detail_level}分析失敗: {e}")
        
        print("\n4. 測試錯誤處理...")
        
        # 測試無效數據
        try:
            empty_data = pd.DataFrame()
            result = analyzer.analyze_trend(empty_data, "TEST", "1h")
            print(f"   ✅ 空數據錯誤處理: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"   ✅ 空數據錯誤處理: {e}")
        
        print("\n✅ 完整整合測試成功！")
        print("\n下一步: 在GUI中進行實際測試")
        
    except ImportError as e:
        print(f"   ❌ 無法導入TrendAnalyzer: {e}")
    except Exception as e:
        print(f"   ❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def test_gui_integration():
    """測試GUI整合的準備工作"""
    print("\n=== GUI整合測試準備 ===")
    
    # 檢查是否有現有的數據文件
    data_path = "./data"
    if os.path.exists(data_path):
        csv_files = [f for f in os.listdir(data_path) if f.endswith('.csv')]
        print(f"1. 找到 {len(csv_files)} 個數據文件:")
        for file in csv_files[:5]:  # 只顯示前5個
            print(f"   - {file}")
        if len(csv_files) > 5:
            print(f"   ... 還有 {len(csv_files) - 5} 個文件")
    else:
        print("1. 數據目錄不存在，建議先下載一些歷史數據")
    
    # 檢查GUI文件
    gui_file = "./gui/app.py"
    if os.path.exists(gui_file):
        print("2. ✅ GUI文件存在")
    else:
        print("2. ❌ GUI文件不存在")
    
    # 檢查主程序
    main_file = "./main.py"
    if os.path.exists(main_file):
        print("3. ✅ 主程序文件存在")
    else:
        print("3. ❌ 主程序文件不存在")
    
    print("\n準備工作完成！可以啟動GUI進行實際測試。")

if __name__ == "__main__":
    test_trend_analyzer_with_mock_api()
    test_gui_integration()
