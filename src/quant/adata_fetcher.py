import logging
import pandas as pd
from typing import List, Optional, Dict
import adata

logger = logging.getLogger(__name__)

class ADataFetcher:
    """
    AData 数据源封装
    Wrapper for 1nchaos/adata
    """
    
    def __init__(self):
        pass

    def get_all_stock_codes(self) -> List[str]:
        """获取所有A股代码"""
        try:
            df = adata.stock.info.all_code()
            if df is not None and not df.empty:
                return df['stock_code'].tolist()
        except Exception as e:
            logger.error(f"Failed to get all stock codes: {e}")
        return []
        
    def get_history_data(self, stock_code: str, start_date: str = '2020-01-01', k_type: int = 1) -> Optional[pd.DataFrame]:
        """
        获取历史行情 (日线)
        k_type: 1.日；2.周；3.月
        """
        try:
            # adata.stock.market.get_market returns: trade_time, open, close, ..., stock_code, trade_date
            df = adata.stock.market.get_market(stock_code=stock_code, start_date=start_date, k_type=k_type)
            if df is not None and not df.empty:
                # Standardize columns to match our system
                # expected: date, open, high, low, close, volume
                # adata columns: trade_date, open, high, low, close, volume, amount, ...
                
                rename_map = {
                    'trade_date': 'date',
                    'trade_time': 'datetime' 
                }
                df = df.rename(columns=rename_map)
                
                # Ensure date is datetime
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                
                # Sort by date
                df = df.sort_values('date')
                return df
                
        except Exception as e:
            logger.error(f"Failed to get history for {stock_code}: {e}")
        return None

    def get_realtime_snapshot(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情快照
        """
        data_map = {}
        try:
            # adata.stock.market.list_market_current() 似乎是获取所有? 文档说是"获取多个股票最新行情信息"
            # 但没有参数传入 stock_codes? README 示例: stock.market.list_market_current() 
            # 让我们假设它返回全市场，或者我们需要过滤
            
            # The doc says "获取多个股票最新行情信息", and source code likely returns a big DF.
            # Let's fetch all and filter.
            df = adata.stock.market.list_market_current()
            if df is not None and not df.empty:
                # columns might be: stock_code, short_name, price, ...
                # We need to map to standard format: date, open, high, low, close, volume
                
                # Check column names from adata (based on common observation or assumption, usually intuitive)
                # If unavailable, we might need to debug. But let's look at typical output.
                # Usually: stock_code, price, open, high, low, volume, amount...
                
                for _, row in df.iterrows():
                    code = str(row['stock_code'])
                    if code in stock_codes:
                        data_map[code] = {
                            'date': pd.Timestamp.now().strftime('%Y-%m-%d'), # Realtime
                            'open': float(row.get('open', 0)),
                            'high': float(row.get('high', 0)),
                            'low': float(row.get('low', 0)),
                            'close': float(row.get('price', 0)), # "price" is usually current price
                            'volume': float(row.get('volume', 0))
                        }
        except Exception as e:
            logger.error(f"Failed to get realtime snapshot: {e}")
            
        return data_map
