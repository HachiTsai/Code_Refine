import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

try:
    from .note_utils import NoteRoutingMaster, NoteIOGuard, AuditProtocols
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from note_utils import NoteRoutingMaster, NoteIOGuard, AuditProtocols

# ==========================================
# 🏗️ Note Manager: SEQ Engine (v17.5: Logic Sync)
# 職責：生成與 ex-n01a-engine v6.8 同步的 SEQ 筆記。
# 版本演進：
#   v17.5: 同步布林邏輯閘 (&) 與 One-Shot (P)/Timer (T) 支持；修正路徑硬編碼缺陷。
#   v17.4: 實施 Lean Metadata。
# ==========================================

__version__ = "v17.5 (Logic Sync)"

class RefineryContract:
    """[v2.2] 邏輯契約：驗證 SEQ 數據誠信、路徑解析與渲染邊界。"""
    @staticmethod
    def validate_logic_item(item: Dict[str, Any]) -> bool:
        return any(k in item for k in ["LOGIC", "logic", "expression", "raw"])

class RawSeqParser:
    """從 Raw TXT 提取邏輯條數，供審計使用 (v2.0: Robust Scanner)"""
    @staticmethod
    def parse_counts(txt_path: Path) -> Dict[str, int]:
        counts = {"shifts": 0, "corrections": 0}
        current_section = None
        if not txt_path.exists(): return counts

        try:
            # 兼容 Shift-JIS 與 UTF-8
            content = ""
            try:
                content = txt_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = txt_path.read_text(encoding='shift_jis')
            
            for line in content.splitlines():
                line = line.strip()
                if not line: continue
                if '<Shift>' in line: current_section = 'shift'
                elif '<Correction>' in line: current_section = 'corr'
                elif line.startswith('<'): current_section = None

                parts = line.split('\t')
                if current_section == 'shift' and len(parts) >= 5 and parts[0].isdigit():
                    counts["shifts"] += 1
                elif current_section == 'corr' and len(parts) >= 3 and parts[0].isdigit():
                    counts["corrections"] += 1
        except Exception: pass
        return counts

class SeqMarkdownBuilder:
    def __init__(self, resolver):
        self.resolver = resolver

    def get_template(self) -> str:
        """提供具備深度工程引導的標準化 SEQ 筆記骨架 (v17.5 Lean)"""
        return """---
loop_id: {loop_id}
tagno: {tagno}
core_link: {core_link}
service_name: {service_name}
unit: {unit}
status: standardized
tags: [seq_logic, {unit_lower}, hitachi_ex_n01a, {client_lower}, {site_lower}, standardized]
updated: {date}
---

%% DCS_FACTS_START %%
Summary:: {service_name} 主工藝順序。 [AGENT 補充：請用500字以下精煉說明該順序控制的製程目的與範圍]
Importance:: [AGENT 補充：說明此順序在全廠生產中的核心地位，如：反應調度、安全中樞等]
Process:: #反應控制 #主順序 #批次自動化
Interlock:: {interlocks}
Signals:: {signals_str}
%% DCS_FACTS_END %%

> [!INFO] AGENT 深度解析：{loop_id} ({tagno}) 核心主序列架構
>
> {deep_analysis_sections}

---

## 🧭 深度邏輯解析

{dynamic_logic_sections}

---

### 🎯 跨模組全域上下游數據流邏輯鏈結解析

1. **驅動 (Producer) 來源**:
    - [AGENT 補充：例如 由哪個上層順序或手動指令觸發]
2. **影響 (Consumer) 對象**:
    - [AGENT 補充：例如 觸發哪些 DDC 迴路的 SV 切換]
3. **全廠地位**:
    - [AGENT 補充：此順序在整個反應單元中的指揮地位]
"""

    def generate(self, loop_id):
        # ==========================================
        # 🏗️ Core Logic: Data Resolving
        # ==========================================
        loop_id = loop_id.upper()
        info = self.resolver.resolve_core_data(loop_id)
        core_data = info.get("raw_data", {})
        if not core_data: return False

        metadata = core_data.get("metadata", {})
        tagno = metadata.get("TAG", "UNKNOWN")
        service_name = info.get("summary", "Unknown Service")

        # --- 🔗 core_link 處理 ---
        core_path = info.get("path")
        core_link = "N/A"
        if core_path:
            try:
                core_link = str(core_path.relative_to(self.resolver.base_dir)).replace("\\", "/")
            except ValueError: pass

        # --- 🛡️ 動態路徑審計 (Fix Hardcoded Paths) ---
        raw_dir = self.resolver.base_dir / "_assets/00_Raw" / self.resolver.client / self.resolver.site / self.resolver.unit_id / "SEQ"
        raw_file = raw_dir / f"MPN{loop_id[2:5]}{loop_id[5:]}.txt"
        if not raw_file.exists():
            raw_file = raw_dir / f"MPN{loop_id[2:5]}.txt"
        if not raw_file.exists():
            # 嘗試搜尋子目錄 (rglob fallback)
            found = list(raw_dir.rglob(f"MPN{loop_id[2:5]}*.txt"))
            if found: raw_file = found[0]

        raw_counts = RawSeqParser.parse_counts(raw_file)
        core_shift_count = len(core_data.get('pattern', []))
        core_always_count = len(core_data.get('always', []))

        print(f"\n📊 [{__version__} Audit] {loop_id} Logic Consistency Report:")
        AuditProtocols.compare_counts(loop_id, raw_counts['shifts'], core_shift_count, label="Shifts")
        AuditProtocols.compare_counts(loop_id, raw_counts['corrections'], core_always_count, label="Corrections")

        metadata = core_data.get("metadata", {})
        service_name = metadata.get("SERVICE", info.get("summary", "UNKNOWN SERVICE"))

        deep_analysis_parts = []
        logic_section_parts = []

        # 1. Process Section
        if core_data.get("process") or core_data.get("process_timer"):
            deep_analysis_parts.append("### 1. 製程階段與時間軸 (Process & Timeline)\n> [AGENT 補充：說明各個 Process 階段的劃分意圖，以及關鍵 Timer 的監控作用。]")
            rows = [
                "### 1.1 階段與時間軸劃分 (Process/Timer)\n| 序號 (No) | 語義身分 (Description) | 動作區間/設定值 (Active/SV) |",
                "| :--- | :--- | :--- |"
            ]
            for item in core_data.get("process_timer", []):
                rows.append(f"| {item.get('No','N/A')} | {item.get('BPROCNAME','N/A')} | SV: {item.get('SV','N/A')} |")
            logic_section_parts.append("\n".join(rows))
        else:
            print(f"   [Suppressed] Process Section (No Data)")

        # 2. Pattern / Shift Section
        shift_data = core_data.get("shift") or core_data.get("pattern")
        if shift_data:
            deep_analysis_parts.append("### 2. 狀態矩陣與執行策略 (Pattern & Strategy)\n> [AGENT 補充：說明 Pattern 矩陣如何調度實體閥門與子順序。是否採用了分權架構？]")
            rows = [
                "### 1.2 SHIFT 邏輯庫 (Full Shift Logic Library)\n| Logic No | 應用步序 (Applied Steps) | 原始碼布林等式 (Boolean- Logic) | 語義化解析 (Engineering Intent) |",
                "| :--- | :--- | :--- | :--- |"
            ]
            
            logic_map = {}
            for item in shift_data:
                logic_no = item.get("LOGIC_NO") or item.get("logic_no") or "N/A"
                expr_val = item.get("LOGIC") or item.get("logic") or "N/A"
                semantic = item.get("logic_intent") or "[AGENT 補充: 請填寫工程意圖]"
                step = item.get("EXEC") or item.get("step") or "N/A"
                
                key = (logic_no, expr_val, semantic)
                if key not in logic_map: logic_map[key] = []
                if step != "N/A" and step not in logic_map[key]: logic_map[key].append(step)
                    
            for (logic_no, expr_val, semantic), steps in logic_map.items():
                steps_str = ", ".join(steps) if steps else "N/A"
                # 保持 SHIFT 表達式的簡潔渲染
                expr_formatted = f"`{expr_val}`"
                rows.append(f"| **{logic_no}** | Step: {steps_str} | {expr_formatted} | {semantic} |")
            logic_section_parts.append("\n".join(rows))
        else:
            print(f"   [Suppressed] Pattern Section (No Data)")

        # 3. Correction Section
        corrections_data = core_data.get("correction") or core_data.get("corrections")
        if corrections_data:
            deep_analysis_parts.append("### 3. 常時守護與例外覆寫 (Always & Correction)\n> [AGENT 補充：說明 Always 區塊的物理互鎖邏輯，以及 Correction 區塊在特定步驟下的緊急覆寫意圖。]")
            rows = [
                "### 1.3 CORRECTION 邏輯表 (特例覆寫規則)\n| LOGIC NO | 應用步序 (Applied Steps) | 原始碼布林等式 (Boolean- Logic) | 語義化解析 (Engineering Intent) |",
                "| :--- | :--- | :--- | :--- |"
            ]
            for idx, item in enumerate(corrections_data, 1):
                step = item.get("step", "N/A")
                logic_str = item.get("logic", "N/A")
                expr_formatted = "<br>".join([f"`{x.strip()}`" for x in str(logic_str).split(",")])
                rows.append(f"| **{idx}** | Step: {step} | {expr_formatted} | [AGENT 補充: 覆寫意圖] |")
            logic_section_parts.append("\n".join(rows))
        else:
            print(f"   [Suppressed] Correction Section (No Data)")

        # 4. Always Section (v17.5 Sync: 完整表達式渲染)
        if core_data.get("always"):
            if not corrections_data:
                deep_analysis_parts.append("### 3. 常時守護與例外覆寫 (Always & Correction)\n> [AGENT 補充：說明 Always 區塊的物理互鎖邏輯，以及 Correction 區塊在特定步驟下的緊急覆寫意圖。]")

            rows = [
                "### 1.4 ALWAYS 邏輯表 (常時守護神經)\n| 輸出位號 (Target) | 原始碼布林等式 (Boolean- Logic) | 語義化解析 (Engineering Intent) |",
                "| :--- | :--- | :--- |"
            ]
            for item in core_data.get("always", []):
                out_val = item.get("output", "N/A")
                expr_val = item.get("expression", "N/A")
                semantic = item.get("logic_intent") or "[AGENT 補充: 請填寫工程意圖]"
                # v17.5: 不再對 expression 進行分割，保持硬化後的完整布林結構
                expr_formatted = f"`{expr_val}`"
                rows.append(f"| **{out_val}** | {expr_formatted} | {semantic} |")
            logic_section_parts.append("\n".join(rows))
        else:
            print(f"   [Suppressed] Always Section (No Data)")

        content = self.get_template().format(
            loop_id=loop_id,
            tagno=tagno,
            core_link=core_link,
            unit_lower=self.resolver.unit_id.lower(),
            unit=self.resolver.unit_id,
            client_lower=self.resolver.client.lower(),
            site_lower=self.resolver.site.lower(),
            service_name=service_name,
            date=datetime.now().strftime("%Y-%m-%d"),
            interlocks="[AGENT 補充]",
            signals_str="[AGENT 補充]",
            deep_analysis_sections="\n\n".join(deep_analysis_parts),
            dynamic_logic_sections="\n\n".join(logic_section_parts)
        )

        kb_path = self.resolver.get_kb_file_path(loop_id, info.get('tag', 'seq_logic'), suffix=tagno)
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        NoteIOGuard.safe_write(kb_path, content)

        print(f"[SeqEngine] Standardized Note Created: {kb_path.name} ({__version__})")
        return True

def _run_self_diagnostic():
    print(f"\n🔍 [Self-Diagnostic] 啟動 SEQ Engine 審計驗證 ({__version__})...")
    try:
        from core_resolver import CoreResolver
        resolver = CoreResolver(unit_id="MLC01")
        print("   ✅ SEQ Engine 接口與審計組件連通。  ")
    except Exception as e:
        print(f"🚨 [Self-Diagnostic] SEQ Engine 驗證失敗: {e}")

if __name__ == "__main__":
    _run_self_diagnostic()
