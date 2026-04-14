import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Set

try:
    from .note_utils import NotePathResolver, NoteRoutingMaster, NoteIOGuard
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from note_utils import NotePathResolver, NoteRoutingMaster, NoteIOGuard

# ==========================================
# 🧠 Note Manager: Core Resolver (v16.8: Unit-Centric Alignment)
# ==========================================
# 職責：數位孿生關係解析、智慧燃料注入。
# 語義：實作三層級 (Client/Site/Unit) 路徑解析，並支持 ID 優先之動態推導。
# ==========================================

__version__ = "v16.8 (Unit-Centric Alignment)"

class CoreResolver:
    def __init__(self, client: str = "RCMT", site: str = "Johor", unit_id: Optional[str] = None):
        # 委派路徑解析器 (factory -> site)
        self._path_mgr = NotePathResolver(client=client, site=site, unit=unit_id if unit_id else "MLC01")
        
        self.base_dir = self._path_mgr.project_root
        self.kb_base = self._path_mgr.project_root / "20_Knowledge_Base"
        self.inbox_base = self._path_mgr.project_root / "00_Inbox"
        
        self.client = self._path_mgr.client
        self.site = self._path_mgr.site
        self.unit_id = self._path_mgr.unit
        
        self.unit_kb_root: Path = Path(".")
        self.core_data_base: Path = Path(".")
        self._refresh_paths()

    def _refresh_paths(self):
        """同步更新委派解析器的狀態並刷新路徑"""
        self._path_mgr.unit = self.unit_id
        self._path_mgr.site = self.site
        self._path_mgr.client = self.client
        self.unit_kb_root = self._path_mgr.kb_root
        self.core_data_base = self._path_mgr.core_root

    def _auto_detect_unit(self, loop_id: str) -> bool:
        # ==========================================
        # 📡 Auto-Detection Logic (ID-First)
        # ==========================================
        route = self.get_routing_info(loop_id)
        core_search_root = self.base_dir / "_assets/30_Digital_Twin/core" / self.client / self.site
        
        # 優先規則：從 Sxx 後綴推導 (例如 US050S03 -> MLC03)
        match = re.search(r'S(\d{2})', loop_id.upper())
        if match:
            predicted_unit = f"MLC{match.group(1)}"
            predict_path = core_search_root / predicted_unit / route["sub_dir"]
            if predict_path.exists() and list(predict_path.glob(route["core_pattern"])):
                self.unit_id = predicted_unit
                self._refresh_paths()
                return True

        # 次要規則：暴力搜尋當前 Site 下的所有單元
        if core_search_root.exists():
            for unit_dir in core_search_root.glob("MLC*"):
                if unit_dir.is_dir():
                    target_path: Path = unit_dir / route["sub_dir"]
                    if target_path.exists() and list(target_path.glob(route["core_pattern"])):
                        self.unit_id = unit_dir.name
                        self._refresh_paths()
                        return True
        return False

    def get_loop_type(self, loop_id: str) -> str:
        upper_id = loop_id.upper()
        if upper_id.startswith("LP"):
            return "DDC"
        if any(upper_id.startswith(p) for p in ["US", "MPN", "PN"]): 
            return "SEQ"
        if upper_id.startswith("BL"):
            return "BLS"
        return "UNKNOWN"

    def get_routing_info(self, loop_id: str) -> Dict[str, str]:
        info = NoteRoutingMaster.get_info(loop_id)
        ref_dir = self.base_dir / ".gemini" / "skills" / "note-manager" / "references"
        info["spec_path"] = str(ref_dir / f"{info['spec_id']}.md")
        return info

    def find_global_references(self, loop_id: str, signals: Set[str]) -> Dict[str, List[str]]:
        ref_map = {}
        loop_upper = loop_id.upper()
        search_targets = set(signals)
        if any(loop_upper.startswith(p) for p in ["US", "MPN", "PN"]):
            num_match = re.search(r'\d+', loop_upper)
            if num_match:
                num = num_match.group()
                search_targets.update({f"US{num}", f"MPN{num}", f"PN{num}"})
        else:
            search_targets.add(loop_upper)
        
        if not self.core_data_base.exists(): return {}
        
        # 限定在當前單元目錄內搜尋，提高精度並避免跨站點污染
        for json_file in self.core_data_base.rglob("*_core.json"):
            file_name = json_file.name.upper()
            num_match = re.search(r'\d+', loop_upper)
            if num_match:
                num = num_match.group()
                if re.search(fr'(MPN|US){num}(S\d+)?_core', file_name):
                    continue
            try:
                content = json_file.read_text(encoding='utf-8')
                found_in_this_file = [t for t in search_targets if t in content]
                if found_in_this_file:
                    ref_id = json_file.stem.replace("_core", "")
                    ref_map[ref_id] = found_in_this_file
            except Exception: continue
        return ref_map

    def resolve_core_data(self, loop_id: str) -> Dict[str, Any]:
        loop_id = loop_id.upper()
        
        # [ID-First] 強制優先偵測單元，防止誤載 MLC01 預設資產
        if re.search(r'S\d{2}', loop_id):
            self._auto_detect_unit(loop_id)

        route = self.get_routing_info(loop_id)
        target_dir = self.core_data_base / route["sub_dir"]
        core_files = list(target_dir.glob(route["core_pattern"]))
        
        if len(core_files) > 1:
            exact_match = [f for f in core_files if loop_id in f.name.upper()]
            if exact_match: core_files = exact_match
            else: core_files.sort(key=lambda x: 0 if x.name.startswith("US") else 1)
        
        if not core_files:
            return {"raw_data": {}, "summary": "Unknown", "previous_expert_insight": "", "importance": "Low", "signals": set(), "global_references": {}, "knowledge_keywords": [loop_id], "category": route["category"], "tag": route["tag"]}

        data = json.loads(core_files[0].read_text(encoding='utf-8'))
        metadata = data.get("metadata", {})
        
        summary = ""
        for k, v in metadata.items():
            if k.strip().upper() == "SERVICE":
                summary = str(v).strip()
                break
        
        if not summary:
            raw_comment = data.get("comment", "")
            raw_summary = metadata.get("summary", "")
            summary = raw_comment if raw_comment else raw_summary
            if summary:
                summary = re.sub(r'<!--.*?-->', '', summary).strip()
                summary = summary.split('。')[0].strip()

        if not summary and data.get("blocks"):
            first_block = data["blocks"][0]
            terminals = first_block.get("terminals", {})
            semantic = ""
            if "TERM1" in terminals: semantic = terminals["TERM1"].get("semantic", "")
            else:
                for t_data in terminals.values():
                    if "semantic" in t_data:
                        semantic = t_data["semantic"]
                        break
            if "]" in semantic: summary = semantic.split("]")[-1].strip()
            elif semantic: summary = semantic

        if not summary: summary = "UNKNOWN SERVICE"

        previous_insight = metadata.get("expert_insight", "")
        importance = metadata.get("importance", "Medium")
        
        content_str = json.dumps(data)
        found_signals = re.findall(r'\b[A-Z]{1,4}\d{3,4}[A-Z0-9]*\b', content_str)
        blacklist = ('IN', 'IX')
        signals = {sig for sig in found_signals if not sig.startswith(blacklist)}
        global_refs = self.find_global_references(loop_id, signals)

        intelligence_report = ""
        try:
            nav_src = self.base_dir / ".gemini" / "skills" / "intelligence-navigator" / "src"
            if nav_src.exists():
                if str(nav_src) not in sys.path: sys.path.insert(0, str(nav_src))
                from intelligence_hub import IntelligenceHub 
                hub = IntelligenceHub(site=self.site)
                report = hub.query(loop_id)
                intelligence_report = report.get("summary_prompt", "")
        except Exception as e:
            intelligence_report = f"⚠️ [Intelligence Link] Failed: {e}"

        return {
            "raw_data": data,
            "path": core_files[0],
            "summary": summary,
            "previous_expert_insight": previous_insight,
            "importance": importance,
            "signals": signals,
            "global_references": global_refs,
            "intelligence_report": intelligence_report,
            "knowledge_keywords": [loop_id, summary],
            "category": route["category"],
            "tag": route["tag"],
            "spec_id": route["spec_id"]
        }

    def get_kb_file_path(self, loop_id: str, clean_tag: str, suffix: str = "") -> Path:
        info = self.resolve_core_data(loop_id)
        loop_upper = loop_id.upper()
        unit_suffix = info.get("raw_data", {}).get("metadata", {}).get("unit_suffix", "")
        loop_final = f"{loop_upper}{unit_suffix}" if unit_suffix and "S0" not in loop_upper else loop_upper
        
        # --- 🏷️ 檔名清洗 (v1.2: Win32 Hardened) ---
        if suffix:
            suffix = NoteIOGuard.sanitize_filename(suffix)
        else:
            raw_service = info.get("summary", "")
            suffix = NoteIOGuard.sanitize_filename(raw_service.split('\n')[0].strip())
            
        existing = list(self.unit_kb_root.glob(f"{loop_final}*.md"))
        if existing: return existing[0]
        return self.unit_kb_root / f"{loop_final}_{suffix}.md" if suffix else self.unit_kb_root / f"{loop_final}.md"

def _run_self_diagnostic():
    print("\n🔍 [Self-Diagnostic] 啟動 Core Resolver 邏輯契約檢查...")
    try:
        resolver = CoreResolver(unit_id="MLC02")
        actual = resolver.get_routing_info("LP001")['category']
        if actual != "ddc_logic": raise ValueError(f"路由錯誤: {actual}")
        print("   ✅ 核心路由映射契對齊。")
        print("✨ [Self-Diagnostic] 檢查完成。\n")
    except Exception as e:
        print(f"🚨 [Self-Diagnostic] 驗證失敗: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    _run_self_diagnostic()
