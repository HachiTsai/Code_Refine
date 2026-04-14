"""
🧠 Intelligence Navigator: Behavior BLS Engine (v1.0)
============================================================
職責：模擬日立 EX-N01A BLS (簡易運算) 的邏輯執行與數據搬運。
邏輯來源：5_BLS.md 與 BLxxx_core.json。
美學：遵循 Aesthetic Hardening v2.0 規範。
"""

import re

class HitachiBLSSimulator:
    """模擬 BLS 腳本執行"""
    def __init__(self, bls_data):
        self.bls_no = bls_data.get("bls_no")
        self.statements = bls_data.get("statements", [])
        self.is_active = True

    def execute(self, global_registry):
        """
        執行所有 Statements 並更新全域暫存器。
        global_registry: 包含所有位號狀態的字典 (e.g., {"TICA301.SV": 70.0})
        """
        if not self.is_active:
            return global_registry

        for stmt in self.statements:
            raw = stmt.get("raw", "")
            if "=" in raw and "/*" not in raw[:2]:
                # 解析賦值語句 a = b
                # 處理 a = b /*comment*/ 這種格式
                clean_raw = re.sub(r'/\*.*?\*/', '', raw).strip()
                if "=" in clean_raw:
                    left, right = clean_raw.split("=")
                    left = left.strip()
                    right = right.strip()
                    
                    # 執行搬運：從全域狀態中讀取 right，寫入 left
                    if right in global_registry:
                        global_registry[left] = global_registry[right]
                    elif re.match(r'^-?\d+(\.\d+)?$', right): # 處理常數賦值
                        global_registry[left] = float(right)
        
        return global_registry
