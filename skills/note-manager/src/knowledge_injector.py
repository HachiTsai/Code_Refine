import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# ==========================================
# 💉 Note Manager: Knowledge Injector (v16.6: Standardized Governance)
# ==========================================
# 職責：實現「看著檔案逐一區塊注入」的高度自動化。
# 核心：精確定位 [AGENT 補充] 佔位符並執行智慧織入。
# ==========================================

__version__ = "v16.6 (Standardized Governance)"

class KnowledgeInjector:
    def __init__(self, resolver):
        self.resolver = resolver

    def get_placeholders(self, content: str) -> List[str]:
        """精確抓取檔案中所有的 AGENT 佔位符文字"""
        # 匹配 [AGENT 補充...]
        pattern = r'\[AGENT\s*補充[^\]]*\]'
        matches = re.findall(pattern, content)
        # 匹配 #[補充關鍵字]
        kw_pattern = r'#\[補充關鍵字\]'
        matches.extend(re.findall(kw_pattern, content))
        return list(set(matches))

    def perform_block_injection(self, loop_id: str, injection_map: Dict[str, str]) -> bool:
        """[Sovereign Injection] 看著檔案逐一區塊注入"""
        route = self.resolver.get_routing_info(loop_id)
        md_file = self.resolver.get_kb_file_path(loop_id, route['tag'])
        if not md_file.exists(): return False

        content = md_file.read_text(encoding='utf-8')
        for placeholder, replacement in injection_map.items():
            if placeholder in content:
                content = content.replace(placeholder, replacement)
        
        # 寫入前執行清理
        content = self.repair_obsidian_links(content)
        md_file.write_text(content, encoding='utf-8')
        print(f"✨ [Injector] 已完成位號 {loop_id} 的區塊化智慧注入。 সন")
        return True

    def verify_asset(self, loop_id, content, info):
        """資產品質門禁 (v16.1: Enforced Physical Alignment)"""
        errors = []
        
        # 1. 基礎內容攔截 (嚴禁任何形式的省略)
        omission_patterns = ["...", "…", "省略", "redundant", "too long"]
        for p in omission_patterns:
            if p in content.lower():
                errors.append(f"❌ [QA 攔截] 偵測到非法省略標記 '{p}'。請補全 100% 物理原始碼，嚴禁縮減數據。")
        
        p_list = self.get_placeholders(content)
        if p_list:
            errors.append(f"❌ [QA 攔截] 偵測到 {len(p_list)} 處未填寫的 [AGENT 補充] 佔位符。")

        # 2. 物理數量對齊審計 (Alignment Audit)
        # 從 info (由 resolver.resolve_core_data 提供) 獲取邏輯指標
        raw_data = info.get("raw_data", {})
        metadata = raw_data.get("metadata", {})
        audit = metadata.get("logic_audit", {})
        
        # [v16.7 Hardening] 區分 SEQ 與 DDC 的審計邏輯
        loop_type = info.get("category", "")
        
        if "ddc" in loop_type.lower():
            # DDC 審計：檢查 Blocks 數量
            expected_total = len(raw_data.get("blocks", []))
            # 針對 DDC 表格特徵過濾
            table_rows = re.findall(r'^\|(?!\s*[:\-]+\s*\|).+\|$', content, re.MULTILINE)
            data_rows = [row for row in table_rows if not any(hk in row for hk in ["BNO", "FNO", "FNM", "工程意圖"])]
        else:
            # SEQ 審計：計算不重複的邏輯條數 (同 Logic No + Expression 算一條)
            # 1. Always (物理輸出通常不重複)
            expected_total = len(raw_data.get("always", []))
            
            # 2. Shift (處理併項計數)
            shift_data = raw_data.get("shift") or raw_data.get("pattern", [])
            unique_shifts = set()
            for item in shift_data:
                l_no = item.get("LOGIC_NO") or item.get("logic_no") or "N/A"
                l_expr = item.get("LOGIC") or item.get("logic") or "N/A"
                unique_shifts.add((l_no, l_expr))
            expected_total += len(unique_shifts)
            
            # 3. Correction (處理併項計數)
            corr_data = raw_data.get("correction") or raw_data.get("corrections", [])
            unique_corrs = set()
            for idx, item in enumerate(corr_data, 1):
                if "logic" in item:
                    l_no = item["logic"].get("logic_no", str(idx))
                    l_expr = item["logic"].get("raw_full", "N/A")
                else:
                    l_no = item.get("logic_no", str(idx))
                    l_expr = item.get("expression") or item.get("logic_content") or item.get("condition") or "N/A"
                unique_corrs.add((l_no, l_expr))
            expected_total += len(unique_corrs)

            table_rows = re.findall(r'^\|(?!\s*[:\-]+\s*\|).+\|$', content, re.MULTILINE)
            header_keywords = ["Logic No", "輸出位號", "Target", "原始碼", "應用步序", "NEXT", "工程意圖", "Engineering Intent"]
            data_rows = [row for row in table_rows if not any(hk in row for hk in header_keywords)]
        
        if expected_total > 0:
            actual_count = len(data_rows)
            if actual_count < expected_total:
                errors.append(f"🛑 [QA 報警] 物理對齊失敗！核心預期 {expected_total} 條邏輯/區塊，Markdown 僅包含 {actual_count} 條。")
                errors.append("   👉 請補全所有遺漏的物理條目，嚴禁為了美觀而省略數據。")

        return errors

    def repair_obsidian_links(self, content: str) -> str:
        """自動修復連結格式 [[ID]] -> **[ID]**"""
        return re.sub(r'\[\[(.*?)\]\]', r'**[\1]**', content)

    def sync_to_core(self, loop_id, expert_insight, all_facts):
        """同步回數位核心"""
        route = self.resolver.get_routing_info(loop_id)
        target_dir = self.resolver.core_data_base / route["sub_dir"]
        core_files = list(target_dir.glob(route["core_pattern"]))
        if not core_files: return False
        
        data = json.loads(core_files[0].read_text(encoding='utf-8'))
        if "metadata" not in data: data["metadata"] = {}
        if expert_insight: data["metadata"]["expert_insight"] = expert_insight
        
        MAP_SPECIAL = {"summary": "summary", "importance": "importance", "process": "process_tags", "interlock": "interlock_refs", "signals": "signals"}
        for key, val in all_facts.items():
            target_key = MAP_SPECIAL.get(key.lower(), key.lower())
            data["metadata"][target_key] = val
            
        core_files[0].write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        return True

    def clean_empty_sections(self, content: str) -> str:
        """自清除機制：移除標記為無邏輯的空區塊（包含其 Markdown 標題）"""
        patterns = [
            r'### 1\.1 階段與時間軸劃分[^\n]*\n+\*本序列無 Process 邏輯\*\n*',
            r'### 1\.2 輸出矩陣深度解碼[^\n]*\n+\*本序列無 Pattern 邏輯\*\n*',
            r'### 1\.3 ALWAYS 邏輯表[^\n]*\n+\*本序列無 Always 邏輯\*\n*',
            r'### 1\.4 CORRECTION 邏輯表[^\n]*\n+\*本序列無 Correction 邏輯\*\n*'
        ]
        for p in patterns:
            content = re.sub(p, '', content)
        return content

    def sync_back_from_md(self, loop_id):
        """從 Markdown 同步回 Core (帶有攔截邏輯與自清除)"""
        md_file = self.resolver.get_kb_file_path(loop_id, "")
        if not md_file.exists(): return False
        content = md_file.read_text(encoding='utf-8')
        
        # --- 🧹 執行自清除機制 ---
        cleaned_content = self.clean_empty_sections(content)
        if cleaned_content != content:
            content = cleaned_content
            md_file.write_text(content, encoding='utf-8')
            print("   🧹 [自清除機制] 已移除無邏輯數據的空白章節。")
        
        info = self.resolver.resolve_core_data(loop_id)
        qa_errors = self.verify_asset(loop_id, content, info)
        if qa_errors:
            print(f"\n🛑 [QA 攔截] {loop_id} 偵測到品質異常：")
            for err in qa_errors: print(f"   {err}")
            
            # --- 🤖 互動式放行機制 ---
            choice = input(f"\n⚠️  [USER_DECISION] 是否忽略以上 QA 錯誤並強行同步 {loop_id}？(y/N): ").strip().lower()
            if choice != 'y':
                print(f"❌ [同步取消] 使用者拒絕放行 {loop_id}。")
                return False
            else:
                print(f"🔓 [強制放行] 已由使用者授權忽略 QA 錯誤。")

        all_facts = {}
        for key, val in re.findall(r'^(\w+)::\s*(.*)', content, re.MULTILINE):
            all_facts[key.strip()] = val.strip()
        
        analysis_match = re.search(r'## 🧭 深度邏輯解析\s*(.*?)(?=\n---|$\n##)', content, re.DOTALL)
        deep_analysis = analysis_match.group(1).strip() if analysis_match else ""
        
        print(f"   -> Back-syncing {loop_id} intelligence to core JSON...")
        return self.sync_to_core(loop_id, expert_insight=deep_analysis, all_facts=all_facts)

def _run_self_diagnostic():
    print("\n🔍 [Self-Diagnostic] 驗證 Infiltrator 注入引擎...")
    try:
        try:
            from .core_resolver import CoreResolver
        except (ImportError, ValueError):
            import sys
            sys.path.append(str(Path(__file__).resolve().parent))
            from core_resolver import CoreResolver
            
        resolver = CoreResolver(unit_id="MLC02")
        injector = KnowledgeInjector(resolver)
        test_md = "Summary:: [AGENT 補充] \n### 1.1 [AGENT 補充：測試]"
        placeholders = injector.get_placeholders(test_md)
        if len(placeholders) == 2:
            print("   ✅ 佔位符偵測精確。")
        else:
            raise ValueError(f"偵測失敗，數量: {len(placeholders)}")
        print("✨ [Self-Diagnostic] 驗證完成。\n")
    except Exception as e:
        print(f"🚨 [Self-Diagnostic] 失敗: {e}")

if __name__ == "__main__":
    _run_self_diagnostic()
