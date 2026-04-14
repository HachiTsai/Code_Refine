import re
import json
from pathlib import Path
from datetime import datetime

try:
    from .note_utils import NoteRoutingMaster, NoteIOGuard
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from note_utils import NoteRoutingMaster, NoteIOGuard

# ==========================================
# 🏗️ Note Manager: BLS Engine (v17.5: Logic Sync)
# 職責：生成高純度、無冗餘且具備物理血緣的 BLS 筆記。
# 版本演進：
#   v17.5: 同步 YAML 欄位標準 (unit, tags)；修正 plant 屬性引用缺陷。
#   v17.4: 實施 Lean Metadata。
# ==========================================

__version__ = "v17.5 (Logic Sync)"

class BlsMarkdownBuilder:
    # 信號分類正則表達式常數
    REGEX_REGISTERS = r'^ (GS|IN)\d+'
    REGEX_LOGIC_UNITS = r'^ (BL|US|LP)\d+'

    def __init__(self, resolver):
        self.resolver = resolver

    def get_template(self) -> str:
        """提供具備深度工程引導的標準化 BLS 筆記骨架 (v17.5 Lean)"""
        return """---
loop_id: {loop_id}
core_link: {core_link}
service_name: {service_name}
unit: {unit}
status: standardized
tags: [bls_logic, {unit_lower}, hitachi_ex_n01a, {client_lower}, {site_lower}, standardized]
updated: {date}
---

%% DCS_FACTS_START %%
Summary:: {service_name} 運算腳本。 [AGENT 補充：精煉說明此 BLS 執行的物理運算任務]
Importance:: [AGENT 補充：說明此腳本在製程中的關鍵性，例如：單一真相閘道 (SSoT Gateway)]
Interlock:: {interlocks}
Signals:: {signals_str}
BLS action:: {bls_action}
%% DCS_FACTS_END %%

> [!INFO] 🚨 AGENT 提煉戰略解析：說明整個控制邏輯的「戰略意義」與「工程意圖」。

## 🧭 BLS 邏輯深度解析

### 1. 運算任務與數據流 (Calculation Tasks)
[🚨 AGENT 戰略解析要求：從「數據流動」與「物理意義」視角，描述此模組如何承接上游 GMS/SEQ 狀態、進行了何種計算折線、並最終注入影響哪個下游目標實體。]

### 2. 核心算法與表達式清單 (Core Algorithms List)
| # | Statement (原始碼) | 語義化解析 (Engineering-Intent) |
| :---: | :--- | :--- |
{statements_table}

### 3. 與 GMS/SEQ 的交握機制 (Interlock & Handshake)
[AGENT 補充：描述此腳本是如何被啟動的 (例如受 IN0xxx 觸發)，以及與 SEQ 的交握關係。]

---

## 🚨 系統協作與安全哲學 (System Collaboration & Safety Philosophy)
> [!IMPORTANT] 💡 為什麼要這樣保護？
> [AGENT 補充：追蹤輸出信號 (如 GSxxx) 的最終去向。若接入 DDC 的 APRO (斜坡產生器) 或判斷邏輯，請揭露其背後的化工機械保護哲學：
> 1. **物理防護**： [AGENT 補充：如黏度過載防護、防扭軸衝擊。]
> 2. **控制防護**： [AGENT 補充：如防電網衝擊、防階躍訊號引發的 PID 震盪。]
> 3. **神級協作**： [AGENT 補充：描述 BLS 與 DDC (如 F14 APRO) 如何完美分工達成平滑控制。]

---

### 🎯 跨模組全域上下游數據流邏輯鏈結解析

1. **驅動 (Producer) 來源 (戰略上位)**:
    - [AGENT 補充：例如 由哪個上層順序或手動指令觸發]
2. **影響 (Consumer) 對象 (戰略下位)**:
    - [AGENT 補充：例如 影響哪些 DDC 迴路的 SV/MV 控制]
3. **全廠地位**:
    - [AGENT 補充：此順序在整個反應單元中的「指揮官」或「防火牆」地位]
"""

    def _format_strategic_signals(self, signals: set) -> str:
        """分類並排序信號：物理位號優先 (R501, SIC501) -> 邏輯暫存器 (GS, IN)"""
        if not signals:
            return "PENDING"

        physical_tags = []
        registers = []
        logic_units = []

        for s in sorted(list(signals)):
            s_upper = s.upper()
            if re.match(self.REGEX_REGISTERS, s_upper):
                registers.append(s)
            elif re.match(self.REGEX_LOGIC_UNITS, s_upper):
                logic_units.append(s)
            else:
                physical_tags.append(s)

        ordered_signals = physical_tags + logic_units + registers
        return ", ".join([f"**[{s}]**" for s in ordered_signals])

    def _build_statements_table(self, statements: list) -> str:
        """從 core.json statements[] 逐一提取並渲染 Markdown 表格列"""
        if not statements:
            return "| - | *（無 Statement 數據）* | [AGENT 補充] |"

        rows = []
        for idx, stmt in enumerate(statements, 1):
            raw_code = stmt.get("raw", "").strip()
            raw_code_md = raw_code.replace("\n", "<br>")
            raw_cell = raw_code_md if raw_code_md else "*（空）*"
            insight_prompt = "[AGENT 補充：說明此 Statement 的工程語義與設計意圖]"
            rows.append(f"| **{idx}** | {raw_cell} | {insight_prompt} |")

        return "\n".join(rows)

    def generate(self, loop_id: str) -> bool:
        """生成具備高度引導性的 BLS 筆記 (v17.5: Logic Sync)"""
        loop_id = loop_id.upper()
        info = self.resolver.resolve_core_data(loop_id)
        core_data = info.get("raw_data", {})

        if not core_data:
            print(f"[BlsEngine] No core data found for {loop_id}")
            return False

        # --- 🔗 core_link 處理 ---
        core_path = info.get("path")
        core_link = "N/A"
        if core_path:
            try:
                core_link = str(core_path.relative_to(self.resolver.base_dir)).replace("\\", "/")
            except ValueError: pass

        # ==========================================
        # 📦 Data Extraction
        # ==========================================
        metadata = core_data.get("metadata", {})
        statements = core_data.get("statements", [])
        comment = core_data.get("comment", "").strip()
        bls_action = core_data.get("action", "").strip()

        # --- 🏷️ SERVICE 欄位處理 (v1.3: Hardened) ---
        service_name = ""
        for k, v in metadata.items():
            if k.strip().upper() == "SERVICE":
                service_name = str(v).strip()
                break
        
        if not service_name:
            service_name = comment if comment else metadata.get("summary", info.get("summary", "UNKNOWN SERVICE"))
        
        # 移除註釋、換行並限制長度
        if service_name:
            service_name = re.sub(r'<!--.*?-->', '', service_name).replace('\n', ' ').strip()
            service_name = service_name.split('。')[0].strip()

        signals_str = self._format_strategic_signals(info.get("signals", set()))
        statements_table_str = self._build_statements_table(statements)

        content = self.get_template().format(
            loop_id=loop_id,
            core_link=core_link,
            unit=self.resolver.unit_id,
            unit_lower=self.resolver.unit_id.lower(),
            client_lower=self.resolver.client.lower(),
            site_lower=self.resolver.site.lower(),
            service_name=service_name,
            date=datetime.now().strftime("%Y-%m-%d"),
            interlocks=info.get("interlocks", "[AGENT 補充]"),
            signals_str=signals_str,
            bls_action=bls_action if bls_action else "N/A",
            statements_table=statements_table_str
        )

        kb_path = self.resolver.get_kb_file_path(loop_id, "bls_logic", suffix=service_name)
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        NoteIOGuard.safe_write(kb_path, content)

        print(f"   ✅ [BlsEngine] Note Created: {kb_path.name} ({len(statements)} statements) ({__version__})")
        return True

def _run_self_diagnostic():
    print("\n🔍 [Self-Diagnostic] 啟動 BLS Engine 契約驗證...")
    try:
        from core_resolver import CoreResolver
        resolver = CoreResolver(unit_id="MLC01")
        print("   ✅ BLS Engine 接口連通。")
    except Exception as e:
        print(f"🚨 [Self-Diagnostic] BLS Engine 驗證失敗: {e}")

if __name__ == "__main__":
    _run_self_diagnostic()
