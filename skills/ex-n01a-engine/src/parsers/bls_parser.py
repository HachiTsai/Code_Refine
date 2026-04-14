import re
import json
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# ==========================================
# 🏗️ Core Logic: Hitachi BLS Parser (v7.2: Logic-Physical Bridge)
# ==========================================
# 職責：BLS 深度解析。透過精確編號剝離技術，打通邏輯位號與物理檔名之間的映射。
# 變更紀錄:
#   v7.2: 修正 num_part 提取邏輯，防止站號數字污染檔名尋找；支援多補零格式匹配。
# ==========================================

__version__ = "v7.2 (Bridge Hardened)"

try:
    from .base import BaseParser
    from ..utils import PathResolver, SignalScanner, IDStandardizer
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser
    from utils import PathResolver, SignalScanner, IDStandardizer

class HitachiBLSParser(BaseParser):
    def __init__(self):
        super().__init__(description="Hitachi BLS Parser v7.2")
        self.scanner = SignalScanner()
        self.load_specs("bls_schema.json")
        self.op_map = self._build_op_map()
        self.tag_registry = self._load_tag_registry()

    def _build_op_map(self) -> Dict[str, str]:
        m = {}
        ops = self.specs.get("operators", {})
        for item in ops.get("arithmetic", []): m[item["symbol"]] = item["desc"]
        for item in ops.get("logic", []): m[item["symbol"]] = item["desc"]
        for item in ops.get("comparison", []): m[item["symbol"]] = item["desc"]
        assign = ops.get("assignment", {})
        if assign: m[assign["symbol"]] = assign["desc"]
        return m

    def _load_tag_registry(self) -> Dict[str, Any]:
        registry_path = self.resolver.build_base / "GEN_tag_registry.json"
        if registry_path.exists():
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def standardize_expression(self, expr: str) -> str:
        if not expr: return ""
        clean_expr = re.sub(r'/*.*/*/', '', expr)
        found_signals = self.scanner.scan(clean_expr)
        std_expr = expr
        for sid in sorted(found_signals, key=len, reverse=True):
            raw_id = sid
            for station_id in IDStandardizer.STATION_MAP.values():
                if sid.endswith(station_id):
                    raw_id = sid[:-len(station_id)]
                    break
            std_id = self.standardize(raw_id)
            std_expr = std_expr.replace(raw_id, std_id)
        return std_expr

    def parse_bls_file(self, file_path: Path, tag_info: Dict[str, Any]) -> Dict[str, Any]:
        content = self.read_text(file_path)
        if not content: return {}

        file_id_raw = file_path.stem.upper()
        physical_id = self.standardize(file_id_raw)
        content_id_raw = self._extract(r"BLSNO\.:\s*(\w+)", content)
        
        identity_conflict = False
        if content_id_raw and content_id_raw != file_id_raw:
            identity_conflict = True

        result = {
            "id": physical_id,
            "logic_alias": content_id_raw,
            "tag_name": tag_info.get("tag", "UNKNOWN"),
            "action": self._extract(r"Action:\s*(.*)", content),
            "comment": self._extract(r"Comment:\s*(.*)", content) or tag_info.get("description", ""),
            "statements": [],
            "metadata": {
                "identity_conflict": identity_conflict,
                "source_file": file_path.name,
                "ref_tag": tag_info.get("tag")
            }
        }

        stmt_match = re.search(r"Statement:\s*(.*)", content, re.DOTALL)
        if stmt_match:
            stmt_text = re.split(r'\n={3,}', stmt_match.group(1))[0]
            result['statements'] = self._parse_recursive_blocks(stmt_text.splitlines())
        
        return result

    def _extract(self, pattern: str, text: str) -> str:
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""

    def _parse_recursive_blocks(self, lines: List[str]) -> List[Dict[str, Any]]:
        statements = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line: i += 1; continue
            if line.upper().startswith("IF "):
                block, consumed = self._handle_if_recursive(lines[i:])
                statements.append(block)
                i += consumed
            elif line.upper().startswith("FOR "):
                block, consumed = self._handle_for_recursive(lines[i:])
                statements.append(block)
                i += consumed
            else:
                statements.append(self._decode_statement(line))
                i += 1
        return statements

    def _handle_if_recursive(self, lines: List[str]) -> Tuple[Dict[str, Any], int]:
        first_line = lines[0].strip()
        condition = first_line[3:].strip().rstrip(';')
        stmt = {
            "type": "IF_CONDITION",
            "condition": self.standardize_expression(condition),
            "then_actions": [], "else_actions": [], "raw": first_line
        }
        consumed, current_collecting = 1, "THEN"
        while consumed < len(lines):
            line = lines[consumed].strip()
            if not line: consumed += 1; continue
            if line.upper().startswith(("IF ", "FOR ", "NEXT ", "RTN ", "END")): break
            if line.upper().startswith("THEN "):
                line = line[5:].strip(); current_collecting = "THEN"
            elif line.upper().startswith("ELSE "):
                line = line[5:].strip(); current_collecting = "ELSE"
            if line:
                action = self._decode_statement(line)
                if current_collecting == "THEN": stmt["then_actions"].append(action)
                else: stmt["else_actions"].append(action)
            stmt["raw"] += "\n" + lines[consumed]
            consumed += 1
        stmt["translation"] = f"如果 {stmt['condition']}，則執行 {len(stmt['then_actions'])} 項動作"
        return stmt, consumed

    def _handle_for_recursive(self, lines: List[str]) -> Tuple[Dict[str, Any], int]:
        first_line = lines[0].strip()
        stmt = {"type": "LOOP_FOR", "range": first_line[4:].strip(), "actions": [], "raw": first_line}
        consumed, inner_lines = 1, []
        while consumed < len(lines):
            line = lines[consumed].strip()
            stmt["raw"] += "\n" + lines[consumed]
            consumed += 1
            if line.upper().startswith("NEXT "): break
            inner_lines.append(line)
        stmt["actions"] = self._parse_recursive_blocks(inner_lines)
        stmt["translation"] = f"針對範圍 [{stmt['range']}] 執行重複運算 ({len(stmt['actions'])} 步)"
        return stmt, consumed

    def _decode_statement(self, raw_line: str) -> Dict[str, Any]:
        std_line = self.standardize_expression(raw_line)
        stmt = {"raw": std_line, "type": "SIMPLE_ASSIGNMENT", "intent": "DATA_TRANSFER", "translation": ""}
        pid_pattern = r"([\w-]+)\.([\w-]+)\s*=\s*([\w-]+)\.K(\d+)"
        pid_match = re.search(pid_pattern, std_line, re.IGNORECASE)
        if pid_match:
            loop, param, gms, k_idx = pid_match.groups()
            stmt["type"] = "PARAMETER_INJECTION"
            stmt["translation"] = f"從配方 [{gms}] 提取 K{k_idx}，注入至 [{loop}] 的 {param}"; return stmt
        translation = re.sub(r'/*.*/*/', '', std_line).strip()
        sorted_ops = sorted(self.op_map.keys(), key=len, reverse=True)
        for op in sorted_ops:
            if op in translation: translation = translation.replace(op, f" {self.op_map[op]} ")
        stmt["translation"] = translation.strip()
        return stmt

    def run_batch(self):
        print(f"🚀 Starting Active-Scan BLS extraction for {self.resolver.context_path}...")
        raw_dir, gid_dir = self.resolver.get_raw("BLS"), self.resolver.get_gid("BLS")
        build_dir = self.resolver.build_base
        
        bls_registry = {}
        skipped_records = []
        processed_count = 0
        gid_dir.mkdir(parents=True, exist_ok=True)
        build_dir.mkdir(parents=True, exist_ok=True)

        for raw_file in sorted(raw_dir.rglob("*.txt")):
            raw_id_str = raw_file.stem.upper()
            std_id = self.standardize(raw_id_str, unit=self.resolver.unit)
            
            matched_tag_info = {}
            for internal_id, info in self.tag_registry.items():
                if info.get("prefix") == "BL" and self.standardize(internal_id, unit=self.resolver.unit) == std_id:
                    matched_tag_info = info
                    break
            
            if not matched_tag_info:
                skipped_records.append({
                    "file": raw_file.name,
                    "type": "BLS",
                    "status": "PROCESSED_WITH_WARNING",
                    "reason": "NOT_IN_REGISTRY",
                    "detail": "檔案存在物理目錄，但在 GEN_tag_registry 中未註冊"
                })
            
            try:
                result = self.parse_bls_file(raw_file, matched_tag_info)
            except Exception as e:
                skipped_records.append({
                    "file": raw_file.name,
                    "type": "BLS",
                    "status": "SKIPPED",
                    "reason": "PARSE_ERROR",
                    "detail": f"解析異常: {str(e)}"
                })
                continue

            if not result or not result.get('statements'):
                skipped_records.append({
                    "file": raw_file.name,
                    "type": "BLS",
                    "status": "SKIPPED",
                    "reason": "EMPTY_STATEMENT_LOGIC",
                    "detail": "具有標頭資訊，但內部無任何有效的控制邏輯"
                })
                continue

            out_path = gid_dir / f"{std_id}_refined.json"
            self.save_json(result, out_path)
            
            bls_registry[std_id] = {
                "tag": matched_tag_info.get("tag") or raw_id_str,
                "path": str(out_path.relative_to(self.resolver.project_root)),
                "alias": result.get("logic_alias"),
                "comment": result.get("comment"),
                "action": result.get("action")
            }
            processed_count += 1
        
        self.save_json(bls_registry, build_dir / "GEN_bls_registry.json")
        
        # --- Update Skipped Files Track ---
        skip_file_path = build_dir / "GEN_skipped_files.json"
        existing_skips = {"unit": self.resolver.unit, "skipped_files": []}
        if skip_file_path.exists():
            try:
                with open(skip_file_path, "r", encoding="utf-8") as f:
                    existing_skips = json.load(f)
            except Exception:
                pass
                
        # Filter old BLS skips, add newly found ones
        updated_skips = [s for s in existing_skips.get("skipped_files", []) if s.get("type", "") != "BLS"]
        updated_skips.extend(skipped_records)
        existing_skips["skipped_files"] = updated_skips
        
        with open(skip_file_path, "w", encoding="utf-8") as f:
            json.dump(existing_skips, f, indent=2, ensure_ascii=False)

        print(f"✅ Active-Scan Pipeline-Ready: {processed_count} files processed. ({len(skipped_records)} skipped/warnings tracked)")
        self.handshake(processed_count)

if __name__ == "__main__":
    parser = HitachiBLSParser()
    if parser.args.action in ["batch", "run"]: parser.run_batch()
