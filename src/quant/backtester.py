import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VectorBacktester:
    """
    向量化回测引擎
    
    适合低频策略，基于 pandas 向量化计算，速度快但忽略了交易细节（滑点、撮合等）。
    """
    
    def __init__(self, strategy_func):
        self.strategy_func = strategy_func

    def run(self, df: pd.DataFrame, initial_capital: float = 100000.0, commission: float = 0.0003) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            df: 历史数据 DataFrame (OHLCV)
            initial_capital: 初始资金
            commission: 手续费率 (双向)
            
        Returns:
            Dict: 回测结果统计
        """
        # 深度拷贝以防修改原数据
        data = df.copy()
        
        # 检查必要列
        required_cols = ['open', 'close', 'high', 'low']
        if not all(col in data.columns for col in required_cols):
            logger.error(f"Backtest failed: data missing columns. Has: {data.columns.tolist()}")
            return {}
            
        try:
            # 1. 计算信号
            data['signal'] = self.strategy_func(data)
            
            # 2. 计算持仓 (Position)
            # 假设：信号为1表示持有，0表示空仓。
            # 简单的 shift(1): 今天的信号决定明天的持仓
            data['position'] = data['signal'].shift(1).fillna(0)
            
            # 3. 计算每日收益率
            # 市场收益率
            data['market_ret'] = data['close'].pct_change().fillna(0)
            
            # 策略收益率 = 昨天的持仓 * 今天的市场涨跌幅
            # 不考虑滑点和手续费的基础收益
            data['strategy_ret'] = data['position'] * data['market_ret']
            
            # 4. 考虑手续费
            # 当持仓发生变化时（从0变1，或1变0），产生交易
            data['trade_occurred'] = data['position'].diff().abs().fillna(0)
            # 简单估算：每次换仓产生手续费
            # 手续费 = 1 (100%仓位) * commission
            data['cost'] = data['trade_occurred'] * commission
            
            data['net_strategy_ret'] = data['strategy_ret'] - data['cost']
            
            # 5. 计算资金曲线
            data['equity_curve'] = (1 + data['net_strategy_ret']).cumprod() * initial_capital
            
            # 6. 计算统计指标
            result = self._calculate_metrics(data, initial_capital)
            result['data'] = data # 包含详细数据的 DataFrame
            
            return result
            
        except Exception as e:
            logger.exception(f"Backtest runtime error: {e}")
            return {"error": str(e)}

    def _calculate_metrics(self, data: pd.DataFrame, initial_capital: float) -> Dict[str, Any]:
        """计算夏普比率、回撤等指标"""
        equity = data['equity_curve']
        
        # 总收益率
        total_return = (equity.iloc[-1] - initial_capital) / initial_capital
        
        # 年化收益率 (假设252个交易日)
        days = len(data)
        if days > 0:
            annual_return = (1 + total_return) ** (252 / days) - 1
        else:
            annual_return = 0
            
        # 波动率
        volatility = data['net_strategy_ret'].std() * np.sqrt(252)
        
        # 夏普比率 (无风险利率假设 0.03)
        risk_free_rate = 0.03
        if volatility > 0:
            sharpe_ratio = (annual_return - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0
            
        # 最大回撤
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 胜率 (仅统计产生交易且收益>0的日子吗？低频策略通常统计“交易笔数”，但向量化里比较难精确统计“笔”，这里统计“持仓日胜率”)
        holding_days = data[data['position'] != 0]
        if len(holding_days) > 0:
            win_rate = len(holding_days[holding_days['net_strategy_ret'] > 0]) / len(holding_days)
        else:
            win_rate = 0
            
        return {
            "total_return": total_return,
            "total_return_pct": f"{total_return*100:.2f}%",
            "annual_return": f"{annual_return*100:.2f}%",
            "sharpe_ratio": f"{sharpe_ratio:.2f}",
            "max_drawdown": f"{max_drawdown*100:.2f}%",
            "volatility": f"{volatility*100:.2f}%",
            "win_rate": f"{win_rate*100:.2f}%"
        }
