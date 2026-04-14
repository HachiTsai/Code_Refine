"""
🧠 Intelligence Navigator: Intelligence Hub (v1.9 - Pure Fuel Edition)
============================================================
職責：語義導航數據引擎。提供全維度、全量網羅的物理與語義數據。
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from .utils import NavigatorPathResolver, NavigatorStandardizer
    from .physical_engine import PhysicalSearchManager
    from .expert_consultant import ExpertRAGManager
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from utils import NavigatorPathResolver, NavigatorStandardizer
    from physical_engine import PhysicalSearchManager
    from expert_consultant import ExpertRAGManager

# ==========================================
# 🧠 Intelligence Navigator: Intelligence Hub (v2.0: Type-Aware & Context-Hardened)
# 職責：語義導航數據引擎。提供全維度、全量網羅的物理與日立標準規範對齊數據。
# ==========================================

class IntelligenceHub:
    def __init__(self, client: Optional[str] = None, site: Optional[str] = None):
        self.resolver = NavigatorPathResolver(client=client, site=site)
        self.physical = PhysicalSearchManager(client=client, site=site)
        self.expert = ExpertRAGManager(client=client, site=site)

    def get_full_data(self, loop_id: str) -> Dict[str, Any]:
        """
        [Fuel API] 核心數據收割。
        提供包含「日立標準規範對齊」的全量數據包。
        """
        std_id = NavigatorStandardizer.standardize_id(loop_id)
        
        # 1. 物理數據與全量溯源 (Producers/Consumers)
        phys = self.physical.search_signal(std_id)
        core_data = phys.get('evidence', {}).get('core', {})
        
        # 2. 類別感應查詢 (Type-Aware Context Injection)
        query_context = [std_id]
        compliance_directive = "Standard Engineering Analysis"
        
        if std_id.startswith("LP"):
            # DDC: 提取 FNO 列表作為關鍵字
            fnos = {b.get("fno") for b in core_data.get("blocks", []) if b.get("fno")}
            if fnos: query_context.extend([f"F{f}" for f in fnos])
            compliance_directive = "Hitachi DDC FNO Block Definition & Standard Analysis"
        elif any(std_id.startswith(p) for p in ["US", "MPN", "PN"]):
            # SEQ: 加入步序標準規範
            query_context.append("Hitachi SEQ Step Sequence Standard")
            compliance_directive = "Hitachi SEQ Sequence Logic & Step Transition Analysis"
        elif std_id.startswith("BL"):
            # BLS: 加入聯鎖邏輯矩陣
            query_context.append("Hitachi BLS Interlock Logic Standard")
            compliance_directive = "Hitachi BLS Logical Expressions & Interlock Matrix Analysis"

        # 3. 語義 RAG 檢索 (強化全貌感應)
        full_query = " ".join(query_context)
        semantic = self.expert.execute_consult(full_query)
        
        return {
            "id": std_id,
            "core": core_data,
            "lineage": phys.get('evidence', {}).get('lineage', {}),
            "semantic": semantic,
            "compliance_directive": compliance_directive
        }

    def query(self, loop_id: str) -> Dict[str, Any]:
        """[Integration API] Note-Manager 調用入口"""
        data = self.get_full_data(loop_id)
        
        # [v2.0] 為 Note-Manager 準備具備「強合規約束」的燃料摘要
        data["summary_prompt"] = (
            f"[DCS FUEL v2.0] {data['id']} | "
            f"Lineage: P={len(data['lineage'].get('producers',[]))} C={len(data['lineage'].get('consumers',[]))} | "
            f"Semantic: {len(data['semantic'])} docs. | "
            f"MANDATORY_DIRECTIVE: {data['compliance_directive']}"
        )
        
        return data
