import re
import logging
from typing import Optional, Callable
import pandas as pd
import numpy as np
import google.generativeai as genai
from src.config import get_config

logger = logging.getLogger(__name__)

class StrategyGenerator:
    """
    基于 LLM 的量化策略代码生成器
    
    功能:
    将自然语言描述的交易策略转换为标准化的 Python pandas 函数。
    """
    
    def __init__(self):
        self.config = get_config()
        self._setup_gemini()
        
    def _setup_gemini(self):
        """初始化 Gemini API"""
        if self.config.gemini_api_key:
            genai.configure(api_key=self.config.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("Gemini API Key not configured. Strategy generation will not work.")
            self.model = None

    def generate_code(self, description: str) -> str:
        """
        根据自然语言描述生成 Python 策略代码
        
        Args:
            description: 策略描述，如 "当5日均线上穿20日均线时买入，下穿时卖出"
            
        Returns:
            str: 可执行的 Python 代码字符串 (包含 generate_signals 函数)
        """
        if not self.model:
            return "Error: LLM model not initialized."

        prompt = f"""
        You are an expert quantitative developer. Your task is to correct or write a Python function `generate_signals(df)` based on the user's strategy description.

        User Strategy: "{description}"

        ### Input Data Format
        - `df` is a pandas DataFrame.
        - Index: DatetimeIndex (sorted).
        - Columns: 'open', 'high', 'low', 'close', 'volume' (all float).
        
        ### Function Signature
        ```python
        def generate_signals(df: pd.DataFrame) -> pd.Series:
            # ...
        ```
        
        ### Output Requirements
        - Return a **pandas Series** of signals with the same index as `df`:
            - `1`: Long/Buy/Hold
            - `0`: Cash/Empty
            - `-1`: Short/Sell (only if user explicitly asks for shorting, otherwise use 0)
        - Use **vectorized pandas/numpy operations** for performance (avoid loops).
        - Handle NaN values (e.g., from rolling windows) appropriately (usually fill with 0).
        - **Do not** use external libraries like TA-Lib unless absolutely necessary; prefer computing indicators (MA, RSI, MACD) from scratch using pandas `rolling`, `ewm`, etc.
        - **Output ONLY the python code**. Do not include markdown "```python" markers, explanations, or imports.
        - Assume `import pandas as pd` and `import numpy as np` is already done.
        
        ### Example
        If user says "MA5 cross over MA20", generate:
        def generate_signals(df):
            ma5 = df['close'].rolling(window=5).mean()
            ma20 = df['close'].rolling(window=20).mean()
            signal = pd.Series(0, index=df.index)
            signal[ma5 > ma20] = 1
            return signal
        """
        
        try:
            response = self.model.generate_content(prompt)
            code = response.text
            
            # 清理代码
            code = self._clean_code(code)
            return code
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return f"# An error occurred: {str(e)}\ndef generate_signals(df):\n    import pandas as pd\n    return pd.Series(0, index=df.index)"

    def _clean_code(self, code: str) -> str:
        """移除 Markdown 标记和其他非代码内容"""
        code = re.sub(r'```python', '', code, flags=re.IGNORECASE)
        code = re.sub(r'```', '', code)
        return code.strip()

    def compile_strategy(self, code_str: str) -> Optional[Callable]:
        """
        编译生成的代码字符串为可调用函数
        
        注意：使用 exec 有安全风险，仅供本地 Demo 使用。
        """
        try:
            local_scope = {}
            # 预注入依赖
            global_scope = {
                'pd': pd,
                'np': np
            }
            exec(code_str, global_scope, local_scope)
            if 'generate_signals' in local_scope:
                return local_scope['generate_signals']
            else:
                logger.error("Function 'generate_signals' not found in generated code.")
                return None
        except Exception as e:
            logger.error(f"Strategy compilation failed: {e}")
            return None
