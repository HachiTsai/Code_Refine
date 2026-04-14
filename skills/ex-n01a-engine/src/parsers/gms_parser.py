import os
import json
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# ==========================================
# 🏗️ Core Logic: Hitachi GMS Parser (v5.4)
# ==========================================
# 職責：GMS (Group Management System) 解析。處理 destin 與 dtattr 配對檔案。
# 語義：還原 DCS 的品種配方 (Recipe)、設定值映射與參數索引地圖。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
    from ..utils import PathResolver
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser
    from utils import PathResolver

class HitachiGMSParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization & Constraints
        # ==========================================
        super().__init__(description="Hitachi GMS Parser v5.4")
        self.valid_data_limit = 300

    def parse_set(self, destin_path: Path, dtattr_path: Path, set_id: int) -> List[Dict[str, Any]]:
        """解析單一 Set (destin + dtattr)"""
        # ==========================================
        # 📂 Recipe Set Extraction Logic
        # ==========================================
        if not destin_path.exists() or not dtattr_path.exists(): return []
        
        lines_d = self.read_text(destin_path).splitlines()
        lines_a = self.read_text(dtattr_path).splitlines()
        
        results = []
        max_len = max(len(lines_d), len(lines_a))
        
        has_star_g = any(line.startswith('*G') for line in lines_d)
        block_start = [i for i, line in enumerate(lines_d) if line.startswith('*G')][0] if has_star_g else 0
        data_start_offset = 2 if has_star_g else 1
        
        for offset_idx in range(self.valid_data_limit):
            idx = block_start + data_start_offset + offset_idx
            if idx >= max_len or (idx < len(lines_d) and lines_d[idx].startswith('*G')): break
            
            name = self._get_col_value(lines_a, idx, 0)
            address = self._get_col_value(lines_d, idx, 1)
            
            if not name and (not address or address == "0"): continue
            if name in ["W", "0"]: continue
            
            results.append({
                "category_id": set_id,
                "recipe_name": name,
                "gradeno": str(offset_idx + 1),
                "address": address
            })
        return results

    def _get_col_value(self, lines: List[str], idx: int, col_idx: int) -> str:
        if idx < len(lines):
            parts = lines[idx].strip().split('\t')
            return parts[col_idx].strip() if len(parts) > col_idx else ""
        return ""

    def run_batch(self):
        # ==========================================
        # 🚜 Batch GMS Processing Protocol
        # ==========================================
        print(f"🚀 Starting Batch GMS extraction for {self.resolver.context_path}...")
        raw_dir, gid_dir = self.resolver.get_raw("GMS"), self.resolver.get_gid("GMS")
        build_dir = self.resolver.build_base
        
        all_mappings = []
        for i in range(1, 17):
            d, a = raw_dir / f"destin{i}.txt", raw_dir / f"dtattr{i}.txt"
            if d.exists():
                mappings = self.parse_set(d, a, i)
                all_mappings.extend(mappings)
        
        if all_mappings:
            self.save_json(all_mappings, gid_dir / "gms_mapping_refined.json")
            registry = {f"GMS_S{item['category_id']:02d}_N{int(item['gradeno']):03d}": item for item in all_mappings}
            self.save_json(registry, build_dir / "GEN_GMS_MAPPING_BASELINE.json")
            
            # --- 🤝 Final Handshake ---
            print(f"✅ GMS extraction complete: {len(all_mappings)} entries.")
            self.handshake(len(all_mappings), status="Success")

if __name__ == "__main__":
    parser = HitachiGMSParser()
    if parser.args.action in ["batch", "run", "batch-baseline"]:
        parser.run_batch()
