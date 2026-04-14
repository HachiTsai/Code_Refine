import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# ==========================================
# 🏗️ Core Logic: Hitachi SEQ Timer Parser (v5.5)
# ==========================================
# 職責：序列計時器 (SEQ Timer) 解析。處理 seq_tm.txt 原始碼。
# 語義：還原 DCS 的計時器編號、標籤與對應的設定值。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
    from ..utils import PathResolver
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser
    from utils import PathResolver

class HitachiSEQTimerParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization
        # ==========================================
        super().__init__(description="Hitachi SEQ Timer Parser v5.5")

    def parse_timer_master(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析 seq_tm.txt"""
        # ==========================================
        # 📂 Timer Master Extraction Logic
        # ==========================================
        timers = []
        if not file_path.exists(): return timers
            
        content = self.read_text(file_path)
        lines = content.splitlines()
        
        for line in lines[1:]: # 跳過標題
            line = line.strip()
            if not line: continue
            
            parts = line.split('\t')
            if len(parts) >= 3:
                timers.append({
                    "no": parts[0].strip(),
                    "tag": self.standardize(parts[1].strip()),
                    "value": parts[2].strip()
                })
        return timers

    def run_batch(self):
        # ==========================================
        # 🚜 Batch Extraction Engine
        # ==========================================
        print(f"🚀 Starting SEQ Timer Parsing for {self.resolver.context_path}...")
        raw_file = self.resolver.get_raw("SEQ") / "seq_tm.txt"
        gid_dir = self.resolver.get_gid("SEQ")
        
        gid_dir.mkdir(parents=True, exist_ok=True)
        
        timers = self.parse_timer_master(raw_file)
        if timers:
            out_path = gid_dir / "seq_tm_refined.json"
            self.save_json(timers, out_path)
            
            # --- 🤝 Final Handshake ---
            print(f"✅ Saved: {out_path.name}")
            self.handshake(len(timers), status="Success")

if __name__ == "__main__":
    parser = HitachiSEQTimerParser()
    if parser.args.action in ["batch", "run"]: parser.run_batch()
