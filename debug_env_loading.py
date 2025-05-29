#!/usr/bin/env python3
"""
調試環境變數載入問題
"""
import os
import sys

def debug_environment():
    """調試環境變數"""
    print("=== 環境變數調試 ===")
    print(f"當前工作目錄: {os.getcwd()}")
    print(f"Python路徑: {sys.executable}")
    print()
    
    # 檢查.env文件是否存在
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ .env文件存在: {os.path.abspath(env_file)}")
        
        # 讀取.env文件內容
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 檢查API密鑰行
        for line_num, line in enumerate(content.split('\n'), 1):
            if 'GOOGLE_API_KEY=' in line and not line.strip().startswith('#'):
                print(f"第{line_num}行: {line}")
                api_key = line.split('=', 1)[1] if '=' in line else ''
                print(f"提取的API密鑰: {api_key[:10]}..." if api_key else "空值")
                break
    else:
        print(f"❌ .env文件不存在: {os.path.abspath(env_file)}")
    
    print()
    
    # 測試不同的載入方式
    print("=== 測試環境變數載入 ===")
    
    # 方式1: 直接讀取
    print("1. 直接讀取os.environ:")
    direct_key = os.environ.get('GOOGLE_API_KEY', '')
    print(f"   結果: {direct_key[:10]}..." if direct_key else "   結果: 空值")
    
    # 方式2: 使用dotenv
    try:
        from dotenv import load_dotenv
        print("2. 使用dotenv載入:")
        load_dotenv()
        dotenv_key = os.environ.get('GOOGLE_API_KEY', '')
        print(f"   結果: {dotenv_key[:10]}..." if dotenv_key else "   結果: 空值")
    except ImportError:
        print("2. dotenv未安裝")
    
    # 方式3: 強制重新載入
    try:
        from dotenv import load_dotenv
        print("3. 強制重新載入dotenv:")
        load_dotenv(override=True)
        reload_key = os.environ.get('GOOGLE_API_KEY', '')
        print(f"   結果: {reload_key[:10]}..." if reload_key else "   結果: 空值")
    except ImportError:
        print("3. dotenv未安裝")
    
    # 方式4: 手動解析.env文件
    print("4. 手動解析.env文件:")
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GOOGLE_API_KEY=') and not line.startswith('#'):
                    manual_key = line.split('=', 1)[1]
                    print(f"   結果: {manual_key[:10]}..." if manual_key else "   結果: 空值")
                    break
            else:
                print("   結果: 未找到GOOGLE_API_KEY行")
    else:
        print("   結果: .env文件不存在")

def test_gui_simulation():
    """模擬GUI中的邏輯"""
    print("\n=== 模擬GUI邏輯 ===")
    
    # 模擬用戶輸入
    user_api_key = ""  # 空值，模擬用戶沒有輸入
    user_project_id = ""
    
    print(f"用戶輸入API密鑰: '{user_api_key}'")
    print(f"用戶輸入專案ID: '{user_project_id}'")
    
    # 模擬GUI中的檢查邏輯
    api_key = user_api_key.strip()
    project_id = user_project_id.strip()
    
    # 檢查是否使用測試模式
    if api_key.lower() == "test":
        print("🧪 使用測試模式")
        api_key = "test"
    # 檢查是否有有效的配置
    elif not api_key and not project_id:
        print("⚠️ 用戶未輸入配置，嘗試從環境變數讀取...")
        
        # 如果沒有API密鑰，嘗試從環境變數讀取
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("GOOGLE_API_KEY", "")
            if api_key:
                print(f"✅ 從環境變數讀取到API密鑰: {api_key[:10]}...")
            else:
                print("❌ 環境變數中未找到API密鑰")
        
        # 如果沒有專案ID，嘗試從環境變數讀取
        if not project_id:
            from dotenv import load_dotenv
            load_dotenv()
            project_id = os.environ.get("GOOGLE_PROJECT_ID", "")
            if project_id and project_id != "your_google_cloud_project_id_here":
                print(f"✅ 從環境變數讀取到專案ID: {project_id}")
            else:
                print("❌ 環境變數中未找到有效的專案ID")
    
    # 最終檢查
    print(f"\n最終配置:")
    print(f"API密鑰: {'有' if api_key else '無'}")
    print(f"專案ID: {'有' if project_id else '無'}")
    
    if not api_key and not project_id:
        print("❌ 配置缺失！")
        return False
    else:
        print("✅ 配置有效！")
        return True

def main():
    """主函數"""
    debug_environment()
    success = test_gui_simulation()
    
    print("\n" + "="*50)
    if success:
        print("🎉 環境變數載入測試成功！")
        print("\n建議:")
        print("1. 在GUI中將API密鑰欄位留空")
        print("2. 或者輸入 'test' 使用測試模式")
    else:
        print("❌ 環境變數載入測試失敗！")
        print("\n建議:")
        print("1. 檢查.env文件是否存在且格式正確")
        print("2. 嘗試在GUI中手動輸入API密鑰")
        print("3. 或者輸入 'test' 使用測試模式")

if __name__ == "__main__":
    main()
