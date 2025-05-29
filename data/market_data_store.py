import pandas as pd
import os
from datetime import datetime
import time
import queue

class MarketDataStore:
    """
    市場數據存儲管理類，使用HDF5格式高效存儲和管理歷史K線數據。
    """
    
    def __init__(self, base_path="./data"):
        """
        初始化市場數據存儲管理器。
        
        Args:
            base_path (str): 數據存儲的基礎路徑
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _get_hdf_path(self, symbol, interval):
        """獲取指定交易對和時間框架的HDF5文件路徑"""
        return os.path.join(self.base_path, f"{symbol}_{interval}.h5")
    
    def get_available_data_range(self, symbol, interval):
        """
        獲取指定交易對和時間框架的可用數據時間範圍。
        
        Returns:
            tuple: (最早時間戳, 最晚時間戳) 或 (None, None) 如果無數據
        """
        file_path = self._get_hdf_path(symbol, interval)
        if not os.path.exists(file_path):
            return None, None
            
        try:
            with pd.HDFStore(file_path, 'r') as store:
                # 檢查是否有數據
                if '/market_data' not in store:
                    return None, None
                    
                # 獲取第一行和最後一行的時間戳
                first_timestamp = store.select('market_data', start=0, stop=1).index[0]
                last_timestamp = store.select('market_data', start=-1, stop=None).index[0]
                
                return first_timestamp, last_timestamp
        except Exception as e:
            print(f"獲取數據範圍時出錯: {e}")
            return None, None
    
    def get_data(self, symbol, interval, start_time, end_time):
        """
        從存儲中獲取指定時間範圍的數據。
        
        Args:
            symbol (str): 交易對符號
            interval (str): 時間框架
            start_time (datetime): 開始時間
            end_time (datetime): 結束時間
            
        Returns:
            pd.DataFrame: 包含請求時間範圍內數據的DataFrame，如果無數據則返回空DataFrame
        """
        file_path = self._get_hdf_path(symbol, interval)
        if not os.path.exists(file_path):
            return pd.DataFrame()
            
        try:
            with pd.HDFStore(file_path, 'r') as store:
                if '/market_data' not in store:
                    return pd.DataFrame()
                
                # 將datetime轉換為pandas timestamp以便查詢
                start_ts = pd.Timestamp(start_time)
                end_ts = pd.Timestamp(end_time)
                
                # 使用where條件查詢指定時間範圍的數據
                data = store.select(
                    'market_data',
                    where=f"index >= '{start_ts}' & index <= '{end_ts}'"
                )
                
                return data
        except Exception as e:
            print(f"獲取數據時出錯: {e}")
            return pd.DataFrame()
    
    def save_data(self, symbol, interval, data):
        """
        保存數據到存儲，合併現有數據並去重。
        
        Args:
            symbol (str): 交易對符號
            interval (str): 時間框架
            data (pd.DataFrame): 要保存的數據
        """
        if data.empty:
            print("沒有數據需要保存")
            return
            
        # 確保數據索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
            else:
                raise ValueError("數據必須有timestamp列或DatetimeIndex索引")
        
        file_path = self._get_hdf_path(symbol, interval)
        
        try:
            # 如果文件已存在，讀取現有數據並合併
            if os.path.exists(file_path):
                with pd.HDFStore(file_path, 'r') as store:
                    if '/market_data' in store:
                        existing_data = store.get('market_data')
                        # 合併數據並按時間排序
                        combined_data = pd.concat([existing_data, data])
                        # 去重，保留最新的數據
                        combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
                        # 按時間排序
                        data = combined_data.sort_index()
            
            # 保存合併後的數據
            with pd.HDFStore(file_path, 'w') as store:
                store.put('market_data', data, format='table', data_columns=True)
                
            print(f"成功保存數據到 {file_path}，共 {len(data)} 行")
            
        except Exception as e:
            print(f"保存數據時出錯: {e}")
            raise
