# ==========================================
# 🏗️ Note Manager Utilities (v16.9: Dynamic Client Mapping)
# 職責：提供 note-manager 技能的標準化工具組，包含動態 Client 解析與路徑對稱。
# ==========================================

__version__ = "v16.9 (Dynamic Client Mapping)"

import os
import sys
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

# ==========================================
# 🏗️ Core Logic: NoteRoutingMaster (SSoT)
# ==========================================
class NoteRoutingMaster:
    MAP = {
        "LP": {"category": "ddc_logic", "sub_dir": "DDC", "spec_id": "spec-analyze-ddc", "tag": "ddc_logic"},
        "US": {"category": "seq_logic", "sub_dir": "SEQ", "spec_id": "spec-analyze-seq", "tag": "seq_logic"},
        "MPN": {"category": "seq_logic", "sub_dir": "SEQ", "spec_id": "spec-analyze-seq", "tag": "seq_logic"},
        "BL": {"category": "bls_logic", "sub_dir": "BLS", "spec_id": "spec-analyze-bls", "tag": "bls_logic"}
    }

    @classmethod
    def get_info(cls, loop_id: str) -> Dict[str, str]:
        upper_id = loop_id.upper()
        prefix = ""
        if upper_id.startswith("LP"): prefix = "LP"
        elif upper_id.startswith("US"): prefix = "US"
        elif upper_id.startswith("MPN"): prefix = "MPN"
        elif upper_id.startswith("BL"): prefix = "BL"
        info = cls.MAP.get(prefix, cls.MAP["LP"]).copy()
        if prefix in ["US", "MPN"]:
            info["core_pattern"] = f"*{upper_id}*_core.json"
        elif prefix == "BL":
            if re.search(r'S\d{2}', upper_id):
                info["core_pattern"] = f"*{upper_id}*_core.json"
            else:
                base_num = re.search(r'\d+', upper_id)
                info["core_pattern"] = f"*BL{base_num.group()}*_core.json" if base_num else f"*{upper_id}*_core.json"
        else:
            info["core_pattern"] = f"{upper_id}*_core.json"
        return info

# ==========================================
# 🏗️ Core Logic: NotePathResolver (v17.0: Cross-Skill Context Aware)
# ==========================================
# 職責：標準化路徑解析器。支援從 Navigator 共享的 context_cache.json 中讀取最後使用的 site資訊。
# 邏輯優先級：CLI 參數 > Navigator Cache > 硬編碼預設。
# ==========================================

class NotePathResolver:
    def __init__(self, client: Optional[str] = None, site: Optional[str] = None, unit: str = "MLC01"):
        self.project_root = self._find_root()
        self.cache_path = self.project_root / ".gemini/skills/intelligence-navigator/references/context_cache.json"
        
        # 1. 載入共享暫存
        cached = self._load_context_cache()
        
        # 2. 確定當前上下文
        self.client = client or cached.get("client") or "RCMT"
        self.site = site or cached.get("site") or "Johor"
        self.unit = unit

    def _find_root(self) -> Path:
        curr = Path(__file__).resolve()
        for parent in curr.parents:
            if (parent / "GEMINI.md").exists(): return parent
        return Path(os.getcwd()).resolve()

    def _load_context_cache(self) -> Dict[str, str]:
        """讀取由 Intelligence Navigator 維護的共享暫存"""
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception: return {}
        return {}

    def _resolve_client_folder(self) -> str:
        """動態解析具備索引前綴的 Client 資料夾 (例如 RCMT -> 1_RCMT)"""
        kb_hitachi_root = self.project_root / "20_Knowledge_Base" / "1_Hitachi_EX-N01A"
        if not kb_hitachi_root.exists():
            return self.client
        
        # 尋找後綴匹配的資料夾 (無視大小寫)
        target = self.client.upper()
        for folder in kb_hitachi_root.iterdir():
            if folder.is_dir():
                # 匹配模式: [Index]_[Client] 或單純 [Client]
                folder_name = folder.name.upper()
                if folder_name == target or folder_name.endswith(f"_{target}"):
                    return folder.name
        
        return self.client

    @property
    def core_root(self) -> Path:
        return self.project_root / "_assets" / "30_Digital_Twin" / "core" / self.client / self.site / self.unit

    @property
    def kb_root(self) -> Path:
        # 動態解析 Client 層級資料夾名稱
        client_folder = self._resolve_client_folder()
        return self.project_root / "20_Knowledge_Base" / "1_Hitachi_EX-N01A" / client_folder / self.site / self.unit
    
    @property
    def raw_root(self) -> Path:
        return self.project_root / "_assets" / "00_Raw" / self.client / self.site / self.unit

# ==========================================
# 🏗️ Core Logic: NoteIOGuard
# ==========================================
class NoteIOGuard:
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Win32 合規檔名清洗 (v1.2)：
        1. 移除前後空白
        2. 空格 -> 底線 '_'
        3. 違規符號 (\\ / : * ? " < > |) -> 短橫線 '-'
        4. 限制長度為 40 字元
        """
        if not name: return "UNKNOWN"
        # 1. 先移除前後空白與不可見字元
        name = "".join(c for c in name if c.isprintable()).strip()
        # 2. 處理空格轉底線
        name = name.replace(" ", "_")
        # 3. 處理非法字元轉短橫線
        name = re.sub(r'[\\/:*?"<>|]', '-', name)
        # 4. 移除末尾點或空格並限制長度
        return name.rstrip(". ")[:40]

    @staticmethod
    def safe_read(file_path: Path) -> str:
        return file_path.read_text(encoding='utf-8')

    @staticmethod
    def safe_write(file_path: Path, content: str):
        file_path.write_text(content, encoding='utf-8')

# ==========================================
# 🏗️ Core Logic: AuditProtocols
# ==========================================
class AuditProtocols:
    @staticmethod
    def check_placeholders(content: str) -> List[str]:
        errors = []
        forbidden = ["AGENT 補充", "請AGENT補充", "[待注入]", "PENDING", "[補充關鍵字]"]
        for p in forbidden:
            if p in content:
                errors.append(f"❌ 偵測到未填寫佔位符: '{p}'")
        return errors

    @staticmethod
    def compare_counts(id: str, raw: int, core: int, label: str = "Blocks"):
        print(f"   🔹 Raw Data:  {label}={raw}")
        print(f"   🔹 Core Data: {label}={core}")
        if raw > 0 and raw != core:
            print(f"   🛑 [QA 報警] {id} {label} 數量不一致！物理偏移={raw - core}")
            return False
        print(f"   ✅ [ZERO OMISSIONS CHECK PASSED]")
        return True
