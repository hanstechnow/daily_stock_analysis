import asyncio
import logging
import os
import sys

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.quant.runner import QuantRunner
from src.notification import Notifier
from src.config import setup_env

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    setup_env()
    
    # 1. 模拟用户输入策略
    user_input_strategy = "当MA5上穿MA20时全仓买入，当MA5下穿MA20时全仓卖出"
    print(f"\n[用户]: {user_input_strategy}")
    
    runner = QuantRunner()
    
    # 2. 生成策略代码
    print("\n[系统]: 正在生成量化策略代码...")
    code = await runner.build_strategy(user_input_strategy)
    
    print("-" * 40)
    print("生成的策略代码:")
    print("-" * 40)
    print(code)
    print("-" * 40)
    print("[系统]: 策略代码已编译。")
    
    # 3. 选定测试股票 (茅台, 五粮液)
    # 实际应用中可以是全市场扫描，或者用户自选股
    test_stocks = ['600519', '000858'] # 也可以用 runner.data_manager 获取全市场列表
    
    print(f"\n[系统]: 开始扫描目标股票: {test_stocks} ...")
    results = await runner.scan_market(test_stocks)
    
    print(f"\n[系统]: 扫描完成，发现 {len(results)} 个符合条件的标的 (最近信号为买入).")
    
    # 4. 生成报告
    report_lines = ["# 量化策略扫描报告", "", f"策略描述: {user_input_strategy}", ""]
    
    if results:
        for res in results:
            stock = res['stock']
            metrics = res['metrics']
            report_lines.append(f"## {stock}")
            report_lines.append(f"- 年化收益率: {metrics.get('annual_return', 'N/A')}")
            report_lines.append(f"- 夏普比率: {metrics.get('sharpe_ratio', 'N/A')}")
            report_lines.append(f"- 最大回撤: {metrics.get('max_drawdown', 'N/A')}")
            report_lines.append(f"- 胜率: {metrics.get('win_rate', 'N/A')}")
            report_lines.append("")
        
        print("\n".join(report_lines))
        
        # 5. 发送邮件 (如果有配置)
        notifier = Notifier()
        if notifier._is_email_configured():
            print("\n[系统]: 正在发送邮件通知...")
            try:
                # 使用 notifier 的内部方法发送，或者扩充 notifier 接口
                # 这里为了简单直接调用内部私有方法，实际应该封装
                # notifier._send_email 用的是 markdown 转换后的 html
                import markdown2
                title = "量化策略选股通知"
                content_md = "\n".join(report_lines)
                content_html = markdown2.markdown(content_md, extras=["tables"])
                
                notifier._send_email(title, content_html)
                print("[系统]: 邮件发送成功!")
            except Exception as e:
                print(f"[错误]: 邮件发送失败 - {e}")
        else:
            print("\n[提示]: 未配置邮件发送 (EMAIL_SENDER/EMAIL_PASSWORD)，跳过邮件推送。")
            
    else:
        print("没有发现符合买入条件的股票。")

if __name__ == "__main__":
    asyncio.run(main())
