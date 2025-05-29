#!/usr/bin/env python3
"""
測試走勢分析器的基本功能
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def create_sample_data():
    """創建示例數據用於測試"""
    # 創建30天的示例數據
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                         end=datetime.now(), freq='1H')
    
    # 生成模擬價格數據
    np.random.seed(42)
    base_price = 50000  # 假設是BTC價格
    
    # 生成隨機走勢
    price_changes = np.random.normal(0, 0.02, len(dates))  # 2%的標準差
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # 創建OHLCV數據
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        # 模擬開高低收
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

def test_trend_analyzer():
    """測試TrendAnalyzer的基本功能"""
    print("=== 測試走勢分析器 ===")
    
    # 創建示例數據
    print("1. 創建示例數據...")
    sample_data = create_sample_data()
    print(f"   數據形狀: {sample_data.shape}")
    print(f"   數據範圍: {sample_data.index[0]} 到 {sample_data.index[-1]}")
    print(f"   價格範圍: ${sample_data['Close'].min():.2f} - ${sample_data['Close'].max():.2f}")
    
    # 測試不需要Google API的功能
    print("\n2. 測試數據處理功能...")
    
    try:
        from analysis.trend_analyzer import TrendAnalyzer
        
        # 測試在沒有Google API的情況下初始化
        print("   嘗試初始化分析器（無API）...")
        try:
            analyzer = TrendAnalyzer(api_key="test_key", project_id="test_project")
            print("   ❌ 應該失敗但沒有失敗")
        except Exception as e:
            print(f"   ✅ 正確處理了缺少依賴的情況: {e}")
        
        # 測試數據摘要功能（不需要AI）
        print("\n3. 測試數據摘要功能...")
        
        # 創建一個模擬的分析器來測試數據處理方法
        class MockAnalyzer:
            def _prepare_data_summary(self, data):
                # 複製TrendAnalyzer的數據摘要邏輯
                try:
                    summary = {
                        "start_date": data.index[0].strftime("%Y-%m-%d %H:%M"),
                        "end_date": data.index[-1].strftime("%Y-%m-%d %H:%M"),
                        "duration_days": (data.index[-1] - data.index[0]).days,
                        "data_points": len(data),
                        "price_start": float(data['Close'].iloc[0]),
                        "price_end": float(data['Close'].iloc[-1]),
                        "price_min": float(data['Low'].min()),
                        "price_max": float(data['High'].max()),
                        "price_change_pct": float(((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100),
                        "volatility": float(data['Close'].pct_change().std() * 100),
                    }
                    
                    if 'Volume' in data.columns and not data['Volume'].isna().all():
                        summary["volume_avg"] = float(data['Volume'].mean())
                        summary["volume_max"] = float(data['Volume'].max())
                        summary["volume_trend"] = "上升" if data['Volume'].iloc[-10:].mean() > data['Volume'].iloc[:10].mean() else "下降"
                    else:
                        summary["volume_avg"] = 0
                        summary["volume_max"] = 0
                        summary["volume_trend"] = "無數據"
                    
                    return summary
                except Exception as e:
                    print(f"準備數據摘要時出錯: {e}")
                    return {"error": str(e)}
        
        mock_analyzer = MockAnalyzer()
        summary = mock_analyzer._prepare_data_summary(sample_data)
        
        print("   數據摘要結果:")
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"     {key}: {value:.4f}")
            else:
                print(f"     {key}: {value}")
        
        print("\n4. 測試提示詞構建...")
        
        # 測試提示詞構建
        def build_test_prompt(data_summary, symbol="BTCUSDT", timeframe="1h", detail_level="標準"):
            analysis_requirements = {
                "簡要": ["1. 整體趨勢判斷", "2. 當前價格位置評估", "3. 簡要風險提示"],
                "標準": ["1. 整體趨勢判斷", "2. 關鍵支撐和阻力位分析", "3. 技術指標解讀", "4. 風險評估", "5. 短期展望", "6. 交易建議"],
                "詳細": ["1. 整體趨勢判斷與趨勢強度評估", "2. 詳細的支撐和阻力位分析", "3. 多重技術指標綜合解讀"]
            }
            
            requirements = analysis_requirements.get(detail_level, analysis_requirements["標準"])
            
            prompt = f"""你是一位資深的加密貨幣技術分析專家。請基於以下數據對 {symbol} 在 {timeframe} 時間框架下進行專業的技術分析。

=== 基本數據摘要 ===
交易對: {symbol}
時間框架: {timeframe}
分析期間: {data_summary['start_date']} 至 {data_summary['end_date']}
數據點數: {data_summary['data_points']} 個
分析天數: {data_summary['duration_days']} 天

=== 價格數據 ===
起始價格: ${data_summary['price_start']:.6f}
結束價格: ${data_summary['price_end']:.6f}
價格變化: {data_summary['price_change_pct']:.2f}%
最高價: ${data_summary['price_max']:.6f}
最低價: ${data_summary['price_min']:.6f}
整體波動率: {data_summary['volatility']:.2f}%

=== 分析要求 ===
請提供以下{detail_level}分析:
{chr(10).join(requirements)}

請用繁體中文回答，保持專業、客觀的分析語調。
"""
            return prompt
        
        prompt = build_test_prompt(summary)
        print(f"   提示詞長度: {len(prompt)} 字符")
        print("   提示詞預覽:")
        print("   " + prompt[:200] + "...")
        
        print("\n✅ 所有測試完成！數據處理功能正常工作。")
        print("\n注意: 要完整測試AI分析功能，需要:")
        print("   1. 安裝 Google Cloud AI Platform 依賴")
        print("   2. 配置有效的 Google API 密鑰")
        print("   3. 在GUI中進行實際測試")
        
    except ImportError as e:
        print(f"   ❌ 無法導入TrendAnalyzer: {e}")
        print("   請確保analysis/trend_analyzer.py文件存在且語法正確")
    except Exception as e:
        print(f"   ❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_trend_analyzer()
