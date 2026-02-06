import asyncio
import logging
import os
import sys
import argparse
from datetime import datetime

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.quant.runner import QuantRunner
from src.quant.strategy_manager import StrategyManager
from src.quant.data_storage import DataStorage
from src.quant.monitor import RealTimeMonitor
from src.config import setup_env
from data_provider.efinance_fetcher import EFinanceFetcher # Use efinance for history

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_update_data(stocks):
    """单独的数据更新任务"""
    print(f"Updates local data for: {stocks}")
    storage = DataStorage()
    fetcher = EFinanceFetcher()
    
    for code in stocks:
        print(f"Downloading {code} ...")
        try:
            # 下载最近 2 年数据
            df = fetcher.get_history_data(code, start_date="20240101", end_date="20261231")
            if df is not None and not df.empty:
                storage.save_history(code, df)
                print(f"Saved {len(df)} records.")
            else:
                print("No data found.")
        except Exception as e:
            print(f"Error: {e}")

async def run_backtest_ui():
    """交互式回测与策略生成"""
    runner = QuantRunner()
    st_mgr = StrategyManager()
    
    while True:
        print("\n" + "="*40)
        print("1. 生成并回测新策略 (LLM)")
        print("2. 查看/管理已保存策略")
        print("3. 退出")
        choice = input("请选择: ")
        
        if choice == '1':
            desc = input("\n请输入策略描述 (例如 'MA5金叉MA20'): ")
            if not desc: continue
            
            print("正在生成代码...")
            code = await runner.build_strategy(desc)
            print(f"\n--- Code ---\n{code}\n------------")
            
            stock = input("输入测试股票代码 (默认 600519): ") or "600519"
            
            # 使用本地数据回测? 还是在线?
            # 为了演示方便，Runner目前逻辑可能需要微调
            # 这里先用在线拉取（run_quant_demo 逻辑），或者应该整合 use DataStorage
            # 简单起见，利用 runner 现有逻辑 (fetch fresh)
            
            print(f"正在回测 {stock}...")
            res = await runner.run_backtest(stock)
            
            if "metrics" in res:
                print("\n回测结果:")
                for k, v in res['metrics'].items():
                    print(f"  {k}: {v}")
                    
                save = input("\n保留此策略? (y/n): ")
                if save.lower() == 'y':
                    name = input("策略名称: ")
                    st_id = st_mgr.add_strategy(name, desc, code)
                    print(f"策略已保存! ID: {st_id}")
            else:
                print(f"回测失败: {res.get('error')}")

        elif choice == '2':
            strategies = st_mgr.list_strategies()
            print(f"\n已保存策略 ({len(strategies)}):")
            for s in strategies:
                status = "🟢" if s['status']=='active' else "🔴"
                print(f"[{s['id']}] {status} {s['name']} : {s['description']}")
            
            print("\n操作: (d:删除, t:切换状态, b:返回)")
            op = input("> ")
            if op.startswith('d '):
                st_mgr.delete_strategy(op.split()[1])
            elif op.startswith('t '):
                # Toggle logic needed
                 pass
        elif choice == '3':
            break

async def run_monitor_mode(stocks):
    """实盘监控模式"""
    print(f"启动实盘监控... 目标: {stocks}")
    monitor = RealTimeMonitor(stock_list=stocks)
    
    # 1. 加载上下文 (History & Strategies)
    monitor.load_context()
    
    print("开始轮询 (Ctrl+C 停止)...")
    try:
        while True:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 扫描行情中...")
            await monitor.run_once()
            
            # 模拟每 60 秒运行一次
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        print("停止监控.")

async def main():
    setup_env()
    
    parser = argparse.ArgumentParser(description="AI Quant Platform")
    parser.add_argument('mode', choices=['data', 'backtest', 'monitor'], help="运行模式")
    parser.add_argument('--stocks', default='600519,000858,601318', help="股票代码列表(逗号分隔)")
    
    args = parser.parse_args()
    stock_list = args.stocks.split(',')
    
    if args.mode == 'data':
        await run_update_data(stock_list)
    elif args.mode == 'backtest':
        await run_backtest_ui()
    elif args.mode == 'monitor':
        await run_monitor_mode(stock_list)

if __name__ == "__main__":
    asyncio.run(main())
