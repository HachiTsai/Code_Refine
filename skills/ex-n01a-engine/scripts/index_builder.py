import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any

# ==========================================
# 🏗️ Core Logic: DCS Index Builder (v5.7)
# ==========================================
# 職責：數位孿生索引建構。產出相對路徑索引與訊號全域追蹤地圖。
# 語義：建立 DCS 位號間的「血緣關係」與快速查找路由。
# 變更紀錄:
#   v5.7: 將 plant 參數遷移至 unit 以對齊 PathResolver v7.0
# ==========================================

__version__ = "v5.7"

# 🛠️ v6.3 標準：注入技能根目錄，使 src.utils 可被解析
scripts_path = Path(__file__).resolve().parent
skill_root = scripts_path.parent
if str(skill_root) not in sys.path:
    sys.path.insert(0, str(skill_root))

from src.utils import PathResolver, SignalScanner, IDStandardizer, system_handshake

class IndexBuilder:
    def __init__(self, resolver: PathResolver):
        # ==========================================
        # 🗺️ Initialization & Context
        # ==========================================
        self.resolver = resolver
        self.project_root = resolver.project_root

    def build_metadata_index(self) -> List[Dict[str, Any]]:
        """重建 IDX_metadata.json (檔案級元數據)"""
        # ==========================================
        # 📂 File-Level Metadata Harvesting
        # ==========================================
        index_data = []
        core_root = self.resolver.core_base
        for cat in ["DDC", "SEQ", "BLS", "VMD", "ALM"]:
            cat_dir = core_root / cat
            if not cat_dir.exists(): continue
            
            for f in cat_dir.rglob("*.json"):
                rel_path = f.relative_to(self.project_root).as_posix()
                obj_id = f.stem.replace("_core", "").replace("_refined", "")
                index_data.append({
                    "text": f"DCS {cat} object {obj_id} with enriched semantics.",
                    "source": rel_path,
                    "type": "digital_twin_core"
                })
        return index_data

    def build_logic_index(self) -> Dict[str, Any]:
        """重建快速查找字典 (ID -> Path)"""
        # ==========================================
        # 🔍 Logic Routing Map (ID -> Physical Path)
        # ==========================================
        logic_map = {}
        core_root = self.resolver.core_base
        for f in core_root.rglob("*.json"):
            rel_path = f.relative_to(self.project_root).as_posix()
            obj_id = f.stem.replace("_core", "").replace("_refined", "")
            logic_map[obj_id] = rel_path
        return logic_map

    def build_signal_trace_index(self) -> Dict[str, Any]:
        """建立全局訊號追蹤地圖 (Signal Trace Map)"""
        # ==========================================
        # 🧬 Signal Lineage & Trace Discovery
        # ==========================================
        trace_map = {}
        scanner = SignalScanner()
        
        print("[*] Building Signal Trace Map...")
        
        # 1. 掃描 TAG 定義層
        tag_root = self.resolver.gid_base / "TAG"
        if tag_root.exists():
            for f in tag_root.glob("*.json"):
                with open(f, 'r', encoding='utf-8') as f_in:
                    try:
                        data = json.load(f_in)
                        for item in data:
                            sid = item.get("internal_id") or item.get("tag_id")
                            if not sid: continue
                            sid = IDStandardizer.standardize(sid)
                            
                            if sid not in trace_map:
                                trace_map[sid] = {
                                    "name": item.get("tag", ""),
                                    "description": item.get("description", ""),
                                    "defined_in": f.relative_to(self.project_root).as_posix(),
                                    "usages": {}
                                }
                    except: continue

        # 2. 掃描使用地 (DDC, SEQ, BLS, VMD, ALM)
        for cat in ["DDC", "SEQ", "BLS", "VMD", "ALM"]:
            cat_dir = self.resolver.core_base / cat
            if not cat_dir.exists():
                cat_dir = self.resolver.gid_base / cat
            
            if not cat_dir.exists(): continue
            
            for f in cat_dir.rglob("*.json"):
                rel_path = f.relative_to(self.project_root).as_posix()
                with open(f, 'r', encoding='utf-8') as f_in:
                    try:
                        data = json.load(f_in)
                        found_signals = scanner.scan(data)
                        
                        for sid in found_signals:
                            if sid not in trace_map:
                                trace_map[sid] = {
                                    "name": "Unknown",
                                    "description": "Implicit signal found in usage",
                                    "defined_in": None,
                                    "usages": {}
                                }
                            
                            if cat not in trace_map[sid]["usages"]:
                                trace_map[sid]["usages"][cat] = []
                            
                            if rel_path not in trace_map[sid]["usages"][cat]:
                                trace_map[sid]["usages"][cat].append(rel_path)
                    except: continue
        
        return trace_map

    def save_indexes(self):
        # ==========================================
        # 💾 Persistence & Synchronization
        # ==========================================
        index_dir = self.resolver.index_base
        index_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Metadata Index
        metadata = self.build_metadata_index()
        with open(index_dir / "IDX_metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        # 2. Logic Index
        logic = self.build_logic_index()
        with open(index_dir / "IDX_logic.index", 'w', encoding='utf-8') as f:
            json.dump(logic, f, ensure_ascii=False, indent=2)

        # 3. Signal Trace Index
        trace = self.build_signal_trace_index()
        with open(index_dir / "IDX_signal_trace.json", 'w', encoding='utf-8') as f:
            json.dump(trace, f, ensure_ascii=False, indent=2)
            
        print(f"[*] Indexes rebuilt successfully in {index_dir}")
        print(f"    - Metadata entries: {len(metadata)}")
        print(f"    - Logic mapping: {len(logic)}")
        print(f"    - Signal traces: {len(trace)}")
        
        # --- 🤝 Handshake with Global Orchestrator ---
        system_handshake(self.project_root)

def run_indexing(client: str, site: str, unit: str = "MLC01"):
    """
    ==========================================
    🏗️ External Orchestration Entry (Facade)
    ==========================================
    Provides a functional entry point for scripts like unit_refinery.py
    to trigger indexing without subprocessing.
    """
    print(f"[*] Starting DCS Index Build for {client}/{site}/{unit}...")
    resolver = PathResolver(client=client, site=site, unit=unit)
    builder = IndexBuilder(resolver=resolver)
    builder.save_indexes()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DCS Index Builder v5.7")
    parser.add_argument("--client", default="RCMT")
    parser.add_argument("--site", default="Johor")
    parser.add_argument("--unit", default="MLC01")
    args = parser.parse_args()

    resolver = PathResolver(client=args.client, site=args.site, unit=args.unit)
    builder = IndexBuilder(resolver=resolver)
    builder.save_indexes()
