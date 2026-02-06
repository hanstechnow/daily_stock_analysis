from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio

# 引入我们之前的 quant 模块
from src.quant.strategy_manager import StrategyManager
from src.quant.runner import QuantRunner
from src.quant.monitor import RealTimeMonitor

# 全局单例 Monitor (为了简单，实际应放到 app state)
# ⚠️ 注意: Monitor 需要长时间运行，这里仅作 Demo 
# 实际生产中 Monitor 应是独立进程或后台任务
monitor_instance = RealTimeMonitor()

router = APIRouter()
strategy_mgr = StrategyManager()
runner = QuantRunner()

class StrategyCreateRequest(BaseModel):
    name: str
    description: str
    code: str

class StrategyGenerateRequest(BaseModel):
    description: str

class StrategyUpdateRequest(BaseModel):
    status: str # active / inactive

@router.get("/strategies", response_model=List[dict])
async def get_strategies():
    """获取所有策略"""
    return strategy_mgr.list_strategies()

@router.post("/strategies/generate")
async def generate_strategy(req: StrategyGenerateRequest):
    """根据描述生成策略代码"""
    code = await runner.build_strategy(req.description)
    return {"code": code}

@router.post("/strategies")
async def create_strategy(req: StrategyCreateRequest):
    """保存新策略"""
    strategy_id = strategy_mgr.add_strategy(req.name, req.description, req.code)
    return {"id": strategy_id, "message": "Strategy saved"}

@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """删除策略"""
    success = strategy_mgr.delete_strategy(strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"message": "Deleted"}

@router.patch("/strategies/{strategy_id}/status")
async def update_strategy_status(strategy_id: str, req: StrategyUpdateRequest):
    """切换策略状态"""
    success = strategy_mgr.toggle_strategy(strategy_id, req.status)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # 如果 monitor 正在运行，可能需要 reload
    if monitor_instance:
         # 简单的 reload context 触发更新
        monitor_instance.load_context()
        
    return {"message": f"Status updated to {req.status}"}

@router.post("/monitor/start")
async def start_monitor(background_tasks: BackgroundTasks):
    """启动监控 (Demo用)"""
    # 实际应该检查是否已运行
    # 这里只是演示 API 调用 monitor 逻辑
    return {"message": "Monitor start signal sent (Not fully implemented in API demo)"}
