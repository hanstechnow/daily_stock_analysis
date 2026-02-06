import asyncio
import logging
import os
import sys
import argparse
from tqdm import tqdm

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.quant.adata_fetcher import ADataFetcher
from src.quant.data_storage import DataStorage
from src.config import setup_env

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def download_all_data(start_date='2008-01-01'):
    """
    下载全市场数据到本地
    """
    fetcher = ADataFetcher()
    storage = DataStorage()
    
    print("正在获取全市场股票列表...")
    codes = fetcher.get_all_stock_codes()
    print(f"获取到 {len(codes)} 只股票。开始下载历史数据 (Start: {start_date})...")
    
    # 使用 tqdm 显示进度条
    pbar = tqdm(codes, desc="Downloading", unit="stock")
    
    success_count = 0
    fail_count = 0
    
    for code in pbar:
        try:
            # 为了避免请求过快被封，可以适当 sleep，但 adata 宣称多源融合且本地代理似乎不需要太担心?
            # 还是安全第一，不做 sleep 用于演示速度，如果报错再加
            df = fetcher.get_history_data(code, start_date=start_date)
            
            if df is not None and not df.empty:
                storage.save_history(code, df)
                success_count += 1
            else:
                fail_count += 1
                
            # 更新进度条描述
            pbar.set_postfix({"Success": success_count, "Fail": fail_count})
            
        except Exception as e:
            fail_count += 1
            logger.debug(f"Error downloading {code}: {e}")
            
    print("\n" + "="*40)
    print(f"下载完成! 成功: {success_count}, 失败: {fail_count}")
    print(f"数据已保存至: {storage.data_dir}")
    print("="*40)

if __name__ == "__main__":
    setup_env()
    
    parser = argparse.ArgumentParser(description="AData Downloader Script")
    parser.add_argument('--start', default='2008-01-01', help="开始日期 (Res format: YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # 异步运行
    asyncio.run(download_all_data(start_date=args.start))
