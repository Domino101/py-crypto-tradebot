#!/usr/bin/env python3
"""
Google AI 配置測試腳本
"""
import os
from dotenv import load_dotenv

def test_google_ai_config():
    """測試Google AI配置"""
    print("=== Google AI 配置測試 ===\n")

    # 載入環境變數
    load_dotenv()

    # 檢查環境變數
    print("1. 檢查環境變數...")
    api_key = os.getenv('GOOGLE_API_KEY')
    project_id = os.getenv('GOOGLE_PROJECT_ID')
    location = os.getenv('GOOGLE_LOCATION', 'us-central1')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    print(f"   GOOGLE_API_KEY: {'✅ 已設置' if api_key and api_key != 'your_google_api_key_here' else '❌ 未設置或使用預設值'}")
    print(f"   GOOGLE_PROJECT_ID: {'✅ 已設置' if project_id and project_id != 'your_google_cloud_project_id_here' else '❌ 未設置或使用預設值'}")
    print(f"   GOOGLE_LOCATION: {location}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {'✅ 已設置' if credentials_path else '❌ 未設置'}")

    # 檢查依賴
    print("\n2. 檢查依賴套件...")
    try:
        import google.generativeai as genai
        print("   ✅ google-generativeai 已安裝")
        genai_available = True
    except ImportError:
        print("   ❌ google-generativeai 未安裝")
        genai_available = False

    try:
        from google.cloud import aiplatform
        print("   ✅ google-cloud-aiplatform 已安裝")
        vertex_available = True
    except ImportError:
        print("   ❌ google-cloud-aiplatform 未安裝")
        vertex_available = False

    # 測試方式1：Google Generative AI
    print("\n3. 測試 Google Generative AI...")
    if genai_available and api_key and api_key != 'your_google_api_key_here':
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            print("   正在測試API連接...")
            response = model.generate_content("請用繁體中文回答：你好，這是一個測試。")

            if response and response.text:
                print("   ✅ Google Generative AI 連接成功！")
                print(f"   回應: {response.text[:100]}...")
                return True
            else:
                print("   ❌ API回應為空")
        except Exception as e:
            print(f"   ❌ Google Generative AI 測試失敗: {e}")
            if "API_KEY_INVALID" in str(e):
                print("   提示: API密鑰可能無效，請檢查是否正確設置")
            elif "QUOTA_EXCEEDED" in str(e):
                print("   提示: API配額已用盡，請檢查使用限制")
    else:
        if not genai_available:
            print("   ⏭️ 跳過測試 - google-generativeai 未安裝")
        else:
            print("   ⏭️ 跳過測試 - API密鑰未設置")

    # 測試方式2：Vertex AI
    print("\n4. 測試 Vertex AI...")
    if vertex_available and project_id and project_id != 'your_google_cloud_project_id_here':
        try:
            # 設置認證
            if credentials_path and os.path.exists(credentials_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                print(f"   使用服務帳號金鑰: {credentials_path}")

            aiplatform.init(project=project_id, location=location)
            print("   ✅ Vertex AI 初始化成功！")

            # 嘗試創建模型實例
            model = aiplatform.GenerativeModel("gemini-pro")
            print("   ✅ Vertex AI 模型創建成功！")
            return True

        except Exception as e:
            print(f"   ❌ Vertex AI 測試失敗: {e}")
            if "permission" in str(e).lower():
                print("   提示: 權限問題，請檢查服務帳號權限")
            elif "project" in str(e).lower():
                print("   提示: 專案問題，請檢查專案ID是否正確")
    else:
        if not vertex_available:
            print("   ⏭️ 跳過測試 - google-cloud-aiplatform 未安裝")
        else:
            print("   ⏭️ 跳過測試 - 專案ID未設置")

    # 測試TrendAnalyzer
    print("\n5. 測試 TrendAnalyzer 整合...")
    try:
        from analysis.trend_analyzer import TrendAnalyzer

        # 測試初始化
        if api_key and api_key != 'your_google_api_key_here':
            analyzer = TrendAnalyzer(api_key=api_key)
            print("   ✅ TrendAnalyzer 初始化成功 (使用API密鑰)")
        elif project_id and project_id != 'your_google_cloud_project_id_here':
            analyzer = TrendAnalyzer(project_id=project_id)
            print("   ✅ TrendAnalyzer 初始化成功 (使用專案ID)")
        else:
            print("   ⏭️ 跳過測試 - 無有效配置")
            return False

        return True

    except Exception as e:
        print(f"   ❌ TrendAnalyzer 測試失敗: {e}")

    return False

def show_configuration_guide():
    """顯示配置指南"""
    print("\n" + "="*60)
    print("📋 配置指南")
    print("="*60)
    print()
    print("如果測試失敗，請按照以下步驟配置：")
    print()
    print("🌟 推薦方式：Google Generative AI")
    print("1. 前往 https://aistudio.google.com/app/apikey")
    print("2. 登入您的Google帳號")
    print("3. 點擊 'Create API Key'")
    print("4. 複製生成的API密鑰")
    print("5. 在 .env 文件中設置：")
    print("   GOOGLE_API_KEY=您的實際API密鑰")
    print()
    print("🔧 進階方式：Vertex AI")
    print("1. 前往 https://console.cloud.google.com/")
    print("2. 創建新的Google Cloud專案")
    print("3. 啟用 Vertex AI API")
    print("4. 設置計費帳戶")
    print("5. 在 .env 文件中設置：")
    print("   GOOGLE_PROJECT_ID=您的專案ID")
    print()
    print("📖 詳細說明請參考：Google_AI_配置指南.md")
    print()

def main():
    """主函數"""
    success = test_google_ai_config()

    if success:
        print("\n🎉 配置測試成功！")
        print("您現在可以使用Google AI進行走勢分析了。")
        print()
        print("下一步：")
        print("1. 啟動應用程式：python main.py")
        print("2. 切換到 '走勢分析' 模式")
        print("3. 輸入您的API密鑰（或使用環境變數）")
        print("4. 開始分析！")
    else:
        print("\n❌ 配置測試失敗")
        show_configuration_guide()

if __name__ == "__main__":
    main()
