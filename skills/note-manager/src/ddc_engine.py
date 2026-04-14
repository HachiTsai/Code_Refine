import re
import json
from pathlib import Path
from datetime import datetime

try:
    from .note_utils import NoteRoutingMaster, NoteIOGuard, AuditProtocols
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from note_utils import NoteRoutingMaster, NoteIOGuard, AuditProtocols

# ==========================================
# 🏗️ Note Manager: DDC Engine (v17.6: Protocol Semantic)
# 職責：生成高純度、無冗餘且具備物理血緣的 DDC 筆記。
# 版本演進：
#   v17.6: 將「LaTeX 數學模型」標題更名為「IEC61131-3 協定語義」。
#   v17.5: 同步 YAML 欄位標準 (unit, tags)；修正 plant 屬性引用缺陷。
# ==========================================

__version__ = "v17.6 (Protocol Semantic)"

class DdcMarkdownBuilder:
    def __init__(self, resolver):
        self.resolver = resolver

    def get_template(self) -> str:
        """提供具備深度工程引導的標準化 DDC 筆記骨架 (v17.6)"""
        return """---
loop_id: {loop_id}
tagno: {tagno}
core_link: {core_link}
service_name: {service_name}
unit: {unit}
status: standardized
tags: [ddc_logic, {unit_lower}, hitachi_ex_n01a, {client_lower}, {site_lower}, standardized]
updated: {date}
---

%% DCS_FACTS_START %%
Summary:: 邏輯解析 {service_name}。 [AGENT 補充：請用500字以下摘要精煉說明該迴路的控制標的與策略]
Importance::  [AGENT 補充：說明此迴路在製程中的關鍵性，如：品質關鍵、安全保護等]
Process:: #[補充關鍵字]
Interlock:: [AGENT 補充：此迴路涉及的關鍵安全聯鎖]
Signals:: {signals_str}
%% DCS_FACTS_END %%

> [!INFO] AGENT 深度解析：{loop_id} ({tagno}) 核心控制架構
>
> ### 1. 測量與前置處理 (Measurement & Pre-processing)
> [AGENT 補充：說明感測器輸入的範圍設定與信號處理。]
>
> ### 2. 控制運算與策略 (Control Strategy)
> [AGENT 補充：說明核心控制器的運作模式與策略。]
>
> ### 3. 輸出與安全防護 (Output & Protection)
> [AGENT 補充：說明輸出信號與物理限幅保護。]

---

## 🧭 深度邏輯解析

### 1.1 FNO 功能塊清單 (Functional Blocks)
| BNO | FNO | FNM | 語義化解析 (Engineering Intent) |
| :--- | :--- | :--- | :--- |
{bno_table}

---

### 2. 階梯式控制邏輯鏈 (Phased Logic Chain Analysis)
1. **階段一：數據感知與模式衛兵 (Input & Mode Guarding)**:
    - [AGENT 補充]
2. **階段二：設定值路由與配方策略 (Setpoint Routing & Recipe Logic)**:
    - [AGENT 補充]
3. **階段三：核心大腦與安全監視 (Core Brain & Safety Monitoring)**:
    - [AGENT 補充]
4. **階段四：決策切換與最終執行 (Output Decision & Final Execution)**:
    - [AGENT 補充]

### 3. 智慧分析與工程意圖 (Intelligence Analysis & Rationale)
1. **IEC 61131-3 Syntax**:
    - [AGENT 補充 (此迴路核心控制邏輯,字數500字以上)]
2. **工程深度提問 (Why?)**:
    - [AGENT 補充]

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

        # --- 🔗 core_link 處理 ---
        core_path = info.get("path")
        core_link = "N/A"
        if core_path:
            try:
                core_link = str(core_path.relative_to(self.resolver.base_dir)).replace("\\", "/")
            except ValueError: pass

        blocks = core_data.get("blocks", [])
        metadata = core_data.get("metadata", {})

        # --- 🛡️ 執行物理塊數審計 ---
        audit = metadata.get("logic_audit", {})
        physical_count = audit.get("physical_blocks", 0)
        core_count = len(blocks)

        print(f"\n📊 [{__version__} Audit] {loop_id} Logic Consistency Report:")
        AuditProtocols.compare_counts(loop_id, physical_count, core_count, label="Blocks")

        ROLE_MAP = {
            "ALGC": "**邏輯演算器 (Logic Calculator)**", "ESTS": "**狀態變更器 (Status Changer)**",
            "AINP": "**一般輸入處理 (Input Processor)**", "AROT": "**開平演算器 (Square Root)**",
            "CDEV": "**偏差演算器 (Deviation Calc)**", "CPID": "**核心 PID 控制大腦 (CPID)**",
            "ALMT": "**限幅演算器 (Limiter)**", "COUT": "**輸出處理器 (Output Processor)**",
            "AHLA": "**上下限警報器 (H/L Alarm)**", "AADS": "**加減算器 (Adder/Subtractor)**",
            "AMLD": "**乘除算器 (Multiplier/Divider)**", "ASEL": "**選擇器 (Selector)**",
            "ACON": "**定數產生器 (Constant Gen)**", "ASWH": "**類比開關 (Analog Switch)**",
            "APRO": "**斜坡產生器 (Ramp Generator)**", "ASUM": "**累計計量器 (Totalizer)**",
            "EPAR": "**數據設定器 (Data Setter)**", "ATPR": "**溫壓補正器 (Compensator)**",
            "ACNV": "**函數轉換器 (Function Conv)**", "ALAG": "**慣性延遲器 (Lag/Dead Time)**",
            "ADTC": "**死時補償器 (Dead Time Comp)**", "AFFM": "**前饋模型 (Feedforward)**",
            "ABND": "**不感帶增益器 (Deadband)**", "AMPR": "**程序斜坡產生器 (Program Pattern)**",
            "ASSS": "**緩啟停器 (Slow Start/Stop)**", "AFIL": "**移動平均濾波 (Filter)**",
            "AMMA": "**統計/計時器 (Max/Min/Avg)**", "ARTA": "**變化率檢測器 (Slope Det)**",
            "CRAT": "**比率設定器 (Ratio Setter)**", "CONF": "**ON-OFF 調節器 (Controller)**",
            "CTNF": "**時間比例調節器 (Time Prop)**", "APSM": "**補正脈衝累計 (Pulse Comp)**",
            "CBCH": "**批次計數器 (Batch Counter)**", "EPSV": "**批次數據管家 (Data Manager)**",
            "CGFC": "**品種設定器 (Recipe Setter)**", "CQUE": "**品種預約器 (Recipe Reserver)**",
            "CPOD": "**脈衝輸出處理 (Pulse Out 1)**", "CPOA": "**脈衝輸出處理 (Pulse Out 2)**",
            "CDPF": "**整合偏差 PID (CDPF)**", "AONE": "**單次脈衝檢測 (One-Shot)**",
            "AFBD": "**複合邏輯塊 (Composite)**", "BRPT": "**批次報告器 (Batch Reporter)**",
            "CVLV": "**電動閥操作器 (Valve Op)**"
        }

        bno_rows = []
        found_tag = ""
        for b in sorted(blocks, key=lambda x: x['bno']):
            bno_val = str(b.get("bno", "")).zfill(2)
            fno_val = str(b.get("fno", "")).zfill(2)
            fnm_val = b.get("fnm", "UNKNOWN")
            role_hint = ROLE_MAP.get(fnm_val, "**邏輯運算單元**")

            if fnm_val in ["AINP", "CPID"] and not found_tag:
                term1 = b.get("terminals", {}).get("TERM1", {})
                semantic = term1.get("semantic", "")
                tag_match = re.search(r'\[([A-Z]{2}\d{3,4}[A-Z]*\d*)\]', semantic)
                if tag_match:
                    found_tag = tag_match.group(1)

            bno_rows.append(f"| **{bno_val}** | **F{fno_val}** | **{fnm_val}** | {role_hint} [AGENT 補充] |")

        bno_table_str = "\n".join(bno_rows)
        
        # --- 🏷️ 標籤與語義提取 ---
        raw_service = metadata.get("SERVICE", "").strip()
        raw_tag = metadata.get("TAG", "").strip()
        tagno = raw_tag if raw_tag else "PENDING"
        
        if not raw_service or raw_service.upper() == "UNKNOWN SERVICE":
            service_name = raw_tag if raw_tag else "UNKNOWN SERVICE"
        else:
            service_name = raw_service

        raw_signals = sorted(list(info.get("signals", [])))
        signals_str = ", ".join([f"**[{s}]**" for s in raw_signals]) if raw_signals else "PENDING"

        content = self.get_template().format(
            loop_id=loop_id,
            tagno=tagno,
            core_link=core_link,
            unit=self.resolver.unit_id,
            unit_lower=self.resolver.unit_id.lower(),
            client_lower=self.resolver.client.lower(),
            site_lower=self.resolver.site.lower(),
            service_name=service_name,
            date=datetime.now().strftime("%Y-%m-%d"),
            signals_str=signals_str,
            bno_table=bno_table_str
        )

        # --- 🏷️ 檔名生成 (Filename Strategy: [LOOP]_[TAGNO].md) ---
        kb_path = self.resolver.get_kb_file_path(loop_id, "ddc_logic", suffix=tagno)
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        NoteIOGuard.safe_write(kb_path, content)

        print(f"[DdcEngine] Standardized Note Created: {kb_path.name} ({__version__})")
        return True

def _run_self_diagnostic():
    print("\n🔍 [Self-Diagnostic] 啟動 DDC Engine 審計驗證...")
    try:
        from core_resolver import CoreResolver
        resolver = CoreResolver(unit_id="MLC01")
        print("   ✅ DDC Engine 接口與審計組件連通。")
    except Exception as e:
        print(f"🚨 [Self-Diagnostic] DDC Engine 驗證失敗: {e}")

if __name__ == "__main__":
    _run_self_diagnostic()
