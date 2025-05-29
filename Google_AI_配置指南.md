# 🚀 Google AI 配置指南

本指南將協助您配置Google AI服務，用於走勢分析功能。我們提供兩種配置方式，推薦使用方式1（更簡單）。

## 📋 配置選項

### 🌟 方式1：Google Generative AI (推薦)
- ✅ **簡單易用**：只需要一個API密鑰
- ✅ **快速設置**：5分鐘內完成配置
- ✅ **免費額度**：每月有免費使用額度
- ✅ **無需專案**：不需要創建Google Cloud專案

### 🔧 方式2：Vertex AI
- 🔹 **企業級**：適合大規模使用
- 🔹 **更多控制**：提供更多配置選項
- 🔹 **需要專案**：需要Google Cloud專案和計費帳戶

---

## 🎯 方式1：Google Generative AI 配置 (推薦)

### 步驟1：獲取API密鑰

1. **前往Google AI Studio**
   - 打開瀏覽器，訪問：https://aistudio.google.com/app/apikey
   - 使用您的Google帳號登入

2. **創建API密鑰**
   - 點擊 **"Create API Key"** 按鈕
   - 選擇 **"Create API key in new project"** (如果您沒有現有專案)
   - 等待API密鑰生成

3. **複製API密鑰**
   - 複製生成的API密鑰 (格式類似：AIzaSyA...)
   - ⚠️ **重要**：請妥善保管此密鑰，不要分享給他人

### 步驟2：配置環境變數

1. **編輯.env文件**
   - 打開專案根目錄下的 `.env` 文件
   - 找到這一行：`GOOGLE_API_KEY=your_google_api_key_here`
   - 將 `your_google_api_key_here` 替換為您的實際API密鑰

2. **示例配置**
   ```
   GOOGLE_API_KEY=AIzaSyA1234567890abcdefghijklmnopqrstuvwxyz
   ```

### 步驟3：測試配置

1. **在GUI中測試**
   - 啟動應用程式：`python main.py`
   - 切換到 **"走勢分析"** 模式
   - 在 **"Google API 密鑰"** 欄位輸入您的API密鑰
   - 載入任一數據文件
   - 點擊 **"開始分析"** 進行測試

2. **使用測試模式**
   - 如果暫時沒有API密鑰，可以在API密鑰欄位輸入 `test` 來使用測試模式

---

## 🔧 方式2：Vertex AI 配置 (進階)

### 步驟1：創建Google Cloud專案

1. **前往Google Cloud Console**
   - 訪問：https://console.cloud.google.com/
   - 使用您的Google帳號登入

2. **創建新專案**
   - 點擊頂部的專案選擇器
   - 點擊 **"新增專案"**
   - 輸入專案名稱（例如：crypto-trading-ai）
   - 點擊 **"建立"**

3. **記錄專案ID**
   - 創建完成後，記下您的專案ID（通常是專案名稱加上隨機數字）

### 步驟2：啟用API服務

1. **啟用Vertex AI API**
   - 在Google Cloud Console中，前往 **"API和服務" > "程式庫"**
   - 搜索 **"Vertex AI API"**
   - 點擊並啟用該API

2. **設置計費帳戶**
   - 前往 **"計費"** 頁面
   - 設置計費帳戶（Vertex AI需要啟用計費）

### 步驟3：創建服務帳號 (可選)

1. **創建服務帳號**
   - 前往 **"IAM和管理" > "服務帳號"**
   - 點擊 **"建立服務帳號"**
   - 輸入名稱：`crypto-trading-ai-service`
   - 授予角色：**"Vertex AI User"**

2. **下載金鑰文件**
   - 點擊創建的服務帳號
   - 前往 **"金鑰"** 標籤
   - 點擊 **"新增金鑰" > "建立新金鑰"**
   - 選擇 **JSON** 格式
   - 下載並保存金鑰文件到專案目錄

### 步驟4：配置環境變數

1. **編輯.env文件**
   ```
   GOOGLE_PROJECT_ID=your-actual-project-id
   GOOGLE_LOCATION=us-central1
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
   ```

---

## 🧪 測試配置

### 快速測試腳本

創建並運行以下測試腳本：

```python
# test_google_ai.py
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def test_google_ai_config():
    """測試Google AI配置"""
    print("=== Google AI 配置測試 ===")
    
    # 檢查方式1：Google Generative AI
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key and api_key != 'your_google_api_key_here':
        print(f"✅ Google API Key: {api_key[:10]}...")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Hello, this is a test.")
            print("✅ Google Generative AI 連接成功！")
            return True
        except Exception as e:
            print(f"❌ Google Generative AI 測試失敗: {e}")
    
    # 檢查方式2：Vertex AI
    project_id = os.getenv('GOOGLE_PROJECT_ID')
    if project_id and project_id != 'your_google_cloud_project_id_here':
        print(f"✅ Google Project ID: {project_id}")
        
        try:
            from google.cloud import aiplatform
            aiplatform.init(project=project_id, location='us-central1')
            print("✅ Vertex AI 連接成功！")
            return True
        except Exception as e:
            print(f"❌ Vertex AI 測試失敗: {e}")
    
    print("❌ 未找到有效的Google AI配置")
    return False

if __name__ == "__main__":
    test_google_ai_config()
```

### 在GUI中測試

1. **啟動應用程式**
   ```bash
   python main.py
   ```

2. **切換到走勢分析模式**
   - 選擇 **"走勢分析"** 單選按鈕

3. **輸入API密鑰**
   - 在 **"Google API 密鑰"** 欄位輸入您的API密鑰
   - 或者輸入 `test` 使用測試模式

4. **執行分析**
   - 載入任一數據文件
   - 點擊 **"開始分析"**
   - 查看分析結果

---

## 🔍 故障排除

### 常見問題

1. **API密鑰無效**
   - 確認API密鑰正確複製，沒有多餘空格
   - 確認API密鑰沒有過期
   - 檢查API配額是否用盡

2. **Vertex AI連接失敗**
   - 確認專案ID正確
   - 確認已啟用Vertex AI API
   - 確認計費帳戶已設置

3. **權限問題**
   - 確認服務帳號有適當權限
   - 確認金鑰文件路徑正確

### 獲取幫助

- **Google AI Studio文檔**：https://ai.google.dev/docs
- **Vertex AI文檔**：https://cloud.google.com/vertex-ai/docs
- **專案GitHub Issues**：如有問題可在專案中提出

---

## 🎉 配置完成

配置完成後，您就可以使用強大的Google AI來進行加密貨幣走勢分析了！

**下一步**：返回應用程式，開始體驗AI驅動的走勢分析功能。
