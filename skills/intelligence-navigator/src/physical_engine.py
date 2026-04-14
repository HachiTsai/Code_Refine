"""
🧠 Intelligence Navigator: Physical Engine (v1.2)
============================================================
職責：物理數據搜尋與參數提取。支援全量溯源 (Lineage Max)。
美學：遵循 Aesthetic Hardening v2.0 規範。
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    from utils import NavigatorPathResolver, NavigatorStandardizer
except ImportError:
    from .utils import NavigatorPathResolver, NavigatorStandardizer

class PhysicalSearchManager:
    """[Legacy Class Name] 負責物理信號搜尋與溯源"""
    def __init__(self, client: Optional[str] = None, site: Optional[str] = None):
        self.resolver = NavigatorPathResolver(client=client, site=site)

    def search_signal(self, loop_id: str) -> Dict[str, Any]:
        """[Mock Implementation] 搜尋信號物理關聯 (待補全全量溯源)"""
        return {
            "id": loop_id,
            "evidence": {
                "core": {},
                "lineage": {"producers": [], "consumers": []}
            }
        }

    def get_loop_parameters(self, loop_id: str) -> Dict[str, Any]:
        """
        從 core.json 中提取物理配置。
        v5.0: 回傳完整的 core.json 結構 (包含 blocks 陣列)，以支援 Graph VM。
        如果沒有找到檔案，則回傳預設的 PID 參數以維持向下相容。
        """
        sid = loop_id.upper()
        core_files = list(self.resolver.core_base.rglob(f"{sid}*_core.json"))
        
        default_params = {
            'P': 100.0, 'I': 60.0, 'D': 0.0,
            'MH': 100.0, 'ML': 0.0,
            'R1': 1.1, 'R2': 1.1,
            'DRH': 1.1, 'DRL': -1.1,
            'blocks': [] # 確保 graph engine 不會報錯
        }

        if not core_files:
            return default_params

        try:
            with open(core_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 向下相容舊版模擬器，將原本在 parameters 陣列中的參數提煉出來
            raw_params = data.get("parameters", {})
            if isinstance(raw_params, dict):
                mapping = {
                    'P': 'P', 'I': 'I', 'D': 'D',
                    'MH': 'MH', 'ML': 'ML',
                    'R1': 'R1', 'R2': 'R2',
                    'DRH': 'DRH', 'DRL': 'DRL'
                }
                for p_key, json_key in mapping.items():
                    p_data = raw_params.get(json_key, [])
                    if p_data and isinstance(p_data, list):
                        val = p_data[0].get("value")
                        if val is not None:
                            data[p_key] = float(val)
            
            # 確保 default_params 裡的 key 都有
            for k, v in default_params.items():
                if k not in data:
                    data[k] = v

            return data
            
        except Exception as e:
            print(f"⚠️ [Physical Engine] 解析失敗: {e}")

        return default_params

# 向下相容別名
PhysicalEngine = PhysicalSearchManager
