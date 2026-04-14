import re
import json
import argparse
import subprocess
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

# ==========================================
# 🏗️ Core Logic: Hitachi SEQ Parser (v5.5)
# ==========================================
# 職責：序列 (Sequence) 邏輯解析。處理 Pattern, Shift, Correction 與 Always 邏輯塊。
# 語義：還原 DCS 的狀態機演進與聯鎖觸發機制。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
    from ..utils import PathResolver, SignalScanner, IDStandardizer
except ImportError:
    # 修復路徑問題，確保可從 script 直接執行
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser
    from utils import PathResolver, SignalScanner, IDStandardizer

class HitachiSEQParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization & Spec Binding
        # ==========================================
        super().__init__(description="Hitachi SEQ Parser v5.5")
        self.load_specs("seq_schema.json")
        self.scanner = SignalScanner()

    def standardize_expression(self, expr: str) -> str:
        """將表達式中的所有位號標準化 (注入站點後綴)"""
        # ==========================================
        # 📡 Signal Normalization within Logic Expr
        # ==========================================
        if not expr: return ""
        found_signals = self.scanner.scan(expr)
        std_expr = expr
        for sid in sorted(found_signals, key=len, reverse=True):
            raw_id = sid
            for station_id in IDStandardizer.STATION_MAP.values():
                if sid.endswith(station_id):
                    raw_id = sid[:-len(station_id)]
                    break
            std_expr = std_expr.replace(raw_id, sid)
        return std_expr

    def parse_boolean_logic(self, logic_str: str) -> str:
        return logic_str if logic_str else ""

    def _parse_correction_block(self, content: str) -> Dict[str, Dict[str, Any]]:
        # ==========================================
        # 🛠️ Correction Block Decoding
        # ==========================================
        corr_map: Dict[str, Dict[str, Any]] = {}
        corr_match = re.search(r'<Correction>(.*?)<', content, re.DOTALL)
        if not corr_match: return corr_map
        lines = corr_match.group(1).strip().split('\n')
        if len(lines) < 2: return corr_map
        for line in lines[1:]:
            values = line.split('\t')
            if len(values) < 3: continue
            step_no = values[0]
            logic_no = values[1].strip()
            logic_str = values[2].strip()
            if not logic_str: continue
            
            step_logic: Dict[str, str] = {}
            assignments = logic_str.split(',')
            for assign in assignments:
                if '=' in assign:
                    parts = assign.split('=')
                    input_val = parts[0].strip()
                    for output_val in parts[1:]:
                        step_logic[output_val.strip()] = input_val
            
            corr_map[step_no] = {
                "logic_no": logic_no,
                "targets": step_logic,
                "raw_full": logic_str
            }
        return corr_map

    def _compress_steps(self, full_row: Dict[str, str], out_addr: str, corr_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
        # ==========================================
        # 📦 Step Compression Logic
        # ==========================================
        compressed = []
        start_step = None
        current_state_id = None
        for i in range(1, 129):
            step_key = str(i)
            raw_val = full_row.get(step_key, '0').strip()
            if raw_val == '': raw_val = '0'
            if raw_val == '2':
                logic_content = corr_map.get(step_key, {}).get("targets", {}).get(out_addr, "UNDEFINED_CORRECTION")
                std_logic = self.standardize_expression(logic_content)
                state_desc = f"2 (IF {std_logic})"
            else:
                state_desc = raw_val
            if state_desc != current_state_id:
                if current_state_id is not None and current_state_id != '0':
                    end_step = i - 1
                    range_str = f"{start_step}-{end_step}" if start_step != end_step else f"{start_step}"
                    if start_step:
                        compressed.append({"range": range_str, "value": current_state_id})
                start_step = i
                current_state_id = state_desc
        if current_state_id is not None and current_state_id != '0':
            end_step = 128
            range_str = f"{start_step}-{end_step}" if start_step != end_step else f"{start_step}"
            if start_step:
                compressed.append({"range": range_str, "value": current_state_id})
        return compressed

    def _compile_always_block(self, lines: List[str]) -> List[Dict[str, Any]]:
        # ==========================================
        # ⚖️ Always Logic Compilation (v6.0 Spec)
        # ==========================================
        blocks = []
        current_rows = []
        
        for line in lines:
            if not line.strip(): continue
            parts = line.split('\t')
            if parts[0].strip() == "INPUT": continue
            
            input_name = parts[0].strip()
            if input_name.startswith('/'):
                std_input = '/' + self.standardize(input_name[1:])
            else:
                std_input = self.standardize(input_name)

            codes = [parts[i].strip() if i < len(parts) else "0" for i in range(1, 9)]
            output_tag = self.standardize(parts[9].strip()) if len(parts) > 9 and parts[9].strip() and parts[9].strip() != "OUTPUT" else ""

            row_data = {"input": std_input, "codes": codes, "output": output_tag}

            if output_tag and codes[7] not in ('F', 'G'):
                if current_rows:
                    blocks.append(current_rows)
                current_rows = [row_data]
            else:
                if current_rows:
                    current_rows.append(row_data)
        
        if current_rows:
            blocks.append(current_rows)

        final_results = []
        for rows in blocks:
            start_output = rows[0]["output"]
            compiled_expr = self._process_logic_block(rows, start_output)
            if compiled_expr:
                final_results.append({
                    "output": start_output,
                    "expression": compiled_expr,
                    "raw_block": rows
                })
                for r in rows[1:]:
                    if r["output"] and r["codes"][7] in ('F', 'G'):
                        final_results.append({
                            "output": r["output"],
                            "expression": compiled_expr,
                            "raw_block": rows
                        })
        return final_results

    def _process_logic_block(self, rows: List[Dict[str, Any]], output_signal: str) -> str:
        # ==========================================
        # ⚙️ Logic Compilation Matrix Scanner (v6.8: Extended Gates)
        # ==========================================
        num_rows = len(rows)
        num_cols = 8
        
        # 初始化：每一行的初始值為輸入位號
        results = ["" for _ in range(num_rows)]
        for r in range(num_rows):
            name = rows[r]["input"]
            if name.startswith("/"):
                results[r] = f"/({name[1:]})"
            else:
                results[r] = name

        # 逐列處理 (Column 1 to 8)
        for c in range(num_cols):
            r = 0
            while r < num_rows:
                code = rows[r]["codes"][c]
                
                # 規則：NOT (3) - 處理單行否定
                if code == "3":
                    if results[r]:
                        results[r] = f"/({results[r]})"
                
                # 規則：One-Shot (5) 或 Timer (4)
                if code.startswith(("4", "5")):
                    label = "P" if code.startswith("5") else "T"
                    param = ""
                    if "[" in code and "]" in code:
                        param = code[code.find("["):code.find("]")+1]
                    if results[r]:
                        results[r] = f"{label}{param}({results[r]})"
                    
                    # 邏輯閘轉化：[1] 視為 AND (1), 其他視為 OR (2)
                    code = "1" if "[1]" in code else "2"

                # 規則：OR (2/A/B) 或 AND (1) 區塊聚合
                if code in ("1", "2"):
                    op = "&" if code == "1" else "+"
                    group_indices = [r]
                    sr = r + 1
                    # 尋找群組邊界
                    while sr < num_rows:
                        s_code = rows[sr]["codes"][c]
                        if s_code == "C": # Terminator
                            sr += 1
                            continue
                        group_indices.append(sr)
                        if s_code == "B": # End of group
                            break
                        sr += 1
                    
                    # 執行群組聚合
                    elements = [results[gi] for gi in group_indices if results[gi]]
                    if len(elements) > 1:
                        results[r] = f"({ (' ' + op + ' ').join(elements) })"
                    elif len(elements) == 1:
                        results[r] = elements[0]
                    
                    # 消費群組內的其他行
                    for gi in group_indices[1:]:
                        results[gi] = ""
                    
                    r = sr if sr > r else r + 1
                else:
                    r += 1
        
        # 最終聚合：若還有剩餘的平行分支，以 OR (+) 連結
        remaining = [res for res in results if res]
        if len(remaining) > 1:
            final_expr = f"({' + '.join(remaining)})"
        elif len(remaining) == 1:
            final_expr = remaining[0]
        else:
            final_expr = ""
        
        # 全域否定規則
        if rows[0]["codes"][0] == "3" and final_expr and not final_expr.startswith("/"):
            final_expr = f"/({final_expr})"
            
        return final_expr

    def extract_unit_logic(self, file_path: Path, target_no: str = "1") -> Dict[str, Any]:
        # ==========================================
        # 📂 Unit Logic Full Extraction Pipeline
        # ==========================================
        content = self.read_text(file_path)
        result: Dict[str, Any] = {
            "metadata": {},
            "pattern": [],
            "shift": [],
            "correction": [], 
            "always": [],
            "process_timer": [],
            "control_switches": set()
        }
        corr_map = self._parse_correction_block(content)
        
        # 1. Metadata Standardize
        base_match = re.search(r'<Base>(.*?)<', content, re.DOTALL)
        if base_match:
            lines = base_match.group(1).strip().split('\n')
            if len(lines) > 1:
                headers = [h.strip() for h in lines[0].split('\t')]
                first_data_line = lines[1]
                values = first_data_line.split('\t')
                if values:
                    metadata = {headers[i]: values[i].strip() for i in range(len(headers)) if i < len(values) and values[i].strip() != ''}
                    if "No" in metadata and metadata["No"].isdigit():
                        metadata["No"] = f"US{metadata['No'].zfill(4)}"
                    result["metadata"] = metadata

        # 2. Pattern Standardize
        pattern_match = re.search(r'<Pattern>(.*?)<', content, re.DOTALL)
        if pattern_match:
            lines = pattern_match.group(1).strip().split('\n')
            headers = [h.strip() for h in lines[0].split('\t')]
            for line in lines[1:]:
                values = line.split('\t')
                if len(values) > 2:
                    row_full = dict(zip(headers, values))
                    out_addr = row_full.get("OUTADDR", "").strip()
                    if out_addr:
                        std_out = self.standardize(out_addr)
                        result["control_switches"].add(std_out)
                        active_ranges = self._compress_steps(row_full, out_addr, corr_map)
                        if active_ranges:
                            result["pattern"].append({
                                "OUTADDR": std_out, 
                                "ANAGJKN": row_full.get("ANAGJKN", ""), 
                                "active_states": active_ranges
                            })
        
        # 3. Shift Standardize
        shift_match = re.search(r'<Shift>(.*?)<', content, re.DOTALL)
        if shift_match:
            lines = shift_match.group(1).strip().split('\n')
            if len(lines) > 1:
                headers = [h.strip() for h in lines[0].split('\t')]
                for line in lines[1:]:
                    values = line.split('\t')
                    if len(values) > 4 and values[4].strip():
                        row = dict(zip(headers, values))
                        logic_item: Dict[str, Any] = {k: v for k, v in row.items() if v.strip() != ''}
                        logic_item["is_global"] = (values[0] == "**")
                        if "LOGIC" in row:
                            logic_item["LOGIC"] = self.standardize_expression(row["LOGIC"])
                        logic_item["LOGIC_COMPILED"] = self.parse_boolean_logic(logic_item.get("LOGIC", ""))
                        result["shift"].append(logic_item)

        # 4. Correction Standardize
        if corr_map:
            result["correction"] = [
                {"step": step, "logic": logic} 
                for step, logic in corr_map.items()
            ]

        # 5. Timer/Always
        proc_match = re.search(r'<Process/Timer>(.*?)<', content, re.DOTALL)
        if proc_match:
            lines = proc_match.group(1).strip().split('\n')
            if len(lines) > 1:
                headers = [h.strip() for h in lines[0].split('\t')]
                for line in lines[1:]:
                    values = line.split('\t')
                    if len(values) > 1 and values[1].strip():
                        result["process_timer"].append({headers[i].strip(): values[i].strip() for i in range(len(headers)) if i < len(values) and values[i].strip() != ''})

        always_match = re.search(r'<Always>(.*?)<', content, re.DOTALL)
        if always_match:
            always_lines = always_match.group(1).strip().split('\n')
            if len(always_lines) > 1:
                result["always"] = self._compile_always_block(always_lines[1:])

        result["control_switches"] = sorted(list(result["control_switches"]))
        # 6. Logic Audit Summary
        result["metadata"]["logic_audit"] = {
            "shift_count": len(result.get("shift", [])),
            "correction_count": len(result.get("correction", [])),
            "always_count": len(result.get("always", [])),
            "pattern_count": len(result.get("pattern", []))
        }
        return result

    def run_batch(self):
        # ==========================================
        # 🚜 Batch Extraction Engine
        # ==========================================
        print(f"🚀 Starting Batch SEQ extraction for {self.resolver.context_path}...")
        raw_dir = self.resolver.get_raw("SEQ")
        gid_dir = self.resolver.get_gid("SEQ")
        build_dir = self.resolver.build_base
        
        seq_registry = {}
        skipped_records = []
        processed_count = 0
        
        gid_dir.mkdir(parents=True, exist_ok=True)
        build_dir.mkdir(parents=True, exist_ok=True)

        for seq_file in sorted(raw_dir.rglob("MPN*.txt")):
            functional_id = seq_file.stem.upper().replace('MPN', 'US')
            seq_id = self.standardize(functional_id, unit=self.resolver.unit)
            
            try:
                result = self.extract_unit_logic(seq_file)
            except Exception as e:
                skipped_records.append({
                    "file": seq_file.name,
                    "type": "SEQ",
                    "status": "SKIPPED",
                    "reason": "PARSE_ERROR",
                    "detail": f"解析異常: {str(e)}"
                })
                continue
                
            has_always = bool(result.get('always'))
            has_pattern = bool(result.get('pattern'))
            has_shift = bool(result.get('shift'))
            has_correction = bool(result.get('correction'))
            
            if not any([has_always, has_pattern, has_shift, has_correction]):
                skipped_records.append({
                    "file": seq_file.name,
                    "type": "SEQ",
                    "status": "SKIPPED",
                    "reason": "NO_ACTIVE_MATRIX",
                    "detail": "所有的序列矩陣皆未啟用"
                })
                continue

            out_path = gid_dir / f"{seq_id}_refined.json"
            self.save_json(result, out_path)
            
            root = self.resolver.project_root
            rel_path = str(out_path.relative_to(root))
            seq_registry[seq_id] = {
                "path": rel_path,
                "unit_name": result.get('metadata', {}).get('NAME', ''),
                "always_count": len(result.get('always', [])),
                "pattern_count": len(result.get('pattern', []))
            }
            processed_count += 1
        
        self.save_json(seq_registry, build_dir / "GEN_seq_registry.json")
        
        # --- Update Skipped Files Track ---
        skip_file_path = build_dir / "GEN_skipped_files.json"
        existing_skips = {"unit": self.resolver.unit, "skipped_files": []}
        if skip_file_path.exists():
            try:
                with open(skip_file_path, "r", encoding="utf-8") as f:
                    existing_skips = json.load(f)
            except Exception:
                pass
                
        updated_skips = [s for s in existing_skips.get("skipped_files", []) if s.get("type", "") != "SEQ"]
        updated_skips.extend(skipped_records)
        existing_skips["skipped_files"] = updated_skips
        
        with open(skip_file_path, "w", encoding="utf-8") as f:
            json.dump(existing_skips, f, indent=2, ensure_ascii=False)

        print(f"✅ Batch SEQ complete: {processed_count} files processed. ({len(skipped_records)} skipped/warnings tracked)")
        self.handshake(processed_count, status="Success")

if __name__ == "__main__":
    parser = HitachiSEQParser()
    if parser.args.action in ["batch", "run"]:
        parser.run_batch()
