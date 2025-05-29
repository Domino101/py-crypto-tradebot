# 🚀 專業級加密貨幣分析交易平台

一個基於Python的專業級加密貨幣分析與交易平台，整合了N8N工作流、Google Gemini AI分析、回測和實盤交易功能。

## ✨ 重大更新 (v2.0)

### 🤖 N8N工作流移植
- **完整移植N8N專業分析工作流**
- **Google Gemini AI雙重調用**：新聞情緒分析 + 專業交易分析
- **多時間框架自動數據獲取**：15分鐘、1小時、1天
- **繁體中文專業分析報告**
- **自動新聞情緒分析**

### 🏗️ 模塊化架構重構
- **解決UI切換問題**：完全重寫GUI架構
- **分離顯示與業務邏輯**：提升可維護性
- **專用UI管理器**：BacktestUI、LiveTradingUI、TrendAnalysisUI
- **統一模式切換**：BaseUIManager處理所有模式

### 🌐 Web版本界面
- **Flask + Bootstrap響應式設計**
- **RESTful API架構**
- **實時數據更新**
- **移動設備友好**

## 🎯 功能特色

### 📊 走勢分析 (NEW!)
- 🤖 **AI驅動分析**: Google Gemini專業分析
- 📰 **新聞情緒整合**: 自動獲取和分析市場新聞
- 📈 **多時間框架**: 15m/1h/1d交叉驗證
- 💼 **專業交易建議**: 現貨 + 槓桿交易策略
- 🎯 **精確價格預測**: 進場、止損、止盈位

### 📊 回測功能
- 📈 **歷史數據回測**: 使用真實市場數據
- 🔧 **多種策略**: RSI、MACD、EMA等技術指標
- 📋 **詳細報告**: 完整績效分析和圖表
- ⚙️ **參數優化**: 策略參數自動調整

### 🤖 實盤交易
- 🔗 **Alpaca API整合**: 美股和加密貨幣交易
- 🛡️ **風險管理**: 止損、止盈自動執行
- 📊 **實時監控**: 持倉和訂單狀態追蹤
- 🔔 **交易通知**: 重要事件即時提醒

### 🎨 雙重界面
- 🖥️ **桌面GUI**: Tkinter專業界面
- 🌐 **Web界面**: 現代化響應式設計
- 📱 **移動友好**: 支援手機和平板

## 🚀 快速開始

### 環境需求

- Python 3.8+
- Google AI API密鑰 (用於走勢分析)
- Alpaca API密鑰 (用於實盤交易，可選)

### 安裝步驟

1. **克隆專案**
```bash
git clone https://github.com/Domino101/py-crypto-tradebot.git
cd py-crypto-tradebot
```

2. **安裝依賴**
```bash
# 桌面版
pip install -r requirements.txt

# Web版 (額外)
pip install -r requirements-web.txt
```

3. **配置API密鑰**
```bash
# 複製環境變數模板
cp .env.example .env

# 編輯 .env 文件，添加您的API密鑰
GOOGLE_API_KEY=your_google_api_key_here
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here
```

4. **運行程式**
```bash
# 桌面GUI版本
python main.py

# 或使用新的模塊化版本
python gui/new_app.py

# Web版本
python web/app.py
```

## 📖 使用指南

### 🎯 走勢分析模式 (推薦)

1. **啟動程式**並選擇「走勢分析」模式
2. **輸入幣種名稱**：如 `BTC`、`ETH`、`SUI`
3. **系統自動轉換**為USDT交易對 (如 BTCUSDT)
4. **點擊「🚀 開始專業分析」**
5. **觀看N8N工作流執行**：
   - 📊 獲取多時間框架數據
   - 📰 分析新聞情緒
   - 🔄 合併技術與情緒數據
   - 🎯 生成專業交易建議

### 📊 回測模式

1. 選擇「回測」模式
2. 載入歷史數據或使用內建數據
3. 選擇交易策略和參數
4. 開始回測並查看結果

### 🤖 實盤交易模式

1. 選擇「實盤交易」模式
2. 配置Alpaca API密鑰
3. 選擇策略和風險參數
4. 開始實盤交易

## 🔧 配置指南

### Google AI配置
詳見：[Google_AI_配置指南.md](Google_AI_配置指南.md)

### GUI測試指南
詳見：[GUI_測試指南.md](GUI_測試指南.md)

### 快速測試
詳見：[快速測試指南.md](快速測試指南.md)

## 📁 專案結構

```
py-crypto-tradebot/
├── analysis/              # AI分析模組
│   └── trend_analyzer.py  # N8N工作流分析器
├── gui/                   # 模塊化GUI
│   ├── base_ui.py         # 基礎UI管理器
│   ├── backtest_ui.py     # 回測界面
│   ├── live_trading_ui.py # 實盤交易界面
│   ├── trend_analysis_ui.py # 走勢分析界面
│   └── new_app.py         # 新版主程式
├── web/                   # Web版本
│   ├── app.py             # Flask應用
│   ├── api.py             # RESTful API
│   └── models.py          # 數據模型
├── strategies/            # 交易策略
├── data/                  # 數據管理
└── backtest/              # 回測引擎
```

## 🎯 策略說明

### 技術分析策略
- **RSI EMA策略**: 相對強弱指標 + 指數移動平均
- **MACD背離策略**: 移動平均收斂發散指標
- **Vegas雙隧道策略**: 雙移動平均線系統
- **布朗運動策略**: 隨機遊走模型

### AI分析策略 (NEW!)
- **多時間框架分析**: 15m短期 + 1h中期 + 1d長期
- **新聞情緒驅動**: 結合市場新聞情緒
- **技術指標確認**: MACD、RSI、OBV綜合驗證
- **專業交易建議**: 具體進場、止損、止盈位

## 🔍 測試文件

- `test_trend_analyzer.py` - 走勢分析測試
- `test_new_gui.py` - 新GUI測試
- `test_google_ai_config.py` - Google AI配置測試
- `test_full_integration.py` - 完整集成測試

## ⚠️ 風險警告

**加密貨幣交易具有極高風險，可能導致全部資金損失。**

- 📚 **教育用途**: 本專案主要用於學習和研究
- 🧪 **充分測試**: 實盤前請充分回測和模擬
- 💰 **風險管理**: 只投入您能承受損失的資金
- 📊 **理性決策**: AI分析僅供參考，非投資建議

## 🤝 貢獻

歡迎提交Issue和Pull Request！

## 📄 授權條款

MIT License

---

**⭐ 如果這個專案對您有幫助，請給個星星支持！**
