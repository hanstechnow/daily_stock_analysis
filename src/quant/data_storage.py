import os
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class DataStorage:
    """
    本地数据存储管理器
    
    职责:
    - 保存/读取股票历史数据 (CSV format)
    - 简单的文件系统缓存
    """
    
    def __init__(self, data_dir: str = "data/stock_history"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
    def save_history(self, stock_code: str, df: pd.DataFrame):
        """保存历史数据到 CSV"""
        if df is None or df.empty:
            logger.warning(f"Empty dataframe for {stock_code}, skipping save.")
            return
            
        file_path = os.path.join(self.data_dir, f"{stock_code}.csv")
        try:
            # 保存前确保索引是 setup 的，或者是列
            # 假设 df 有 'date' 列或者 date index
            # 为了统一，我们reset index 保存 'date' 列
            save_df = df.copy()
            if 'date' not in save_df.columns and isinstance(save_df.index, pd.DatetimeIndex):
                 save_df = save_df.reset_index()
                 # 如果reset之后叫 'index'，重命名为 'date'
                 if 'index' in save_df.columns:
                     save_df = save_df.rename(columns={'index': 'date'})
            
            save_df.to_csv(file_path, index=False)
            logger.debug(f"Saved history for {stock_code} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save history for {stock_code}: {e}")

    def load_history(self, stock_code: str) -> Optional[pd.DataFrame]:
        """从 CSV 读取历史数据"""
        file_path = os.path.join(self.data_dir, f"{stock_code}.csv")
        if not os.path.exists(file_path):
            return None
            
        try:
            df = pd.read_csv(file_path)
            # 转换日期列
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
            return df
        except Exception as e:
            logger.error(f"Failed to load history for {stock_code}: {e}")
            return None
            
    def has_data(self, stock_code: str) -> bool:
        return os.path.exists(os.path.join(self.data_dir, f"{stock_code}.csv"))
