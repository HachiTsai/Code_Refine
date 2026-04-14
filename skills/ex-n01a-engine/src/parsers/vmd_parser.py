import re
import json
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# ==========================================
# 🏗️ Core Logic: Hitachi VMD Parser (v5.5)
# ==========================================
# 職責：虛擬設備 (VMD) 解析。處理 SEL (選擇器), SW (開關), VM (馬達/閥門)。
# 語義：還原 DCS 的邏輯控制物件、狀態回饋信號與操作指令。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser

class HitachiVMDParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization
        # ==========================================
        super().__init__(description="Hitachi VMD Parser v5.5")
        self.vsrname_map = {}

    def _is_invalid(self, val: str) -> bool:
        if not val: return True
        v = val.strip()
        return v == "" or v == "W" or v in ["0", "1", "2", "3"]

    def parse_vsrname(self, file_path: Path):
        """解析服務名稱對照表"""
        # ==========================================
        # 📂 VSRNAME Parsing Logic
        # ==========================================
        if not file_path.exists(): return
        content = self.read_text(file_path)
        lines = content.splitlines()[1:] 
            
        for line in lines:
            parts = line.split('\t')
            if len(parts) < 3: continue
            no, rname1, rname2 = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if rname1 or rname2:
                self.vsrname_map[no] = f"{rname1}/{rname2}".strip('/')

    def parse_sel(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析虛擬選擇器 (SEL)"""
        # ==========================================
        # 📂 SEL Parsing Logic
        # ==========================================
        results = []
        if not file_path.exists(): return results
        content = self.read_text(file_path)
        lines = content.splitlines()
        if not lines: return results
        
        headers = lines[0].split('\t')
        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) < 3 or not parts[1].strip(): continue
            
            row = dict(zip(headers, parts))
            item = {
                "No": parts[0].strip(),
                "TAGNO": parts[1].strip(), 
                "SERVICE": parts[2].strip(),
                "SIGNAL": self.standardize(parts[3].strip()) if len(parts) > 3 else "",
                "Options": []
            }
            for i in range(1, 17):
                name_val = row.get(f"NAME{i}", "").strip()
                if name_val and name_val != "0":
                    item["Options"].append({"index": i, "name": name_val})
            results.append(item)
        return results

    def parse_sw(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析虛擬開關 (SW)"""
        # ==========================================
        # 📂 SW Parsing Logic
        # ==========================================
        results = []
        if not file_path.exists(): return results
        content = self.read_text(file_path)
        for line in content.splitlines()[1:]:
            parts = line.split('\t')
            if len(parts) < 8 or not parts[1].strip(): continue
            tagno, service, sw_type, signal, on_off_no = parts[1].strip(), parts[2].strip(), parts[4].strip(), parts[5].strip(), parts[7].strip()
            if self._is_invalid(signal) and self._is_invalid(sw_type): continue
            
            no_val = parts[0].strip()
            no_formatted = self.standardize(f"SW{no_val.zfill(4)}") if no_val.isdigit() else self.standardize(no_val)
            
            results.append({
                "No": no_formatted, 
                "TAGNO": self.standardize(tagno), 
                "SERVICE": service,
                "TYPE": sw_type, 
                "SIGNAL": self.standardize(signal),
                "ON_OFF_DESC": self.vsrname_map.get(on_off_no, on_off_no)
            })
        return results

    def parse_vm(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析虛擬電機/閥門 (VM)"""
        # ==========================================
        # 📂 VM Parsing Logic
        # ==========================================
        results = []
        if not file_path.exists(): return results
        content = self.read_text(file_path)
        for line in content.splitlines()[1:]:
            parts = line.split('\t')
            if len(parts) < 10 or not parts[1].strip(): continue
            tagno, service, vm_type = parts[1].strip(), parts[2].strip(), parts[4].strip()
            if all(self._is_invalid(parts[i]) for i in range(5, 9)): continue
            
            no_val, no_padded = parts[0].strip(), parts[0].strip().zfill(4)
            results.append({
                "No": no_val, 
                "TAGNO": self.standardize(tagno), 
                "SERVICE": service, 
                "TYPE": vm_type,
                "OUT1": self.standardize(parts[5].strip()), 
                "OUT2": self.standardize(parts[6].strip()),
                "ANS1": self.standardize(parts[7].strip()), 
                "ANS2": self.standardize(parts[8].strip()),
                "TRIP_SEC": parts[9].strip() if len(parts) > 9 else "",
                "status_signals": {
                    "VS": self.standardize(f"VS{no_padded}"), 
                    "VD": self.standardize(f"VD{no_padded}"),
                    "VI": self.standardize(f"VI{no_padded}"), 
                    "VR": self.standardize(f"VR{no_padded}"), 
                    "VE": self.standardize(f"VE{no_padded}")
                }
            })
        return results

    def run_batch(self):
        # ==========================================
        # 🚜 Batch Extraction Engine
        # ==========================================
        print(f"🚀 Starting VMD extraction for {self.resolver.context_path}...")
        raw_dir, gid_dir = self.resolver.get_raw("VMD"), self.resolver.get_gid("VMD")
        build_dir = self.resolver.build_base
        
        self.parse_vsrname(raw_dir / "vmd_vsrname.txt")
        sel_data = self.parse_sel(raw_dir / "vmd_sel.txt")
        self.save_json(sel_data, gid_dir / "vmd_sel_refined.json")
        sw_data = self.parse_sw(raw_dir / "vmd_sw.txt")
        self.save_json(sw_data, gid_dir / "vmd_sw_refined.json")
        vm_data = self.parse_vm(raw_dir / "vmd_vm.txt")
        self.save_json(vm_data, gid_dir / "vmd_vm_refined.json")
        
        vmd_registry = {
            "SEL": {item["TAGNO"]: item for item in sel_data},
            "SW": {self.standardize(item["TAGNO"]): item for item in sw_data},
            "VM": {self.standardize(item["TAGNO"]): item for item in vm_data}
        }
        self.save_json(vmd_registry, build_dir / "GEN_vmd_registry.json")
        
        # --- 🤝 Final Handshake ---
        total_count = len(sel_data) + len(sw_data) + len(vm_data)
        print(f"✅ VMD Extraction complete: {len(sel_data)} SEL, {len(sw_data)} SW, {len(vm_data)} VM entries.")
        self.handshake(total_count, status="Success")

if __name__ == "__main__":
    parser = HitachiVMDParser()
    if parser.args.action in ["batch", "run"]: parser.run_batch()
