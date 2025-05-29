#!/usr/bin/env python3
"""
Google AI 快速配置助手
"""
import os
import re

def setup_google_ai():
    """Google AI 快速配置助手"""
    print("🚀 Google AI 快速配置助手")
    print("="*50)
    print()

    # 檢查當前配置
    env_file = ".env"
    if not os.path.exists(env_file):
        print("❌ 找不到 .env 文件")
        return

    # 讀取當前 .env 文件
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("📋 當前配置狀態:")
    if "GOOGLE_API_KEY=" in content:
        current_key = ""
        for line in content.split('\n'):
            if line.startswith('GOOGLE_API_KEY='):
                current_key = line.split('=', 1)[1]
                break

        if current_key and current_key != "your_google_api_key_here":
            print(f"   ✅ API密鑰已設置: {current_key[:10]}...")

            # 詢問是否要更新
            update = input("\n是否要更新API密鑰？(y/N): ").strip().lower()
            if update not in ['y', 'yes', '是']:
                print("保持現有配置。")
                return
        else:
            print("   ❌ API密鑰未設置")

    print()
    print("🌟 設置 Google Generative AI (推薦)")
    print("1. 我已經為您打開了 Google AI Studio 網頁")
    print("2. 請在瀏覽器中完成以下步驟：")
    print("   - 登入您的Google帳號")
    print("   - 點擊 'Create API Key' 按鈕")
    print("   - 複製生成的API密鑰")
    print()

    # 獲取API密鑰
    while True:
        api_key = input("請貼上您的Google API密鑰 (或輸入 'skip' 跳過): ").strip()

        if api_key.lower() == 'skip':
            print("跳過API密鑰設置。")
            return

        if not api_key:
            print("❌ API密鑰不能為空，請重新輸入。")
            continue

        # 驗證API密鑰格式
        if not api_key.startswith('AIza') or len(api_key) < 30:
            print("❌ API密鑰格式可能不正確。Google API密鑰通常以 'AIza' 開頭且長度較長。")
            retry = input("是否繼續使用此密鑰？(y/N): ").strip().lower()
            if retry not in ['y', 'yes', '是']:
                continue

        break

    # 更新 .env 文件
    print("\n📝 更新 .env 文件...")

    # 替換或添加API密鑰
    if "GOOGLE_API_KEY=" in content:
        # 替換現有的API密鑰
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('GOOGLE_API_KEY='):
                lines[i] = f"GOOGLE_API_KEY={api_key}"
                break
        content = '\n'.join(lines)
    else:
        # 添加新的API密鑰
        if not content.endswith('\n'):
            content += '\n'
        content += f"GOOGLE_API_KEY={api_key}\n"

    # 寫入文件
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ .env 文件更新成功！")
    except Exception as e:
        print(f"❌ 更新 .env 文件失敗: {e}")
        return

    # 測試配置
    print("\n🧪 測試配置...")
    test_success = test_api_key(api_key)

    if test_success:
        print("\n🎉 配置完成！")
        print("您現在可以使用Google AI進行走勢分析了。")
        print()
        print("下一步：")
        print("1. 啟動應用程式：python main.py")
        print("2. 切換到 '走勢分析' 模式")
        print("3. 開始分析！")
    else:
        print("\n⚠️ 配置完成，但API測試失敗")
        print("可能的原因：")
        print("- API密鑰無效")
        print("- 網路連接問題")
        print("- API配額限制")
        print()
        print("您仍然可以嘗試在應用程式中使用，或稍後重新測試。")

def test_api_key(api_key):
    """測試API密鑰"""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        print("   正在測試API連接...")
        response = model.generate_content("Hello")

        if response and response.text:
            print("   ✅ API測試成功！")
            return True
        else:
            print("   ❌ API回應為空")
            return False

    except Exception as e:
        print(f"   ❌ API測試失敗: {e}")
        return False

def main():
    """主函數"""
    try:
        setup_google_ai()
    except KeyboardInterrupt:
        print("\n\n操作已取消。")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")

if __name__ == "__main__":
    main()
