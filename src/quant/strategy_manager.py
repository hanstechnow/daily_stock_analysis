import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StrategyManager:
    """
    策略管理器
    
    职责:
    - 存储和管理多个策略 (JSON)
    - 启用/禁用策略
    """
    
    def __init__(self, strategy_file: str = "data/strategies.json"):
        self.strategy_file = strategy_file
        self.strategies = self._load_strategies()
        
    def _load_strategies(self) -> List[Dict]:
        if not os.path.exists(self.strategy_file):
            return []
        try:
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load strategies: {e}")
            return []
            
    def _save_strategies(self):
        # 确保目录存在
        os.makedirs(os.path.dirname(self.strategy_file), exist_ok=True)
        try:
            with open(self.strategy_file, 'w', encoding='utf-8') as f:
                json.dump(self.strategies, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save strategies: {e}")

    def add_strategy(self, name: str, description: str, code: str) -> str:
        """添加新策略"""
        import uuid
        strategy_id = str(uuid.uuid4())[:8]
        new_strategy = {
            "id": strategy_id,
            "name": name,
            "description": description,
            "code": code,
            "created_at": datetime.now().isoformat(),
            "status": "active"  # active, inactive
        }
        self.strategies.append(new_strategy)
        self._save_strategies()
        logger.info(f"Strategy '{name}' added with ID {strategy_id}")
        return strategy_id

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        initial_len = len(self.strategies)
        self.strategies = [s for s in self.strategies if s['id'] != strategy_id]
        if len(self.strategies) < initial_len:
            self._save_strategies()
            logger.info(f"Strategy {strategy_id} deleted.")
            return True
        return False
        
    def toggle_strategy(self, strategy_id: str, new_status: str):
        """切换策略状态"""
        for s in self.strategies:
            if s['id'] == strategy_id:
                s['status'] = new_status
                self._save_strategies()
                return True
        return False

    def get_strategy(self, strategy_id: str) -> Optional[Dict]:
        for s in self.strategies:
            if s['id'] == strategy_id:
                return s
        return None

    def get_active_strategies(self) -> List[Dict]:
        return [s for s in self.strategies if s.get('status') == 'active']

    def list_strategies(self) -> List[Dict]:
        return self.strategies
