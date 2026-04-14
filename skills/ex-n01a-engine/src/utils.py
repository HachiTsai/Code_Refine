# Triggering Mode B Test
import re
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Any, Set, List, Dict, Optional, Union, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    # 防止循環導入，僅供類型檢查
    from .utils import PathResolver

# ==============================================================================
# 🛡️ [v2.2] Type Shield & Refinery Contract
# ==============================================================================
__version__ = "v6.7 (Unit-Centric Alignment)"

class RefineryContract:
    """[v2.2] 邏輯契約：驗證位號標準化、路徑解析與 GID/CORE 結構的一致性。"""
    
    @staticmethod
    def validate_standard_id(std_id: str) -> bool:
        """驗證位號是否符合標準化格式：[PREFIX][DIGITS][STATION_SUFFIX]。"""
        # 範例：LP112S02, DI601S01, TM001S02
        pattern = re.compile(r'^[A-Z]{2,3}\d{3,4}[A-Z]*S\d{2}$', re.IGNORECASE)
        if not pattern.match(std_id):
            # 某些全域 GMS 位號可能不帶 Sxx，放行但警告
            if not any(x in std_id for x in ["GMS", "VAL"]):
                print(f"   ⚠️ [Contract] Warning: ID '{std_id}' format deviates from standard [PREFIX][DIGITS][STATION].")
            return False
        return True

    @staticmethod
    def validate_path_mirror(raw: Path, gid: Path, core: Path) -> bool:
        """驗證全管線路徑鏡像是否一致。"""
        # 檢查末端三級 [Client]/[Site]/[Unit] 是否相同
        parts_raw = raw.parts[-3:]
        parts_gid = gid.parts[-3:]
        parts_core = core.parts[-3:]
        if not (parts_raw == parts_gid == parts_core):
            print(f"   ❌ [Contract] Error: Path mirror mismatch!")
            print(f"      RAW : {parts_raw}\n      GID : {parts_gid}\n      CORE: {parts_core}")
            return False
        return True

# ==============================================================================
# 🛠️ Utility Functions
# ==============================================================================

def system_handshake(project_root: Path) -> None:
    """與系統總機握手：自動刷新技能快取並同步核心文件。"""
    manager_path = project_root / ".gemini" / "skills" / "workflow-orchestrator" / "scripts" / "skill_manager.py"
    if manager_path.exists():
        print(f"\n🤝 [Handshake] Synchronizing with Global Orchestrator...")
        try:
            subprocess.run([sys.executable, str(manager_path), "--sync-all"], check=False, capture_output=True)
            print("   ✅ Sync completed.")
        except Exception as e:
            print(f"   ⚠️ Handshake failed: {e}")
    else:
        print("   ⚠️ Orchestrator not found, skipping handshake.")

def trigger_index_rebuild(resolver: 'PathResolver') -> None:
    """[通用連動] 觸發 DCS 索引重建程序。"""
    script_path = resolver.skill_root / "scripts" / "index_builder.py"
    if script_path.exists():
        print(f"\n🔄 [Linkage] Triggering DCS Index Rebuild...")
        try:
            cmd = [
                sys.executable, str(script_path), 
                "--client", resolver.client,
                "--site", resolver.site,
                "--unit", resolver.unit
            ]
            subprocess.run(cmd, check=False)
            print("   ✅ Index rebuild triggered.")
        except Exception as e:
            print(f"   ⚠️ Index trigger failed: {e}")

# ==============================================================================
# 🏷️ ID Standardization Logic
# ==============================================================================

class IDStandardizer:
    """統一 DCS 數位孿生 ID 標準化 (v5.9 - Unit-Centric)"""
    CONTAINER_PREFIXES = [
        "LP", "US", "BL", "SLC", "LC", "LM", "LB", "LS", "BS", "BR", "PE", "BE", 
        "SC", "TR", "IS", "IH", "BP", "FM", "MK", "SN", "CB", "IL", "OF",
        "RE", "QP", "QR", "QH", "QA", "QS", "QM", "QD", "QI", "QK", "QU", "QW", 
        "SS", "SE", "SD", "SU", "PD", "PU", "UE", "TD", "TH", "TU"
    ]
    SIGNAL_PREFIXES = [
        "DI", "DO", "IN", "AI", "AO", "VE", "IE", "PH", "DH", "DL", "PL", "HH", "LL",
        "OG", "UA", "EV", "WB", "GS", "GL", "GR", "WQ", "LG", "DS", "DG", "LA", "IX", "QX", "TM",
        "TS", "TP", "VS", "VD", "VI", "VR", "SB", "GB", "ZA", "ZI", "ZO", "DB", "WS", "WL", "WF"
    ]
    
    STATION_MAP = {
        "MLC01": "S01", "MLC02": "S02", "MLC03": "S03", "MLC04": "S04"
    }

    @staticmethod
    def standardize(raw_id: str, unit: Optional[str] = None) -> str:
        """位號標準化核心邏輯。"""
        if not raw_id: return ""
        clean_id = raw_id.replace('/', '').replace('"', '').upper().strip()
        
        # 1. 預選站點後綴 (plant -> unit)
        station_id = IDStandardizer.STATION_MAP.get(unit.upper()) if unit else None
        if not station_id:
            for u, sid in IDStandardizer.STATION_MAP.items():
                if clean_id.endswith(sid):
                    station_id = sid
                    break
        
        # 2. 避免重複添加
        if station_id and clean_id.endswith(station_id):
            return clean_id

        # 3. 分解 ID
        match = re.match(r'^([A-Z]+)(\d+)([A-Z]*)$', clean_id)
        if not match: return clean_id
        
        prefix, digits, func_suffix = match.group(1), match.group(2), match.group(3)
        
        # 4. 補齊長度
        if prefix in IDStandardizer.CONTAINER_PREFIXES:
            std_id = f"{prefix}{digits.zfill(3)}"
        elif prefix in IDStandardizer.SIGNAL_PREFIXES:
            std_id = f"{prefix}{digits.zfill(4)}"
        else:
            std_id = f"{prefix}{digits}"
            
        final_id = f"{std_id}{func_suffix}"

        # 5. 注入站點後綴並執行契約驗證
        result = f"{final_id}{station_id}" if station_id else final_id
        RefineryContract.validate_standard_id(result)
        return result

class SignalScanner:
    """[v2.2] 訊號掃描器：從 JSON 結構中遞迴提取所有 DCS 位號。"""
    def __init__(self) -> None:
        self.pattern = re.compile(
            r'\b(?:IN|AI|AO|DI|DO|GS|GL|GR|WQ|LG|DS|DG|SLC|US|BL|LP|LA|TM|TS|TP|LC|LM|LB|LS|BS|BR|PE|BE|SC|TR|IS|IH|BP|FM|MK|SN|CB|IL|OF|IE|HH|LL|PH|PL|RE|DH|DL|QP|QR|QH|QA|QS|QM|QD|QI|QK|QU|QW|SS|SE|SD|SU|PD|PU|UE|VS|VD|VI|VR|TD|TH|TU|SB|GB|ZA|ZI|ZO|DB|WB|WS|WL|WF|IX|QX|VA|VE)\d{1,4}(?:[A-Z]*S\d{2})?\b',
            re.IGNORECASE
        )

    def scan(self, data: Any) -> Set[str]:
        found: Set[str] = set()
        if isinstance(data, str):
            matches = self.pattern.findall(data)
            for m in matches: found.add(m.upper())
        elif isinstance(data, list):
            for item in data: found.update(self.scan(item))
        elif isinstance(data, dict):
            meta = data.get("metadata", {})
            if isinstance(meta, dict) and "standardized_tags" in meta:
                found.update(meta["standardized_tags"])
            for key, value in data.items():
                if isinstance(key, str):
                    matches = self.pattern.findall(key)
                    for m in matches: found.add(m.upper())
                found.update(self.scan(value))
        return found

# ==============================================================================
# 🚀 Path Management Logic
# ==============================================================================

class PathResolver:
    """動態路徑管理 (v7.0 Interface Alignment)"""
    def __init__(self, client: str = "RCMT", site: str = "Johor", unit: str = "MLC01") -> None:
        self.client = client
        self.site = site
        self.unit = unit
        self.context_path = Path(client) / site / unit
        
        # 1. 尋找根目錄
        curr = Path(__file__).resolve()
        found_root = None
        for parent in curr.parents:
            if (parent / "GEMINI.md").exists() or (parent / ".git").exists():
                found_root = parent
                break
        self.project_root: Path = found_root if found_root else Path(__file__).resolve().parents[4]

        # 2. 基礎設施路徑
        self.skill_root = self.project_root / ".gemini" / "skills" / "ex-n01a-engine"
        self.ref_base = self.skill_root / "references"
        self.config = self._load_skill_config()
        
        self.unit_suffix: Optional[str] = None
        self.global_scope = False
        self._load_unit_manifest(unit)

        # 3. 資產管線路徑 (Asset Mirror)
        self.raw_base = self.project_root / "_assets" / "00_Raw" / self.context_path
        self.gid_base = self.project_root / "_assets" / "05_GID" / self.context_path
        self.core_base = self.project_root / "_assets" / "30_Digital_Twin" / "core" / self.context_path
        self.index_base = self.project_root / "_assets" / "30_Digital_Twin" / "index" / self.context_path
        self.build_base = self.project_root / "_assets" / "30_Digital_Twin" / "build" / self.context_path
        
        # [v2.2] 路徑契約驗證
        RefineryContract.validate_path_mirror(self.raw_base, self.gid_base, self.core_base)

        # 4. 確保輸出目錄存在
        for p in [self.gid_base, self.core_base, self.index_base, self.build_base]:
            p.mkdir(parents=True, exist_ok=True)

    def _load_skill_config(self) -> Dict[str, Any]:
        config_path = self.skill_root / "config.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding='utf-8'))
            except Exception as e:
                print(f"⚠️ [Config] Failed to load: {e}")
        return {}

    def _load_unit_manifest(self, unit: str) -> None:
        rel_path = self.config.get("references_index", {}).get("unit_manifest", "references/unit_manifest.json")
        manifest_path = self.skill_root / rel_path
        
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                config = manifest.get(unit.upper(), {})
                self.unit_suffix = config.get("unit_suffix")
                self.global_scope = config.get("global_scope", False)
            except Exception as e:
                print(f"⚠️ [Manifest] Failed to load from {rel_path}: {e}")
        
        if self.unit_suffix is None and not self.global_scope:
            match = re.search(r'MLC(\d+)', unit.upper())
            if match: self.unit_suffix = f"S{match.group(1).zfill(2)}"

    def get_raw(self, cat: str, file: str = "") -> Path:
        """獲取 Raw Data 路徑。"""
        if f"POC_{cat.upper()}" == self.context_path.name.upper():
            p = self.raw_base
        else:
            p_std = self.raw_base / "No_Packed" / cat
            p = p_std if p_std.exists() else self.raw_base / cat
        
        if cat.upper() == "SEQ": 
            p_seq = p / "M01"
            if p_seq.exists(): p = p_seq
        return p / file if file else p

    def get_gid(self, cat: str = "", file: str = "") -> Path:
        p = self.gid_base
        if cat and f"POC_{cat.upper()}" != self.context_path.name.upper():
            p = self.gid_base / cat
        p.mkdir(parents=True, exist_ok=True)
        return p / file if file else p

    def get_core(self, file: str = "") -> Path:
        return self.core_base / file if file else self.core_base

    def get_ref(self, filename: str) -> Path:
        return self.ref_base / filename

class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        if not text or "(RESERVE)" in text: return ""
        text = re.sub(r'\?[a-z]', '', text) 
        text = re.sub(r'[^\S\t\n\r]+', ' ', text)
        return text.strip()
