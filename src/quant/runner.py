import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
from src.quant.llm_strategy import StrategyGenerator
from src.quant.backtester import VectorBacktester
# from data_provider.base import DataFetcherManager # 后面需要用这个Manager来获取数据
# 为了简单起见，我们假设外部会传入 DataFetcherManager 或直接用它
from data_provider.base import DataFetcherManager
from src.notification import NotificationChannel

# 如果有邮件发送模块，需要引入。目前 Notification 代码里有 smtplib 逻辑，但封装在函数里。
# 我们可以临时在这里实现一个简单的邮件发送，或者复用 src/notification.py 的逻辑(如果它暴露了接口)

logger = logging.getLogger(__name__)

class QuantRunner:
    """
    量化系统运行入口
    """
    def __init__(self):
        self.strategy_gen = StrategyGenerator()
        self.data_manager = DataFetcherManager()
        # 简单的缓存策略代码
        self.current_strategy_code = None
        self.current_strategy_func = None

    async def build_strategy(self, description: str) -> str:
        """从自然语言构建策略"""
        logger.info(f"Generating strategy from: {description}")
        code = self.strategy_gen.generate_code(description)
        self.current_strategy_code = code
        self.current_strategy_func = self.strategy_gen.compile_strategy(code)
        return code

    async def run_backtest(self, stock_code: str, days: int = 365) -> Dict[str, Any]:
        """对单只股票进行回测"""
        if not self.current_strategy_func:
            return {"error": "No strategy compiled. Please build_strategy first."}
            
        # 获取历史数据
        logger.info(f"Fetching history data for {stock_code}...")
        
        # 注意: get_history_data 的参数和返回需要适配 DataFetcherManager 的接口
        # 假设 DataFetcherManager 有 get_kline 或者 fetch_history
        # 查看 data_provider/base.py，好像没有直接暴露 clean 的 get_kline。
        # 这里可能需要特定 fetcher。为了演示，我们假设用 akshare 或 baostock 
        
        # 临时解决方案：直接调用 efinance_fetcher 或通用的 fetcher 接口
        # DataFetcherManager.get_instance().get_history(...) ?? 
        # 让我们假设我们实例化一个Fetch并用它
        
        fetcher = self.data_manager  # 根据base.py，这可能是一个Manager类？不，base.py里定义了Manager
        
        # 构造日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        try:
            # 尝试获取日线数据
            df = await self._fetch_history_data(stock_code, start_str, end_str)
            if df is None or df.empty:
                 return {"error": f"No data found for {stock_code}"}
                 
            # 运行回测
            backtester = VectorBacktester(self.current_strategy_func)
            result = backtester.run(df)
            
            return {
                "stock": stock_code,
                "metrics": {k: v for k, v in result.items() if k != 'data' and k != 'equity_curve'},
                "last_signal": int(result['data']['signal'].iloc[-1]) if not result['data'].empty else 0
            }
            
        except Exception as e:
            logger.error(f"Backtest failed for {stock_code}: {e}")
            return {"error": str(e)}

    async def scan_market(self, stock_list: List[str]) -> List[Dict]:
        """全市场扫描（或扫描给定列表）"""
        results = []
        for stock in stock_list:
            # 只取最近足够计算指标的数据，比如 100 天
            res = await self.run_backtest(stock, days=200)
            if "error" not in res:
                # 检查最后一个信号
                if res.get("last_signal") == 1:
                    results.append(res)
        return results

    async def _fetch_history_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        辅助函数：获取数据
        需要适配 data_provider 的具体实现。
        """
        # 这里为了确保能跑通，我们直接使用 akshare 或 efinance 如果可能
        # 或者使用 DataFetcherManager 的逻辑。
        # 简单起见，我这里使用 data_provider.efinance_fetcher.EFinanceFetcher
        # 因为它不用配置且速度快
        from data_provider.efinance_fetcher import EFinanceFetcher
        fetcher = EFinanceFetcher()
        
        try:
            # EFinanceFetcher.get_history_data(stock_code, start_date, end_date)
            # 注意：base.py 定义的接口是 get_history_data(stock_code, start_date, end_date, kline_type)
            df = fetcher.get_history_data(stock_code, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"Fetch specific data error: {e}")
            return None
