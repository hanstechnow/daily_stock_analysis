import asyncio
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

from src.quant.strategy_manager import StrategyManager
from src.quant.data_storage import DataStorage
from src.quant.llm_strategy import StrategyGenerator # for cleanup
from src.notification import Notifier
from data_provider.base import DataFetcherManager
# 临时引用 akshare 获取实时数据，理想情况应该封装在 DataFetcherManager (TODO: 实现 get_snapshot)
import akshare as ak

logger = logging.getLogger(__name__)

class RealTimeMonitor:
    """
    实盘监控引擎
    
    职责:
    - 周期性轮询全市场/自选股实时行情
    - 将实时数据追加到已加载的历史数据末尾
    - 运行所有激活的策略
    - 触发买卖信号并发送通知
    """
    
    def __init__(self, stock_list: List[str] = None):
        self.stock_list = stock_list if stock_list else []
        self.strategy_mgr = StrategyManager()
        self.data_storage = DataStorage()
        self.notifier = Notifier()
        self.strategy_gen = StrategyGenerator() # Used only for compiling
        
        # 缓存: strategy_id -> compiled_function
        self.compiled_strategies = {}
        # 缓存: stock_code -> history_dataframe (最近 N 天)
        self.history_cache = {}
        
    def load_context(self, days_lookback: int = 100):
        """预加载历史数据和策略"""
        logger.info("Initializing Monitor Context...")
        
        # 1. 编译所有 Active 策略
        active_strategies = self.strategy_mgr.get_active_strategies()
        self.compiled_strategies = {}
        for s in active_strategies:
            func = self.strategy_gen.compile_strategy(s['code'])
            if func:
                self.compiled_strategies[s['id']] = func
        logger.info(f"Loaded {len(self.compiled_strategies)} active strategies.")
        
        # 2. 预加载历史数据
        # 注意：这里需要数据已经是 ready 的。如果本地没有，需要先 update。
        self.history_cache = {}
        for stock in self.stock_list:
            df = self.data_storage.load_history(stock)
            if df is not None and not df.empty:
                # 只保留最近 lookback 天，减小内存开销
                self.history_cache[stock] = df.tail(days_lookback).copy()
            else:
                logger.warning(f"No local history found for {stock}, skipping monitoring until data update.")
        logger.info(f"Loaded history for {len(self.history_cache)} stocks.")

    async def run_once(self):
        """执行一次全流程扫描"""
        if not self.compiled_strategies:
            logger.warning("No active strategies to run.")
            return

        if not self.history_cache:
            logger.warning("No history data loaded.")
            return

        # 1. 获取实时行情 (Snapshots)
        # 优化：批量获取，不要一个个循环
        # 注意：akshare.stock_zh_a_spot_em() 是全市场数据，比较慢但一次性全拿
        # 对于监控少量股票，可以用 individual fetch.
        # 对于 > 100 只，全市场接口可能更合适。
        # 这里假设 stock_list 数量适中，我们尝试批量或模拟批量
        
        logger.info("Fetching real-time data...")
        realtime_data = self._fetch_realtime_snapshot(list(self.history_cache.keys()))
        
        alerts = []
        
        for stock_code, snapshot in realtime_data.items():
            if stock_code not in self.history_cache:
                continue
                
            hist_df = self.history_cache[stock_code]
            
            # 2. 构造合成 DataFrame
            # 如果 snapshot 日期 > hist_df 最后日期 -> append new row
            # 如果 snapshot 日期 == hist_df 最后日期 -> update last row (盘中更新)
            
            snapshot_date = pd.to_datetime(snapshot['date'])
            last_hist_date = pd.to_datetime(hist_df['date'].iloc[-1])
            
            # 使用副本以免污染缓存 (或者可以污染如果是 update)
            # 这里选择每次构造临时 df
            
            if snapshot_date > last_hist_date:
                # Append
                new_row = pd.DataFrame([snapshot])
                # 确保列名对齐
                eval_df = pd.concat([hist_df, new_row], ignore_index=True)
            elif snapshot_date == last_hist_date:
                # Update last row
                eval_df = hist_df.copy()
                # Update values
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    eval_df.at[eval_df.index[-1], col] = snapshot[col]
            else:
                # 历史数据比实时数据还新？(比如周末跑) -> 直接用历史
                eval_df = hist_df.copy()
            
            # 3. 运行策略
            for s_id, strategy_func in self.compiled_strategies.items():
                try:
                    signals = strategy_func(eval_df)
                    if isinstance(signals, pd.Series) and not signals.empty:
                        last_signal = signals.iloc[-1]
                        
                        # 检测信号
                        # 这里简单逻辑：只要是 1 或 -1 就报警 (实际可能需要防抖或仅在变动时报警)
                        # 为了演示，我们假设只报买入(1)
                        if last_signal == 1:
                            strategy_info = self.strategy_mgr.get_strategy(s_id)
                            alerts.append({
                                "stock": stock_code,
                                "price": snapshot['close'],
                                "strategy": strategy_info['name'],
                                "signal": "BUY",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            
                except Exception as e:
                    logger.error(f"Error running strategy {s_id} on {stock_code}: {e}")

        # 4. 发送通知
        if alerts:
            await self._send_alerts(alerts)
            
    def _fetch_realtime_snapshot(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时快照 (全市场批量获取)
        
        返回: Dict[code, {date, open, high, low, close, volume}]
        """
        data_map = {}
        try:
            # Akshare 的 stock_zh_a_spot_em 返回全市场A股实时行情
            # 这是一个一次性接口，比循环请求快得多
            logger.info("Fetching full market snapshot via akshare...")
            spot_df = ak.stock_zh_a_spot_em()
            # 返回列示例: "序号", "代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅", "最高", "最低", "今开", "昨收", "量比", "换手率", "市盈率-动态", "市净率"
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # 使用 set 优化查找速度
            target_codes = set(codes) if codes else None
            
            for row in spot_df.itertuples():
                # 注意：spot_df 是通过 akshare 接口返回的，列名通常是中文
                # akshare返回的dataframe列名即为展示名
                # itertuples返回的行属性名会将中文列名转换为类似 _1, _2 等，或者如果不更名则无法通过属性访问
                # 更稳妥是用 iterrows 或者直接转换 df columns
                
                # 这里我们假设 spot_df.columns 包含中文名，用 getattr 或 dict access
                # 为了性能，转换为 dict records 列表再遍历可能更好，或者直接向量化筛选
                pass 
                
            # 向量化筛选优化：如果指定了 codes，先过滤 dataframe
            if target_codes:
                # 假设 '代码' 列是字符串类型
                spot_df['代码'] = spot_df['代码'].astype(str)
                filtered_df = spot_df[spot_df['代码'].isin(target_codes)]
            else:
                filtered_df = spot_df

            if filtered_df.empty:
                return {}

            # 批量构建结果
            # 需要处理非数值或者异常值 (akshare 有时返回 '-')
            for _, row in filtered_df.iterrows():
                try:
                    code = str(row['代码'])
                    price = float(row['最新价'])
                    
                    # 停牌或异常数据处理
                    if price <= 0:
                        continue
                        
                    data_map[code] = {
                        'date': today_str,
                        'open': float(row['今开']),
                        'high': float(row['最高']),
                        'low': float(row['最低']),
                        'close': price,
                        'volume': float(row['成交量'])  # 注意单位，akshare通常是手
                    }
                except (ValueError, KeyError, TypeError):
                    continue

        except Exception as e:
            logger.error(f"Fetch realtime snapshot failed: {e}")
            
        return data_map

    async def _send_alerts(self, alerts: List[Dict]):
        """合并警报并发送"""
        logger.info(f"Triggered {len(alerts)} alerts!")
        
        # Console output
        print("\n" + "="*30)
        print(f"🚨 监控警报 ({len(alerts)})")
        print("="*30)
        for a in alerts:
            print(f"[{a['time']}] {a['stock']} - {a['strategy']} -> {a['signal']} @ {a['price']}")
        print("="*30 + "\n")
        
        # Email / Notify
        if self.notifier.is_available():
            lines = ["# 🚨 量化交易实时提醒", "", "| 时间 | 标的 | 现价 | 信号 | 策略 |", "|---|---|---|---|---|"]
            for a in alerts:
                lines.append(f"| {a['time']} | {a['stock']} | {a['price']} | {a['signal']} | {a['strategy']} |")
            
            import markdown2
            content_html = markdown2.markdown("\n".join(lines), extras=["tables"])
            self.notifier._send_email("【紧急】量化交易信号提醒", content_html)

