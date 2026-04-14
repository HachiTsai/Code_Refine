import sys
import argparse
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Type, Optional

# ==========================================
# 🏗️ 模組名稱 (v2.0: 統一抽取引擎)
# 職責：提供單一邏輯（DDC, SEQ, BLS）的快速提煉入口，具備自動防呆與退場機制。
# ==========================================

# Adjust sys.path to load from ex-n01a-engine
engine_root = Path(__file__).resolve().parents[1]
sys.path.append(str(engine_root / "src"))

from utils import PathResolver
from semantic_injector import SemanticInjector
from parsers.bls_parser import HitachiBLSParser
from parsers.seq_parser import HitachiSEQParser
from parsers.ddc_parser import HitachiDDCParser

# ---------------------------------------------------------
# 🛡️ V2 自檢架構 (RefineryContract)
# ---------------------------------------------------------
class FallbackExtractor:
    """
    職責：當遇到了未知的解析類型 (Type) 時，提供優雅的退場防護，
    而非在深層調用中觸發難以追蹤的 Fatal Error。
    """
    def __init__(self, description: str = ""):
        pass
        
    def parse_file(self, *args, **kwargs) -> Optional[Dict[str, Any]]:
        print("   ❌ [Fallback] 解析類型不受支援。目前僅支援：BLS, SEQ, DDC。")
        return None

class UnifiedExtractor:
    def __init__(self):
        # 1. 建立專屬 Parser 避免與 BaseParser 衝突
        self.parser = argparse.ArgumentParser(description="DCS Unified Single Extractor (v2.0)")
        self.parser.add_argument("--client", default="RCMT", help="Client Name")
        self.parser.add_argument("--site", default="Johor", help="Site Location")
        self.parser.add_argument("--unit", required=True, help="Plant Unit (e.g. MLC01)")
        self.parser.add_argument("--type", required=True, choices=["BLS", "SEQ", "DDC"], help="Extraction Category")
        self.parser.add_argument("--tag", required=True, help="Tag ID to extract")
        self.parser.add_argument("--raw", required=True, help="Raw filename")
        
        self.args = self.parser.parse_args()
        self.resolver = PathResolver(client=self.args.client, site=self.args.site, unit=self.args.unit)

    def _get_parser_instance(self) -> Any:
        """動態解耦：根據 type 初始化對應的 Parser，並注入安全的 sys.argv 防護"""
        # ==========================================
        # 🛡️ Argv Sandbox Protection
        # ==========================================
        # 備份真實 sys.argv，提供一組乾淨的 args 讓 BaseParser 安全初始化
        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0], "--client", self.args.client, "--site", self.args.site, "--unit", self.args.unit]
        
        try:
            if self.args.type == "BLS":
                return HitachiBLSParser()
            elif self.args.type == "SEQ":
                return HitachiSEQParser()
            elif self.args.type == "DDC":
                return HitachiDDCParser()
            else:
                return FallbackExtractor()
        finally:
            # 恢復原本的 sys.argv
            sys.argv = original_argv

    def _log_skip(self, file_name: str, reason: str, detail: str):
        skip_file_path = self.resolver.build_base / "GEN_skipped_files.json"
        skip_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing_skips = {"unit": self.resolver.unit, "skipped_files": []}
        if skip_file_path.exists():
            try:
                with open(skip_file_path, "r", encoding="utf-8") as f:
                    existing_skips = json.load(f)
            except Exception:
                pass
                
        existing_skips["skipped_files"].append({
            "file": file_name,
            "type": getattr(self.args, 'type', 'UNKNOWN'),
            "status": "SKIPPED",
            "reason": reason,
            "detail": detail
        })
        
        with open(skip_file_path, "w", encoding="utf-8") as f:
            json.dump(existing_skips, f, indent=2, ensure_ascii=False)

    def extract(self):
        print(f"🚀 [Unified Extractor] Initializing {self.args.type} extraction for {self.args.tag}...")
        
        if "_" in self.args.tag:
            print(f"   ⚠️ [Warning] 位號含有底線等風險字符: {self.args.tag}，可能會導致後綴對齊落差。")

        raw_dir = self.resolver.get_raw(self.args.type)
        raw_path = raw_dir / self.args.raw
        
        if not raw_path.exists():
            print(f"   ❌ [Error] Raw檔不存在: {raw_path}")
            self._log_skip(self.args.raw, "FILE_NOT_FOUND", "指定的 RAW 檔案不存在物理目錄中")
            return
            
        parser_instance = self._get_parser_instance()
        result = None
        
        # ==========================================
        # 🧩 Dynamic Strategy Execution
        # ==========================================
        try:
            if self.args.type == "BLS":
                # BLS 需要 tag_info，提供動態補償前綴而非寫死
                dummy_info = {"tag": self.args.tag, "prefix": "BL"} 
                result = parser_instance.parse_bls_file(raw_path, dummy_info)
            elif self.args.type == "SEQ":
                result = parser_instance.extract_unit_logic(raw_path)
            elif self.args.type == "DDC":
                result = parser_instance.parse_loop(raw_path)
            elif isinstance(parser_instance, FallbackExtractor):
                result = parser_instance.parse_file()
        except Exception as e:
            print(f"   ❌ [Error] 解析過程發生異常: {e}")
            traceback.print_exc()
            self._log_skip(raw_path.name, "PARSE_ERROR", f"解析異常: {str(e)}")
            return
            
        is_empty = not result
        if self.args.type == "BLS" and result:
            is_empty = not result.get('statements')
        elif self.args.type == "SEQ" and result:
            is_empty = not any([result.get('always'), result.get('pattern'), result.get('shift'), result.get('correction')])

        if is_empty:
            print("   ⚠️ [Warning] 萃取結果為空或無效負載，已紀錄至 skipped_files 並停止後續注入。")
            self._log_skip(raw_path.name, "EMPTY_PAYLOAD", "萃取結果為空或不具備有效的控制邏輯/矩陣")
            return
            
        # 儲存 GID (自動補全 Suffix)
        full_tag = self.args.tag if self.args.tag.endswith(self.resolver.unit_suffix) else f"{self.args.tag}{self.resolver.unit_suffix}"
        gid_dir = self.resolver.get_gid(self.args.type)
        gid_dir.mkdir(parents=True, exist_ok=True)
        gid_path = gid_dir / f"{full_tag}_refined.json"
        
        try:
            with open(gid_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"   ✅ [GID] 成功儲存至: {gid_path}")
        except Exception as e:
            print(f"   ❌ [Error] GID 寫入失敗: {e}")
            return
            
        # ==========================================
        # 🧠 Smart Core Injection (DRY 合規)
        # ==========================================
        print(f"   🧠 Injecting semantics for {self.args.tag}...")
        injector = SemanticInjector(self.resolver)
        injected = injector.inject_to_gid(result)
        
        # 套用與 semantic_injector.py 相同的 metadata 寫入邏輯
        meta = result.get("metadata", {}) if isinstance(result, dict) else {}
        from semantic_injector import __version__ as injector_version
        
        meta.update({
            "unit": self.resolver.unit,
            "unit_suffix": self.resolver.unit_suffix,
            "refinery_v": injector_version,
            "summary": result.get("comment", ""),
            "importance": "",
            "expert_insight": ""
        })
        
        if isinstance(injected, dict):
            injected["metadata"] = meta
            final_data = injected
        else:
            final_data = {
                "metadata": meta,
                "entries": injected
            }
            
        core_dir = injector.resolver.get_core(self.args.type)
        core_dir.mkdir(parents=True, exist_ok=True)
        core_path = core_dir / f"{full_tag}_core.json"
        
        try:
            with open(core_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            print(f"   ✅ [CORE] 成功儲存至: {core_path}")
        except Exception as e:
            print(f"   ❌ [Error] CORE 寫入失敗: {e}")

if __name__ == "__main__":
    extractor = UnifiedExtractor()
    extractor.extract()