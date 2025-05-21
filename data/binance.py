from binance.client import Client
import pandas as pd
import time
import os
import queue
from datetime import datetime

def fetch_historical_data(
    symbol: str,
    interval: str,
    start_time: int,
    end_time: int,
    output_path: str,
    retries=3,
    delay=1,
    monitor_queue: queue.Queue = None
) -> None:
    """
    下載幣安歷史K線數據並保存為CSV。

    Args:
        symbol (str): 交易對，例如 'BTCUSDT'。
        interval (str): K線時間間隔，例如 '1h'。
        start_time (int): 開始時間 (毫秒時間戳)。
        end_time (int): 結束時間 (毫秒時間戳)。
        output_path (str): CSV 檔案輸出路徑。
        retries (int, optional): 失敗時重試次數。預設為 3。
        delay (int, optional): 重試間隔秒數。預設為 1。
        monitor_queue (queue.Queue, optional): 用於傳遞監控狀態的佇列。預設為 None。
    """
    
    # 初始化API客戶端
    from config.api_keys import BINANCE_API_KEY, BINANCE_API_SECRET
    client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
    
    # 確保輸出目錄存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 獲取數據
    data = []
    current_start = start_time
    total_attempts = 0
    successful_attempts = 0
    failed_attempts = 0
    last_error = None

    # --- 監控更新函數 ---
    def _send_monitor_update():
        if monitor_queue:
            stats = {
                'type': 'binance_fetch_status',
                'symbol': symbol,
                'interval': interval,
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'failed_attempts': failed_attempts,
                'last_error': last_error,
                'timestamp': datetime.now()
            }
            monitor_queue.put(stats)

    # --- 重試迴圈 ---
    for attempt in range(retries):
        total_attempts += 1
        try:
            # --- 內部迴圈獲取所有數據 ---
            while current_start < end_time:
                # 每次獲取最多1000根K線
                # print(f"Fetching {symbol} {interval} from {datetime.fromtimestamp(current_start/1000)}...") # Debug
                klines = client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    startTime=current_start,
                    endTime=end_time,
                    limit=1000
                )
                
                if not klines:
                    break
                    
                data.extend(klines)
                
                # 更新起始時間為最後一根K線的結束時間+1
                current_start = klines[-1][0] + 1
                
                # 避免過快請求
                time.sleep(0.1) # 避免過快請求

            # --- 成功跳出重試迴圈 ---
            successful_attempts += 1
            last_error = None # 清除最後錯誤
            _send_monitor_update() # 發送最終成功狀態
            break # 跳出 for attempt 迴圈

        except Exception as e:
            failed_attempts += 1
            last_error = {
                'attempt': attempt + 1,
                'error_type': type(e).__name__,
                'message': str(e),
                'timestamp': datetime.now()
            }
            print(f"請求失敗 (Attempt {attempt+1}/{retries}): {e}")
            _send_monitor_update() # 發送失敗狀態

            if attempt == retries - 1:
                print(f"達到最大重試次數 ({retries})，放棄下載 {symbol} {interval}。")
                raise # 將最終錯誤向上拋出
            
            print(f"等待 {delay} 秒後重試...")
            time.sleep(delay)
    
    # 轉換為DataFrame
    columns = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ]
    
    df = pd.DataFrame(data, columns=columns)
    
    # 轉換時間戳
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 保存必要字段并统一列名大小写
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df.to_csv(output_path, index=False)
