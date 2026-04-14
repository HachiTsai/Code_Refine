import os
import re
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# ==========================================
# 🏗️ Core Logic: Hitachi DDC Parser (v6.3)
# ==========================================
# 職責：DDC (Direct Digital Control) 迴路解析。提取 FNO 功能塊與參數映射。
# 語義：還原 DCS 的迴路控制邏輯與儀表訊號鏈。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
    from ..utils import PathResolver, TextCleaner
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser
    from utils import PathResolver, TextCleaner

class HitachiDDCParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization
        # ==========================================
        super().__init__(description="Hitachi DDC Parser v6.4 (Preprocessed)")
        self.cleaner = TextCleaner()

    def parse_index(self, ddcinst_path: Path) -> Dict[str, Dict[str, str]]:
        """解析 ddcinst.txt 獲取 Metadata"""
        # ==========================================
        # 📂 Index Parsing Protocol
        # ==========================================
        metadata_map = {}
        if not ddcinst_path.exists(): return metadata_map
        content = self.read_text(ddcinst_path)
        for line in content.splitlines()[1:]:
            parts = line.split('\t')
            if len(parts) >= 2:
                no = parts[0].strip().zfill(3)
                metadata_map[no] = {"TAG": parts[1].strip(), "SERVICE": parts[2].strip() if len(parts)>2 else ""}
        return metadata_map

    def _preprocess_loop(self, lp_path: Path) -> Dict[str, Any]:
        """
        [Preprocessor Logic]
        記憶體內預處理：安全讀取、段落切分與物理條數審計。
        """
        content = self.read_text(lp_path)
        
        # 切分區塊
        if not content or "<Parameter>" not in content:
            sections = [content, ""]
        else:
            sections = re.split(r'<Parameter>', content, flags=re.IGNORECASE)
            
        block_content = sections[0]
        param_content = sections[1] if len(sections) > 1 else ""

        # 物理審計：精確統計 block_content 中的邏輯行數 (BNO)
        block_lines = []
        for line in block_content.splitlines():
            # 只要行首是數字（允許前導空白），且後面跟著 Tab 或空白，即視為物理邏輯行
            if re.match(r'^\s*\d+[\t\s]', line):
                block_lines.append(line)
        
        return {
            "id": lp_path.stem,
            "raw_logic_lines": len(block_lines),
            "block_lines": block_lines,
            "param_content": param_content
        }

    def parse_loop(self, lp_path: Path) -> Dict[str, Any]:
        """解析單一 DDC 迴路"""
        # ==========================================
        # 🧬 Preprocessed Data Extraction
        # ==========================================
        preprocessed = self._preprocess_loop(lp_path)
        
        result = {
            'metadata': {
                'id': preprocessed["id"],
                'logic_audit': {"physical_blocks": preprocessed["raw_logic_lines"]}
            },
            'blocks': [],
            'parameters': []
        }
        
        if preprocessed["raw_logic_lines"] == 0:
            return result

        # --- 🏗️ Block Extraction ---
        for line in preprocessed["block_lines"]:
            line = self.cleaner.clean(line).strip()
            if not line: continue
            
            parts = line.split('\t')
            if len(parts) < 3: parts = re.split(r'\s{2,}', line)
            
            if len(parts) >= 3:
                try:
                    bno, fno, fnm = int(parts[0]), (int(parts[1]) if parts[1].isdigit() else 0), parts[2]
                    terminals = {}
                    for i in range(1, 5):
                        lno_idx, addr_idx = 1 + (i * 2), 2 + (i * 2)
                        lno = parts[lno_idx].strip() if len(parts) > lno_idx else ""
                        addr = parts[addr_idx].strip() if len(parts) > addr_idx else ""
                        if lno or addr:
                            term_data = {"lno": self.standardize(lno) if lno else "", "addr": addr, "is_external": bool(lno)}
                            enable_idx = 13 + i
                            if len(parts) > enable_idx:
                                enable_val = parts[enable_idx].strip()
                                if enable_val and enable_val.upper() != "NOUSE": term_data["enable"] = self.standardize(enable_val)
                            terminals[f"TERM{i}"] = term_data
                    result['blocks'].append({'bno': bno, 'fno': fno, 'fnm': fnm, 'terminals': terminals, 'raw_params': parts[13] if len(parts) > 13 else ""})
                except: continue

        # --- ⚙️ Parameter Mapping ---
        # [Optimization] Skipping raw parameter list capture to keep Core JSON clean.
        result['parameters'] = []
                
        return result

    def run_batch(self):
        # ==========================================
        # 🚜 Batch Extraction Engine
        # ==========================================
        raw_dir, gid_dir = self.resolver.raw_base / "DDC", self.resolver.gid_base / "DDC"
        if not raw_dir.exists(): return
        print(f"🚀 Starting Smart DDC extraction for {self.resolver.unit}...")
        index_meta = self.parse_index(raw_dir / "ddcinst.txt")
        processed_count = 0
        gid_dir.mkdir(parents=True, exist_ok=True)
        for lp_file in sorted(raw_dir.glob("LP*.txt")):
            loop_id = self.standardize(lp_file.stem.upper())
            result = self.parse_loop(lp_file)
            
            # [v6.5] 精確提取純數字編號，剔除 Sxx 站號，確保能匹配 ddcinst.txt
            num_match = re.search(r'\d+', lp_file.stem)
            if num_match:
                loop_no = num_match.group().zfill(3)
                if loop_no in index_meta:
                    result['metadata'].update(index_meta[loop_no])
                    
            if result.get('blocks'):
                self.save_json(result, gid_dir / f"{loop_id}_refined.json")
                processed_count += 1
        print(f"✅ Batch DDC complete: {processed_count} loops processed.")
        self.handshake(processed_count, status="Success")

if __name__ == "__main__":
    parser = HitachiDDCParser()
    if parser.args.action in ["batch", "run"]: parser.run_batch()
