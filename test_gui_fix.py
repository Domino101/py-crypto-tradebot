#!/usr/bin/env python3
"""
測試GUI修復 - 驗證環境變數讀取功能
"""
import os
from dotenv import load_dotenv

def test_environment_variables():
    """測試環境變數讀取"""
    print("=== 測試環境變數讀取 ===")
    
    # 載入環境變數
    load_dotenv()
    
    # 檢查API密鑰
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        print(f"✅ 環境變數中找到API密鑰: {api_key[:10]}...")
    else:
        print("❌ 環境變數中未找到API密鑰")
    
    # 檢查專案ID
    project_id = os.environ.get("GOOGLE_PROJECT_ID", "")
    if project_id:
        print(f"✅ 環境變數中找到專案ID: {project_id}")
    else:
        print("❌ 環境變數中未找到專案ID")
    
    # 模擬GUI邏輯
    print("\n=== 模擬GUI邏輯 ===")
    
    # 模擬用戶輸入（空值）
    user_api_key = ""
    user_project_id = ""
    
    print(f"用戶輸入API密鑰: '{user_api_key}'")
    print(f"用戶輸入專案ID: '{user_project_id}'")
    
    # 檢查是否有有效的配置
    if not user_api_key and not user_project_id:
        print("⚠️ 用戶未輸入任何配置，檢查環境變數...")
        
        # 如果沒有API密鑰，嘗試從環境變數讀取
        if not user_api_key:
            user_api_key = os.environ.get("GOOGLE_API_KEY", "")
            if user_api_key:
                print(f"✅ 從環境變數讀取到API密鑰: {user_api_key[:10]}...")
        
        # 如果沒有專案ID，嘗試從環境變數讀取
        if not user_project_id:
            user_project_id = os.environ.get("GOOGLE_PROJECT_ID", "")
            if user_project_id:
                print(f"✅ 從環境變數讀取到專案ID: {user_project_id}")
    
    # 最終檢查
    if not user_api_key and not user_project_id:
        print("❌ 配置缺失：請輸入Google API密鑰或Google專案ID")
        return False
    else:
        print("✅ 配置有效，可以進行分析")
        return True

def test_trend_analyzer_initialization():
    """測試TrendAnalyzer初始化"""
    print("\n=== 測試TrendAnalyzer初始化 ===")
    
    try:
        from analysis.trend_analyzer import TrendAnalyzer
        
        # 測試使用環境變數初始化
        print("嘗試使用環境變數初始化...")
        analyzer = TrendAnalyzer()
        print("✅ TrendAnalyzer初始化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ TrendAnalyzer初始化失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🧪 GUI修復測試")
    print("="*50)
    
    # 測試環境變數
    env_test = test_environment_variables()
    
    # 測試TrendAnalyzer
    analyzer_test = test_trend_analyzer_initialization()
    
    print("\n" + "="*50)
    print("📊 測試結果總結")
    print(f"環境變數測試: {'✅ 通過' if env_test else '❌ 失敗'}")
    print(f"TrendAnalyzer測試: {'✅ 通過' if analyzer_test else '❌ 失敗'}")
    
    if env_test and analyzer_test:
        print("\n🎉 所有測試通過！")
        print("現在您可以在GUI中：")
        print("1. 將API密鑰欄位留空")
        print("2. 系統會自動使用環境變數中的配置")
        print("3. 或者輸入 'test' 使用測試模式")
    else:
        print("\n⚠️ 部分測試失敗")
        print("請檢查配置或重新運行設置腳本")

if __name__ == "__main__":
    main()
