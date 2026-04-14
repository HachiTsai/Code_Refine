"""
🧠 Intelligence Navigator: Behavior SEQ Engine (v1.0)
============================================================
職責：模擬日立 EX-N01A Unit Sequence (US) 的步序轉移與 Pattern 輸出。
邏輯來源：4_SEQ.md 與 USxxx_core.json。
美學：遵循 Aesthetic Hardening v2.0 規範。
"""

import re

class HitachiSEQSimulator:
    """模擬 US 步序狀態機"""
    def __init__(self, us_data):
        self.metadata = us_data.get("metadata", {})
        self.patterns = us_data.get("pattern", [])
        self.shifts = us_data.get("shift", [])
        
        self.current_step = 1
        self.step_timer = 0  # 秒
        self.is_active = False

    def _parse_range(self, range_str):
        """解析 11-66 這種格式的步序範圍"""
        if not range_str:
            return []
        if '-' in range_str:
            start, end = map(int, range_str.split('-'))
            return list(range(start, end + 1))
        return [int(range_str)]

    def get_outputs(self):
        """獲取當前步序的所有 active 輸出"""
        active_outputs = {}
        for p in self.patterns:
            addr = p.get("OUTADDR")
            for state in p.get("active_states", []):
                step_range = self._parse_range(state.get("range"))
                if self.current_step in step_range:
                    active_outputs[addr] = state.get("value")
        return active_outputs

    def update(self, dt=1.0, external_signals=None):
        """更新狀態機 (處理步序轉移)"""
        if not self.is_active:
            return
            
        self.step_timer += dt
        
        # 尋找轉移條件 (shift)
        # 註：簡化版僅模擬自動步進或根據外部信號轉移
        for s in self.shifts:
            if int(s.get("No", 0)) == self.current_step:
                # 這裡應解析 s.get("LOGIC")，目前先做時間步進模擬
                pass

    def force_jump(self, step_no):
        """強制跳轉步序"""
        print(f"🔄 SEQ Jump: Step {self.current_step} -> {step_no}")
        self.current_step = step_no
        self.step_timer = 0
