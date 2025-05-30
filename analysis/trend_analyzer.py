"""
走勢分析模組 - 使用Google Vertex AI的Gemini模型分析市場走勢
"""
import os
import pandas as pd
import json
import time
from datetime import datetime, timedelta # Ensure timedelta is imported
from typing import Dict, Any, Optional
import traceback
import numpy as np # Ensure numpy is imported
import re # Ensure re is imported for mock response generation

# 載入環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv 是可選的

try:
    from google.cloud import aiplatform
    from google.oauth2 import service_account
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("警告: Google Cloud AI Platform 依賴未安裝。請安裝 google-cloud-aiplatform 和 google-generativeai")

class TrendAnalyzer:
    """使用Gemini模型分析市場走勢的類"""

    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None, location: Optional[str] = None):
        """
        初始化分析器

        Args:
            api_key: Google API密鑰 (如果未提供，將從環境變數 GOOGLE_API_KEY 讀取)
            project_id: Google Cloud專案ID (如果未提供，將從環境變數 GOOGLE_PROJECT_ID 讀取)
            location: Vertex AI位置 (如果未提供，將從環境變數 GOOGLE_LOCATION 讀取，預設為 us-central1)
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google Cloud AI Platform 依賴未安裝。請安裝相關套件。")

        # 從參數或環境變數獲取配置
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.project_id = project_id or os.environ.get("GOOGLE_PROJECT_ID")
        self.location = location or os.environ.get("GOOGLE_LOCATION", "us-central1")

        # 檢查是否有有效的配置
        if not self.api_key and not self.project_id:
            print("警告: 未找到Google API密鑰或專案ID")
            print("請在環境變數中設置 GOOGLE_API_KEY 或 GOOGLE_PROJECT_ID")
            print("或者在初始化時提供這些參數")

        self.model = None
        self.max_retries = 3
        self.retry_delay = 2

        self._init_ai_client()

    def _init_ai_client(self):
        """初始化AI客戶端連接"""
        try:
            # 優先使用Google Generative AI (更簡單的API)
            if self.api_key:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("已初始化 Google Generative AI 客戶端")
                return

            # 備用：使用Vertex AI
            if self.project_id:
                # 如果有服務帳號金鑰文件，使用它
                if os.path.exists("google_credentials.json"):
                    credentials = service_account.Credentials.from_service_account_file(
                        "google_credentials.json"
                    )
                    aiplatform.init(
                        project=self.project_id,
                        location=self.location,
                        credentials=credentials
                    )
                else:
                    aiplatform.init(project=self.project_id, location=self.location)

                self.model = aiplatform.GenerativeModel("gemini-1.5-flash")
                print("已初始化 Vertex AI 客戶端")
                return

            raise ValueError("需要提供Google API密鑰或Google Cloud專案ID")

        except Exception as e:
            print(f"初始化AI客戶端時出錯: {e}")
            traceback.print_exc()
            raise

    def analyze_trend(self, data: Optional[pd.DataFrame], symbol: str, timeframe: str, detail_level: str = "標準") -> Dict[str, Any]:
        """
        N8N工作流完整移植 - 專業級加密貨幣分析系統

        完整複製N8N工作流的分析邏輯：
        1. 獲取多時間框架K線數據 (15m, 1h, 1d)
        2. 獲取並分析加密貨幣新聞情緒
        3. 使用Google Gemini進行綜合技術分析
        4. 生成具體的現貨和槓桿交易建議

        Args:
            data: 包含OHLCV數據的DataFrame (可選, 在N8N模式下為None)
            symbol: 交易對符號
            timeframe: 時間框架
            detail_level: 分析詳細程度 ("簡要", "標準", "詳細")

        Returns:
            分析結果字典
        """
        try:
            print(f"🚀 開始N8N工作流分析 {symbol} {timeframe} 數據...")

            if data is not None and not self._validate_data(data): # 僅在提供了data時驗證
                    raise ValueError("數據驗證失敗")

            # 步驟1: 獲取多時間框架K線數據
            print("📊 步驟1: 獲取多時間框架K線數據...")
            multi_timeframe_data = self._fetch_multi_timeframe_data(symbol)

            # 步驟2: 獲取並分析新聞情緒
            print("📰 步驟2: 獲取並分析新聞情緒...")
            news_sentiment = self._fetch_and_analyze_news_sentiment(symbol)

            # 步驟3: 合併所有數據
            print("🔄 步驟3: 合併技術數據和情緒數據...")
            combined_data = self._combine_technical_and_sentiment_data(
                multi_timeframe_data, news_sentiment
            )

            # 步驟4: 使用Google Gemini進行專業分析
            print("🎯 步驟4: 使用Google Gemini進行專業分析...")
            professional_analysis = self._generate_professional_trading_analysis(
                symbol, combined_data, detail_level
            )

            return professional_analysis

        except Exception as e:
            error_msg = f"分析過程中發生錯誤: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return {
                "analysis_text": error_msg,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "error_formatting"
            }

    def _fetch_multi_timeframe_data(self, symbol: str) -> Dict[str, Any]:
        """步驟1: 獲取多時間框架K線數據 (模擬N8N的HTTP請求)"""
        try:
            # import requests # Keep this if actual API calls are made
            # import numpy as np # Already imported globally

            timeframes = ['15m', '1h', '1d']
            all_candles_data = [] # Renamed for clarity

            for tf in timeframes:
                print(f"   獲取 {symbol} {tf} K線數據...")
                candles_data = self._generate_realistic_kline_data(symbol, tf, 200)
                formatted_data = {
                    "timeframe": tf,
                    "candles": candles_data
                }
                all_candles_data.append(formatted_data)
                print(f"   ✅ {tf} 數據獲取完成 ({len(candles_data)} 根K線)")

            return {
                "allCandles": all_candles_data,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"獲取多時間框架數據時出錯: {e}")
            return {
                "error": str(e),
                "allCandles": [],
                "symbol": symbol, # Include symbol even in error
                "timestamp": datetime.now().isoformat()
            }

    def _generate_realistic_kline_data(self, symbol: str, timeframe: str, limit: int) -> list:
        """生成更真實的K線數據格式 (模擬Binance API回應)"""
        try:
            # 基礎價格範圍設定
            symbol_price_ranges = {
                "BTC": (60000.0, 75000.0), "ETH": (3000.0, 4000.0),
                "SUI": (0.8, 1.5), "SOL": (150.0, 200.0),
                "ADA": (0.4, 0.6), "DOT": (5.0, 8.0),
                "DOGE": (0.1, 0.2), "LINK": (15.0, 25.0),
                "DEFAULT": (1.0, 50.0) # Adjusted default for typical altcoins
            }
            base_volatility = 0.025 # Slightly increased base volatility

            selected_range = symbol_price_ranges.get(symbol.upper(), symbol_price_ranges["DEFAULT"])
            for prefix, price_range in symbol_price_ranges.items():
                if symbol.upper().startswith(prefix):
                    selected_range = price_range
                    break
            base_price = np.random.uniform(selected_range[0], selected_range[1])

            interval_minutes = {'15m': 15, '1h': 60, '1d': 1440}
            minutes_interval = interval_minutes.get(timeframe, 60)

            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes_interval * limit)

            candles = []
            current_price = base_price
            current_volatility = base_volatility
            
            trend_types = ["uptrend", "downtrend", "sideways"]
            current_trend = np.random.choice(trend_types)
            trend_duration_counter = 0
            
            min_candles_per_trend = max(1, limit // 10) # Trend lasts for at least 10% of candles
            max_trend_len_divisor = np.random.randint(2, 6) # Trend can last 1/2 to 1/5 of total limit
            current_max_trend_duration = max(min_candles_per_trend, limit // max_trend_len_divisor)

            for i in range(limit):
                candle_timestamp = start_time + timedelta(minutes=minutes_interval * i)
                open_time = int(candle_timestamp.timestamp() * 1000)
                close_time = int((candle_timestamp + timedelta(minutes=minutes_interval)).timestamp() * 1000) -1 # Binance format

                if i > 0 and i % 20 == 0: # Adjust volatility periodically
                    volatility_noise = np.random.normal(0, 0.005)
                    current_volatility = max(0.005, current_volatility + volatility_noise)

                trend_duration_counter += 1
                if trend_duration_counter > current_max_trend_duration and i < limit - min_candles_per_trend:
                    current_trend = np.random.choice(trend_types)
                    trend_duration_counter = 0
                    max_trend_len_divisor = np.random.randint(2, 6)
                    current_max_trend_duration = max(min_candles_per_trend, limit // max_trend_len_divisor)
                    # print(f"Candle {i} ({symbol} {timeframe}): New trend '{current_trend}' for ~{current_max_trend_duration} candles. Vol: {current_volatility:.4f}")


                open_p = current_price
                
                # Price change logic with trend bias
                price_change_factor = np.random.normal(0, current_volatility)
                trend_influence = 0
                if current_trend == "uptrend":
                    trend_influence = abs(np.random.normal(0, current_volatility * 0.5)) # Stronger bias
                elif current_trend == "downtrend":
                    trend_influence = -abs(np.random.normal(0, current_volatility * 0.5))
                
                price_change_factor += trend_influence
                price_change_factor = np.clip(price_change_factor, -current_volatility * 4, current_volatility * 4) # Wider clip
                close_p = open_p * (1 + price_change_factor)
                close_p = max(close_p, selected_range[0] * 0.1) # Ensure price doesn't go unrealistically low

                # OHLC generation ensuring consistency
                if open_p == close_p:
                    high_p = open_p * (1 + abs(np.random.normal(0, current_volatility * 0.1)))
                    low_p = open_p * (1 - abs(np.random.normal(0, current_volatility * 0.1)))
                elif open_p < close_p: # Price increased
                    low_p = open_p * (1 - abs(np.random.normal(0, current_volatility * np.random.uniform(0.1,0.5))))
                    high_p = close_p * (1 + abs(np.random.normal(0, current_volatility * np.random.uniform(0.1,0.5))))
                else: # Price decreased (open_p > close_p)
                    low_p = close_p * (1 - abs(np.random.normal(0, current_volatility * np.random.uniform(0.1,0.5))))
                    high_p = open_p * (1 + abs(np.random.normal(0, current_volatility * np.random.uniform(0.1,0.5))))

                # Final OHLC validation
                high_p = max(high_p, open_p, close_p)
                low_p = min(low_p, open_p, close_p)
                if low_p > high_p : low_p = high_p # Should not happen with above logic but as a safeguard
                if low_p <=0 : low_p = min(open_p,close_p) * 0.9 # prevent negative or zero low price

                # Volume simulation
                volume_base = np.random.uniform(50, 1500) # Wider range for volume
                volatility_impact_on_volume = 1 + (current_volatility - base_volatility) / base_volatility if base_volatility > 0 else 1
                trend_impact_on_volume = 1.0
                if (current_trend == "uptrend" and price_change_factor > 0.0005) or \
                   (current_trend == "downtrend" and price_change_factor < -0.0005):
                    trend_impact_on_volume = np.random.uniform(1.2, 2.0) # Higher volume on strong trend moves
                
                volume_val = volume_base * volatility_impact_on_volume * trend_impact_on_volume
                quote_volume_val = volume_val * (high_p + low_p) / 2

                candle = [
                    open_time, f"{open_p:.8f}", f"{high_p:.8f}", f"{low_p:.8f}", f"{close_p:.8f}",
                    f"{volume_val:.8f}", close_time, f"{quote_volume_val:.8f}",
                    int(np.random.uniform(30, 250)), # trades
                    f"{volume_val * np.random.uniform(0.4, 0.6):.8f}", # takerBuyBaseVolume
                    f"{quote_volume_val * np.random.uniform(0.4, 0.6):.8f}", # takerBuyQuoteVolume
                    "0" # ignore
                ]
                candles.append(candle)
                current_price = close_p
            return candles
        except Exception as e:
            print(f"生成K線數據時出錯 ({symbol} {timeframe}): {e}")
            traceback.print_exc()
            return []

    def _fetch_and_analyze_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """步驟2: 獲取並分析新聞情緒"""
        try:
            print(f"   獲取 {symbol} 相關加密貨幣新聞...")
            news_data = self._fetch_crypto_news(symbol) # Pass symbol

            print("   過濾新聞內容...")
            filtered_articles = self._filter_news_articles(news_data)

            print("   分析新聞情緒...")
            sentiment_analysis = self._analyze_news_sentiment_with_ai(filtered_articles)
            
            return sentiment_analysis
        except Exception as e:
            print(f"獲取和分析新聞情緒時出錯: {e}")
            return {
                "error": str(e),
                "shortTermSentiment": {"category": "Neutral", "score": 0.0, "rationale": "無法獲取新聞數據"},
                "longTermSentiment": {"category": "Neutral", "score": 0.0, "rationale": "無法獲取新聞數據"},
                "retrievedArticles": 0
            }

    def _fetch_crypto_news(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """獲取加密貨幣新聞 (模擬NewsAPI) - 增強版"""
        try:
            mock_articles_templates = [
                # Positive
                {"title": "{SYMBOL}創下歷史新高，市場情緒沸騰", "description": "{SYMBOL}價格今日飆升，成功突破先前高點，分析師看好後續漲勢。"},
                {"title": "重大合作宣布：{SYMBOL}將與大型科技公司整合", "description": "{SYMBOL}團隊宣布與一家全球科技巨頭達成戰略合作，預計將推動大規模採用。"},
                {"title": "監管利好：政府對{SYMBOL}等加密資產釋放積極信號", "description": "某主要國家金融監管機構表示，將以更開放的態度對待{SYMBOL}等創新技術，市場解讀為重大利好。"},
                {"title": "{SYMBOL}網絡成功升級，性能提升10倍", "description": "備受期待的{SYMBOL}網絡升級已順利完成，據測試數據顯示，交易速度和網絡容量均有顯著提升。"},
                {"title": "機構巨頭大舉買入{SYMBOL}，長期價值獲認可", "description": "知名投資機構本季度增持了大量{SYMBOL}，報告稱其看好{SYMBOL}的長期發展潛力。"},
                # Negative
                {"title": "市場暴跌：{SYMBOL}價格一日內腰斬", "description": "在恐慌性拋售潮中，{SYMBOL}價格遭遇重挫，24小時內跌幅超過50%，市場信心受到嚴重打擊。"},
                {"title": "安全漏洞警告：{SYMBOL}智能合約發現嚴重缺陷", "description": "安全機構披露{SYMBOL}核心智能合約存在嚴重漏洞，用戶資金面臨潛在風險，團隊正在緊急修復。"},
                {"title": "監管重拳：多國宣布禁止{SYMBOL}相關交易活動", "description": "出於對金融風險的擔憂，數個國家今日聯合宣布將禁止一切與{SYMBOL}相關的交易及挖礦活動。"},
                {"title": "{SYMBOL}項目團隊核心成員集體辭職，項目瀕臨崩潰", "description": "據內部消息，{SYMBOL}項目多名核心開發者因理念不合集體辭職，社群對項目未來感到絕望。"},
                {"title": "交易所被盜：大量{SYMBOL}被黑客轉移", "description": "一家中型交易所遭到黑客攻擊，價值數千萬美元的{SYMBOL}及其他加密貨幣被盜，引發用戶恐慌。"},
                # Neutral
                {"title": "{SYMBOL}價格窄幅震盪，市場等待方向選擇", "description": "{SYMBOL}價格已連續多日在狹窄區間內波動，多空雙方力量均衡，市場參與者正密切關注 posibles的突破信號。"},
                {"title": "分析師對{SYMBOL}未來走勢看法不一", "description": "針對{SYMBOL}的未來價格走勢，市場分析師們持有不同觀點，一些人看漲，另一些人則持謹慎態度。"},
                {"title": "區塊鏈峰會討論{SYMBOL}等加密資產的監管挑戰", "description": "正在進行的全球區塊鏈峰會上，來自各國的監管者和行業領袖就{SYMBOL}等加密資產面臨的監管問題進行了深入探討。"},
                {"title": "{SYMBOL}交易量平穩，市場活躍度維持常態", "description": "最新數據顯示，{SYMBOL}的24小時交易量保持在近期平均水平，市場活躍度未出現顯著變化。"},
                {"title": "報告顯示{SYMBOL}在特定行業的應用案例增加", "description": "一份行業研究報告指出，{SYMBOL}作為支付或底層技術的解決方案，在供應鏈、遊戲等行業的應用案例有所增長。"}
            ]
            
            num_articles_to_return = np.random.randint(min(3, len(mock_articles_templates)), min(10, len(mock_articles_templates)) + 1)
            
            # Ensure deep copy for templates before selection
            selected_article_templates_copies = [dict(t) for t in mock_articles_templates]
            selected_article_templates = np.random.choice(selected_article_templates_copies, size=num_articles_to_return, replace=False)
            
            processed_articles = []
            for article_template in selected_article_templates:
                article = dict(article_template) # Work on a copy
                display_symbol = symbol or "加密貨幣" 
                
                article["title"] = article["title"].replace("{SYMBOL}", display_symbol)
                article["description"] = article["description"].replace("{SYMBOL}", display_symbol)
                processed_articles.append(article)

            return {"articles": processed_articles}
        except Exception as e:
            print(f"獲取新聞時出錯 ({symbol}): {e}")
            return {"articles": []}

    def _filter_news_articles(self, news_data: Dict[str, Any]) -> list: # news_data is Dict
        """過濾新聞文章"""
        try:
            articles = news_data.get("articles", [])
            filtered_articles = []
            for article in articles:
                filtered_articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", "")
                })
            return filtered_articles
        except Exception as e:
            print(f"過濾新聞文章時出錯: {e}")
            return []

    def _analyze_news_sentiment_with_ai(self, filtered_articles: list) -> Dict[str, Any]:
        """使用AI分析新聞情緒"""
        try:
            if self.api_key and self.api_key.lower() in ["test", "demo", "測試"]:
                print("   使用模擬情緒分析...")
                mock_response = self._generate_mock_sentiment_analysis()
                mock_response["retrievedArticles"] = len(filtered_articles)
                return mock_response

            sentiment_prompt = self._build_sentiment_analysis_prompt(filtered_articles)
            print("   調用Google Gemini分析新聞情緒...")
            response_text = self._call_gemini_model_with_retry(sentiment_prompt)
            parsed_sentiment = self._parse_sentiment_response(response_text)
            parsed_sentiment["retrievedArticles"] = len(filtered_articles)
            return parsed_sentiment
        except Exception as e:
            print(f"AI情緒分析時出錯: {e}")
            mock_sentiment = self._generate_mock_sentiment_analysis()
            mock_sentiment["retrievedArticles"] = len(filtered_articles) if filtered_articles else 0
            return mock_sentiment

    def _build_sentiment_analysis_prompt(self, filtered_articles: list) -> str:
        """構建情緒分析提示詞 (完全複製N8N工作流)"""
        articles_json = json.dumps(filtered_articles, ensure_ascii=False, indent=2) # Added indent for readability

        prompt = f"""You are a highly intelligent and accurate sentiment analyzer specializing in cryptocurrency markets. Analyze the sentiment of the provided text using a two-part approach:

1. Short-Term Sentiment:
    -Evaluate the immediate market reaction, recent news impact, and technical volatility.
    -Determine a sentiment category "Positive", "Neutral", or "Negative".
    -Calculate a numerical score between -1 (extremely negative) and 1 (extremely positive).
    -Provide a detailed rationale explaining the short-term sentiment.

2. Long-Term Sentiment:
    -Evaluate the overall market outlook, fundamentals, and regulatory developments.
    -Determine the sentiment category: "Positive", "Neutral", or "Negative".
    -Calculate a numerical score between -1 (extremely negative) and 1 (extremely positive).
    -Provide a detailed rationale explaining the long-term sentiment.

Your output must be exactly a JSON object with exactly two keys: "shortTermSentiment" and "longTermSentiment". Do not output anything else.

For example, your output should look like: {{
  "shortTermSentiment": {{
    "category": "Positive",
    "score": 0.7,
    "rationale": "..."
}},
  "longTermSentiment": {{
    "category": "Neutral",
    "score": 0.1,
    "rationale": "..."
  }}
}}.
Now, analyze the following text (list of news articles) and produce your JSON output:
{articles_json}"""
        return prompt

    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """解析情緒分析回應"""
        try:
            # Find the first '{' and the last '}' to extract the JSON part
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0: # Check if rfind returned -1 then +1 = 0
                raise ValueError("無法在回應中找到有效的JSON對象")
            
            json_part = response[json_start:json_end]
            parsed_response = json.loads(json_part)

            # Validate structure
            if "shortTermSentiment" not in parsed_response or "longTermSentiment" not in parsed_response:
                raise ValueError("AI回應中缺少必要的sentiment鍵")

            return {
                "shortTermSentiment": parsed_response.get("shortTermSentiment", {}),
                "longTermSentiment": parsed_response.get("longTermSentiment", {})
            }
        except json.JSONDecodeError as e:
            print(f"解析情緒分析JSON時出錯: {e}. 回應文本: '{response[:500]}...'") # Log part of response
            return self._generate_mock_sentiment_analysis() # Fallback
        except ValueError as e:
            print(f"解析情緒分析回應時出錯: {e}. 回應文本: '{response[:500]}...'")
            return self._generate_mock_sentiment_analysis() # Fallback
        except Exception as e: # Catch any other unexpected errors
            print(f"解析情緒分析回應時發生未知錯誤: {e}. 回應文本: '{response[:500]}...'")
            return self._generate_mock_sentiment_analysis()


    def _generate_mock_sentiment_analysis(self) -> Dict[str, Any]:
        """生成模擬情緒分析結果 (不含 retrievedArticles)"""
        return {
            "shortTermSentiment": {
                "category": "Neutral", "score": 0.0,
                "rationale": "模擬短期情緒：市場情緒中性，等待更多信號。"
            },
            "longTermSentiment": {
                "category": "Neutral", "score": 0.1,
                "rationale": "模擬長期情緒：基本面保持穩定，但存在不確定性。"
            }
            # retrievedArticles will be added by the caller
        }

    def _combine_technical_and_sentiment_data(self, multi_timeframe_data: Dict[str, Any],
                                            news_sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """步驟3: 合併技術數據和情緒數據"""
        try:
            all_candles = multi_timeframe_data.get("allCandles", [])
            current_symbol = multi_timeframe_data.get("symbol", "UNKNOWN_SYMBOL")

            sentiment_content = {
                "shortTermSentiment": news_sentiment.get("shortTermSentiment", {}),
                "longTermSentiment": news_sentiment.get("longTermSentiment", {}),
                "retrievedArticles": news_sentiment.get("retrievedArticles", 0) 
            }

            combined_data = {
                "allCandles": all_candles,
                "content": sentiment_content,
                "symbol": current_symbol 
            }

            print(f"   ✅ 數據合併完成 - K線數據: {len(all_candles)} 個時間框架, 新聞文章: {sentiment_content['retrievedArticles']}")
            return combined_data
        except Exception as e:
            print(f"合併數據時出錯: {e}")
            return {
                "allCandles": [],
                "content": {"retrievedArticles": 0},
                "symbol": multi_timeframe_data.get("symbol", "ERROR_SYMBOL")
            }

    def _generate_professional_trading_analysis(self, symbol: str, combined_data: Dict[str, Any],
                                              detail_level: str) -> Dict[str, Any]:
        """步驟4: 生成專業交易分析"""
        try:
            professional_prompt = self._build_professional_analysis_prompt(symbol, combined_data)
            print("   調用Google Gemini進行專業交易分析...")
            analysis_result_text = self._call_gemini_model_with_retry(professional_prompt)
            
            # 移除HTML標籤 (Gemini不應該返回HTML, 但以防萬一)
            cleaned_analysis_text = self._remove_html_tags(analysis_result_text)

            return self._format_response(cleaned_analysis_text, symbol, "多時間框架")

        except Exception as e:
            print(f"生成專業分析時出錯: {e}")
            return {
                "analysis_text": f"生成專業分析時發生錯誤: {str(e)}",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "timeframe": "多時間框架", # Default timeframe for this N8N-like flow
                "status": "error"
            }

    def _build_professional_analysis_prompt(self, symbol: str, combined_data: Dict[str, Any]) -> str:
        """構建專業分析提示詞 (完全複製N8N工作流的AI Agent提示詞)"""
        all_candles = combined_data.get("allCandles", [])
        sentiment_content = combined_data.get("content", {}) # Includes retrievedArticles
        current_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S") # Changed format slightly

        # Serializing data to JSON for the prompt
        # Limiting candles per timeframe in prompt to avoid excessive length
        prompt_candles_data = []
        for tf_data in all_candles:
            copied_tf_data = dict(tf_data) # Make a copy
            copied_tf_data["candles"] = copied_tf_data.get("candles", [])[:50] # Limit to first 50 candles for prompt
            prompt_candles_data.append(copied_tf_data)

        technical_data_json = json.dumps(prompt_candles_data, ensure_ascii=False, indent=2)
        sentiment_data_json = json.dumps(sentiment_content, ensure_ascii=False, indent=2)

        prompt = f"""以下是 {symbol} (分析時間: {current_time}) 的綜合市場數據供您參考：

### 技術數據 (僅顯示部分K線以簡潔):
```json
{technical_data_json}
```

### 情緒分析 (基於 {sentiment_content.get('retrievedArticles', '未知數量的')} 篇新聞):
```json
{sentiment_data_json}
```

**指示：** 你是一位專業的加密貨幣市場分析師。基於以上提供的 JSON 格式的技術數據（多時間框架K線：15m, 1h, 1d）和新聞情緒分析，請執行以下任務：

**1. 數據解讀:**
   - **短期 (15m & 1h):** 分析近期價格行為、波動性、潛在支撐/阻力位。結合技術指標（如移動平均線、RSI、MACD - 你需要基於K線數據自行腦補或推斷這些指標的可能狀態）和價格形態。
   - **長期 (1d):** 評估主要趨勢方向、關鍵的長期支撐/阻力區域。同樣，結合可能的指標狀態和價格形態。
   - **新聞情緒整合:** 評論短期和長期新聞情緒如何影響市場，以及它是否與技術分析一致或矛盾。

**2. 交易建議 (請提供詳細理由):**

   **a. 現貨交易:**
      - **操作建議:** (買入 / 賣出 / 持有 / 觀望)
      - **信心水平:** (高 / 中 / 低)
      - **進場價格區域:** (如果建議買入/賣出)
      - **止損參考:**
      - **止盈目標區域 (至少2個):**
      - **理由:** (詳細闡述，結合技術信號、價格形態、趨勢判斷、新聞情緒等)

   **b. 槓桿交易 (如果市場狀況適合):**
      - **操作建議:** (開多 / 開空 / 暫不操作)
      - **信心水平:** (高 / 中 / 低)
      - **建議槓桿倍數:** (例如：3x, 5x, 10x - 請謹慎)
      - **進場價格區域:**
      - **止損參考:**
      - **止盈目標區域 (至少2個):**
      - **理由:** (詳細闡述，特別強調風險管理和為何適合槓桿操作)

**3. 風險評估:**
   - 簡要說明當前交易建議的主要風險點。

**輸出格式要求:**
   - 使用繁體中文。
   - 以清晰的標題和子標題組織報告。
   - 使用項目符號 (`-`) 列點說明。
   - **不要**在最終輸出中使用任何Markdown的代碼塊 (```json ... ```) 或 HTML 標籤。所有內容都應為純文本。
   - 確保理由部分充分、專業，並直接引用數據中的信息（例如，提及特定時間框架的K線模式或情緒得分）。

**報告開始格式:**

---
**{symbol} - 市場分析報告 ({current_time})**
---

**一、整體市場概覽**
   - 短期技術面簡評: ...
   - 長期技術面簡評: ...
   - 新聞情緒總結: (正面/中性/負面)，提及情緒得分和文章數量。

**二、現貨交易建議**
   - 操作建議: ...
   ... (其他現貨細節)

**三、槓桿交易建議 (如適用)**
   - 操作建議: ...
   ... (其他槓桿細節)

**四、主要風險點**
   - ...

---
請開始你的分析。"""
        return prompt

    def _remove_html_tags(self, text: str) -> str:
        """移除HTML標籤"""
        try:
            # import re # Already imported globally
            clean_text = re.sub(r'<[^>]+>', '', text) # Remove HTML tags
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text) # Normalize multiple newlines
            return clean_text.strip()
        except Exception as e:
            print(f"移除HTML標籤時出錯: {e}")
            return text # Return original text if error

    def _validate_data(self, data: pd.DataFrame) -> bool:
        """驗證輸入數據的有效性"""
        required_columns = ['Open', 'High', 'Low', 'Close'] # Case-sensitive
        if data.empty:
            print("錯誤: 數據為空")
            return False
        
        # Check for required columns (case-insensitive check then use original case)
        actual_cols = {col.lower(): col for col in data.columns}
        missing_cols = [req_col for req_col in required_columns if req_col.lower() not in actual_cols]

        if missing_cols:
            print(f"錯誤: 缺少必要的列: {missing_cols}. 可用列: {list(data.columns)}")
            return False
        
        # Rename columns to expected case if they are different (e.g. open -> Open)
        # This is important if data source provides lowercase column names
        rename_map = {}
        for req_col in required_columns:
            if req_col.lower() in actual_cols and actual_cols[req_col.lower()] != req_col:
                rename_map[actual_cols[req_col.lower()]] = req_col
        if rename_map:
            print(f"自動重命名列: {rename_map}")
            data.rename(columns=rename_map, inplace=True)


        if len(data) < 10: # Increased minimum for meaningful analysis
            print(f"警告: 數據點太少 ({len(data)} < 10)，可能影響分析質量")
        
        # Check for non-numeric data in OHLC columns
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                print(f"錯誤: 列 '{col}' 包含非數值數據。嘗試轉換...")
                try:
                    data[col] = pd.to_numeric(data[col])
                except ValueError as e:
                    print(f"錯誤: 無法將列 '{col}' 轉換為數值類型: {e}")
                    return False
        return True

    def _prepare_data_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """準備數據摘要，避免發送過多數據 (此方法在N8N流程中可能不直接使用, 但保留作為輔助)"""
        # This method seems to be from a different flow (original single timeframe analysis)
        # It's not directly used by the N8N-style `analyze_trend` method but kept for potential other uses.
        # For N8N flow, data summarization for the prompt happens in `_build_professional_analysis_prompt`.
        print("警告: _prepare_data_summary 被調用，但在N8N流程中可能不是預期行為。")
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
            # ... (rest of the original method, potentially useful for other analysis types) ...
            return summary
        except Exception as e:
            print(f"準備數據摘要時出錯: {e}")
            return {"error": str(e)}


    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算基本技術指標 (此方法在N8N流程中可能不直接使用)"""
        # This method also seems to be from a different flow.
        # In N8N, AI is expected to infer indicators or they'd be calculated and passed differently.
        print("警告: _calculate_technical_indicators 被調用，但在N8N流程中可能不是預期行為。")
        try:
            # ... (original implementation) ...
            return {} # Placeholder
        except Exception as e:
            print(f"計算技術指標時出錯: {e}")
            return {"error": str(e)}

    def _get_key_price_points(self, data: pd.DataFrame) -> list:
        """智能採樣關鍵價格點 (此方法在N8N流程中可能不直接使用)"""
        print("警告: _get_key_price_points 被調用，但在N8N流程中可能不是預期行為。")
        try:
            # ... (original implementation) ...
            return [] # Placeholder
        except Exception as e:
            print(f"獲取關鍵價格點時出錯: {e}")
            return []

    def _extract_trend_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """提取趨勢特徵 (此方法在N8N流程中可能不直接使用)"""
        print("警告: _extract_trend_features 被調用，但在N8N流程中可能不是預期行為。")
        try:
            # ... (original implementation) ...
            return {} # Placeholder
        except Exception as e:
            print(f"提取趨勢特徵時出錯: {e}")
            return {"error": str(e)}

    def _build_prompt(self, data_summary: Dict[str, Any], symbol: str, timeframe: str, detail_level: str = "標準") -> str:
        """構建提示詞 (此方法在N8N流程中不直接使用, _build_professional_analysis_prompt 取代了它)"""
        # This is the prompt builder for the original single timeframe analysis.
        # The N8N-style flow uses `_build_professional_analysis_prompt`.
        print(f"警告: _build_prompt 被調用 ({symbol}, {timeframe})，但在N8N流程中可能不是預期行為。")
        # ... (original implementation, kept for other potential uses) ...
        return "此提示詞來自舊版流程，不應在N8N模式下使用。"


    def _call_gemini_model_with_retry(self, prompt: str) -> str:
        """調用Gemini模型（帶重試機制）"""
        if self.api_key and self.api_key.lower() in ["test", "demo", "測試"]:
            print("檢測到測試模式，使用模擬AI回應...")
            return self._generate_mock_analysis_response(prompt) # Pass prompt for context

        for attempt in range(self.max_retries):
            try:
                print(f"嘗試調用AI模型 (第 {attempt + 1}/{self.max_retries} 次)...")
                # Assuming self.model is already initialized (genai.GenerativeModel or aiplatform.GenerativeModel)
                if hasattr(self.model, 'generate_content'): # Covers both genai and Vertex AI new SDK
                    response = self.model.generate_content(prompt)
                    # Accessing response text varies slightly
                    if hasattr(response, 'text') and response.text: # genai typically has .text
                        return response.text
                    # Vertex AI SDK might have parts and text within parts
                    elif hasattr(response, 'candidates') and response.candidates:
                         if hasattr(response.candidates[0],'content') and hasattr(response.candidates[0].content,'parts') and response.candidates[0].content.parts:
                             return response.candidates[0].content.parts[0].text
                    # Fallback or if structure is different
                    print(f"AI回應結構未知或無文本: {type(response)}. 嘗試 str(response)")
                    return str(response) # Should be improved if this path is hit often
                else:
                    # This case should ideally not be reached if _init_ai_client worked
                    raise ValueError("AI模型未正確初始化或不支持generate_content")

            except Exception as e:
                print(f"第 {attempt + 1} 次調用失敗: {str(e)}")
                traceback.print_exc() # Print full traceback for debugging
                if attempt < self.max_retries - 1:
                    current_delay = self.retry_delay * (2**attempt) # Exponential backoff
                    print(f"等待 {current_delay} 秒後重試...")
                    time.sleep(current_delay)
                else:
                    print("所有重試都失敗了。提供模擬分析作為備用...")
                    return self._generate_mock_analysis_response(prompt) # Pass prompt
        return "AI模型調用徹底失敗，且無法生成模擬回應。" # Should not be reached

    def _generate_mock_analysis_response(self, prompt: str) -> str:
        """生成模擬的分析回應（用於測試和演示）- N8N流程的模擬"""
        # Extract symbol from prompt if possible (it's complex in professional prompt)
        symbol_match = re.search(r"以下是\s*([A-Z0-9]+)\s*的綜合市場數據", prompt)
        symbol = symbol_match.group(1) if symbol_match else "未知代幣"
        current_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        mock_response = f"""---
**{symbol} - 市場分析報告 ({current_time}) (模擬回應)**
---

**一、整體市場概覽**
   - 短期技術面簡評: 模擬數據顯示，市場近期在主要支撐位附近盤整，波動性有所下降。15m圖表可能呈現中性指標。
   - 長期技術面簡評: 日線圖趨勢尚不明朗，價格處於長期均線下方，但未見明顯破位。需關注後續方向。
   - 新聞情緒總結: (中性)，基於模擬的若干新聞文章，整體情緒評分為0.05，顯示市場情緒謹慎。

**二、現貨交易建議**
   - 操作建議: 觀望
   - 信心水平: 中
   - 進場價格區域: 暫不適用
   - 止損參考: 暫不適用
   - 止盈目標區域 (至少2個): 暫不適用
   - 理由: 由於市場趨勢不明顯，且新聞情緒中性，建議保持觀望，等待更明確的市場信號。模擬的RSI可能處於50附近。

**三、槓桿交易建議 (如適用)**
   - 操作建議: 暫不操作
   - 信心水平: 低
   - 建議槓桿倍數: 暫不適用
   - 進場價格區域: 暫不適用
   - 止損參考: 暫不適用
   - 止盈目標區域 (至少2個): 暫不適用
   - 理由: 當前市場缺乏明確方向和波動性，不適合進行高風險的槓桿交易。

**四、主要風險點**
   - 市場可能隨時出現突發消息導致方向選擇。
   - 當前技術指標未提供一致信號。

---
**注意:** 此為模擬分析回應，僅用於功能演示或API調用失敗時的備案。請勿作為真實交易依據。
"""
        return mock_response.strip()


    def _call_gemini_model(self, prompt: str) -> str:
        """舊版調用Gemini模型方法（保留以防萬一，但不應在新流程中使用）"""
        print("警告: _call_gemini_model (舊版) 被調用。")
        return self._call_gemini_model_with_retry(prompt) # Redirect to new retry logic

    def _format_response(self, analysis_text: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """格式化模型回應"""
        try:
            cleaned_response = analysis_text.strip()
            if not cleaned_response or len(cleaned_response) < 50: # Basic check for empty/too short response
                cleaned_response = f"AI分析回應過短或無效 ({symbol} {timeframe})。請檢查API配置或重試。原始回應長度: {len(analysis_text)}"
                status = "error_short_response"
            else:
                status = "success"

            return {
                "analysis_text": cleaned_response,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "timeframe": timeframe, # For N8N, this is "多時間框架"
                "status": status,
                "word_count": len(cleaned_response.split()) # More accurate word count
            }
        except Exception as e:
            print(f"格式化回應時出錯: {e}")
            return {
                "analysis_text": f"格式化分析結果時發生錯誤: {str(e)}",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "error"
            }