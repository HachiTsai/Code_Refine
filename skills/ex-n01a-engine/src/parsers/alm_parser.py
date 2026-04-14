import os
import json
import re
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# ==========================================
# 🏗️ Core Logic: Hitachi ALM Parser (v5.6)
# ==========================================
# 職責：警報 (Alarm) 解析。整合預處理邏輯，實現「記憶體內」數據結構化。
# 語義：還原 DCS 的警報文本與操作指引，同時保持物理原始碼 (RAW) 的純淨。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser

class HitachiALMParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization
        # ==========================================
        super().__init__(description="Hitachi ALM Parser v5.6")

    def _get_processed_lines(self, file_path: Path, header_name: str) -> List[str]:
        """
        [Preprocessor Logic Integration] 
        記憶體內預處理：為無標題數據注入虛擬標題行與線性編號。
        """
        if not file_path.exists():
            return []
            
        content = self.read_text(file_path)
        raw_lines = content.splitlines()
        if not raw_lines: return []

        # 1. 檢查是否具備標題 (相容舊有已處理過的數據)
        if raw_lines[0].startswith(header_name):
            return raw_lines

        # 2. 執行記憶體內注入 (不修改實體檔案)
        processed_lines = [f"{header_name}\tCONTENT_PLACEHOLDER"] # 虛擬標題
        for i, line in enumerate(raw_lines):
            processed_lines.append(f"{i}\t{line}")
            
        return processed_lines

    def parse_og(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """解析 Operator Guide (OG)"""
        # ==========================================
        # 📂 OG Parsing Logic
        # ==========================================
        lines = self._get_processed_lines(file_path, "OG NO.")
        if not lines: return {}
        
        results = {}
        # 跳過虛擬標題行
        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) < 8: continue
            
            # 第一欄現在是注入的編號，第二欄才是原始的 Tag
            og_no, tag_raw = parts[0].strip(), parts[1].strip()
            
            guide_ch1 = parts[7].strip() if len(parts) > 7 else ""
            guide_ch2 = parts[8].strip() if len(parts) > 8 else ""
            guide_ch3 = parts[9].strip() if len(parts) > 9 else ""
            
            service = guide_ch1
            if not service and guide_ch2 and guide_ch2 not in ["0", "1", "W", "R", "G"]: service = guide_ch2
            if not service and guide_ch3 and guide_ch3 not in ["0", "1", "W", "R", "G"]: service = guide_ch3
            
            if not service or service in ["R", "W", "1", "0", "G"]: continue
            
            ogno_formatted = self.standardize(f"OG{og_no.zfill(4)}") if og_no.isdigit() else self.standardize(og_no)
            tag = self.standardize(tag_raw) if tag_raw and tag_raw not in ["R", "W", "1", "0", "G"] else ogno_formatted

            eq_match = re.search(r'\((.*?)\)', service)
            equipment = eq_match.group(1).replace('-', '') if eq_match else "Common"
            
            if equipment == "Common":
                st_match = re.match(r'^(ST\d+)', service)
                if st_match: equipment = st_match.group(1)

            results[tag] = {"ogno": ogno_formatted, "tag": tag, "service": service, "equipment": equipment}
        return results

    def parse_ua(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """解析 User Alarm (UA)"""
        # ==========================================
        # 📂 UA Parsing Logic
        # ==========================================
        lines = self._get_processed_lines(file_path, "UA NO.")
        if not lines: return {}
        
        results = {}
        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) < 6: continue
            
            # 物理 ID 與描述位址偏移處理
            ua_no, tag_raw, service, signal_raw = parts[0].strip(), parts[1].strip(), parts[3].strip(), parts[5].strip()
            
            if not tag_raw or tag_raw in ["R", "W", "1", "0", "G"]: continue
            
            uano_formatted = self.standardize(f"UA{ua_no.zfill(4)}") if ua_no.isdigit() else self.standardize(ua_no)
            tag = self.standardize(tag_raw)
            signal = self.standardize(signal_raw)

            equipment = service.split('-')[0] + service.split('-')[1] if "-" in service else service.replace('-', '')
            results[tag] = {"uano": uano_formatted, "tag": tag, "service": service, "signal": signal, "equipment": equipment.replace(' ', '')}
        return results

    def run_batch(self):
        # ==========================================
        # 🚜 Batch ALM Extraction Engine
        # ==========================================
        print(f"🚀 Starting Batch ALM extraction for {self.resolver.context_path}...")
        raw_dir, gid_dir = self.resolver.raw_base / "ALM", self.resolver.gid_base / "ALM"
        build_dir = self.resolver.build_base
        
        # --- 🏗️ Integrated Pre-Processing & Parsing ---
        # 直接執行解析，內部會自動處理無標題原始檔
        og_data = self.parse_og(raw_dir / "alm_oprgt.txt")
        self.save_json(og_data, gid_dir / "alm_og_refined.json")
        
        ua_data = self.parse_ua(raw_dir / "alm_usalm.txt")
        self.save_json(ua_data, gid_dir / "alm_ua_refined.json")
        
        full_registry = {"OG": og_data, "UA": ua_data}
        self.save_json(full_registry, build_dir / "GEN_alm_registry.json")
        
        # --- 🤝 Final Handshake ---
        total_count = len(og_data) + len(ua_data)
        self.handshake(total_count, status="Success")

if __name__ == "__main__":
    parser = HitachiALMParser()
    if parser.args.action in ["batch", "run", "batch-registry"]:
        parser.run_batch()
