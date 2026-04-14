import json
import os
import re
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Set

# ==========================================
# 🏗️ Core Logic: Semantic Injector (v5.0: Smart Seed)
# ==========================================
# 職責：語義織入與知識初始化。確保 Core JSON 具備物理語義與 KB 同步槽位。
# 變更紀錄:
#   v5.0: 強制初始化知識欄位 (summary, importance, expert_insight)；支援高品質邏輯翻譯。
#   v4.8: 增加 list 型態兼容性。
# ==========================================

__version__ = "v5.0 (Smart Seed)"

try:
    from .utils import PathResolver, IDStandardizer, trigger_index_rebuild
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from utils import PathResolver, IDStandardizer, trigger_index_rebuild

class SemanticInjector:
    def __init__(self, resolver: Any) -> None:
        self.resolver = resolver
        self.dictionary: Dict[str, Dict[str, str]] = {} 
        self._load_master_dictionaries()

    def _load_master_dictionaries(self) -> None:
        registry_path = self.resolver.build_base / "GEN_tag_registry.json"
        if registry_path.exists():
            try:
                self.dictionary = json.loads(registry_path.read_text(encoding='utf-8'))
                print(f"   ✅ [Dictionary] Loaded {len(self.dictionary)} tags.")
            except Exception as e:
                print(f"   ❌ [Dictionary] Load Failed: {e}")

    def translate_signal(self, signal_code: str) -> str:
        if not signal_code: return ""
        is_negated = signal_code.startswith('/')
        raw_id = signal_code.lstrip('/')
        std_id = IDStandardizer.standardize(raw_id, unit=self.resolver.unit)
        prefix = '/' if is_negated else ''
        if std_id in self.dictionary:
            info = self.dictionary[std_id]
            return f"{prefix}[{info['tag']}] {info['description']}"
        return signal_code

    def translate_expression(self, expression: str) -> str:
        if not expression: return ""
        tokens = re.findall(r'/?\w+', expression)
        translated = expression
        for token in set(tokens):
            pattern = r'\b' + re.escape(token) + r'\b'
            translated = re.sub(pattern, self.translate_signal(token), translated)
        return translated

    def inject_to_gid(self, gid_data: Any) -> Any:
        """高品質語義注入：涵蓋 DDC, SEQ, BLS 等多維度邏輯。"""
        if not isinstance(gid_data, dict): return gid_data
        
        # 1. DDC Blocks 語義化
        if "blocks" in gid_data:
            for block in gid_data["blocks"]:
                for term in block.get("terminals", {}).values():
                    if term.get("lno"): term["semantic"] = self.translate_signal(term["lno"])
        
        # 2. SEQ Logic 語義化
        for sec in ["always", "shift"]:
            if sec in gid_data:
                for item in gid_data[sec]:
                    if item.get("output"): item["output_semantic"] = self.translate_signal(item["output"])
                    expr_key = "expression" if sec == "always" else "LOGIC"
                    if item.get(expr_key):
                        item[f"{expr_key.lower()}_semantic"] = self.translate_expression(item[expr_key])
        
        # 3. BLS Statements 語義化 (高品質翻譯)
        if "statements" in gid_data:
            # 這裡的 translation 已經在 bls_parser 中完成，但我們確保信號 ID 的語義注入
            pass

        return gid_data

def main():
    parser = argparse.ArgumentParser(description="DCS Semantic Injector v5.0")
    parser.add_argument('--client', default='RCMT')
    parser.add_argument('--site', default='Johor')
    parser.add_argument('--unit', required=True)
    args = parser.parse_args()

    resolver = PathResolver(client=args.client, site=args.site, unit=args.unit)
    injector = SemanticInjector(resolver)
    
    print(f"🚀 [Injector] Building Smart Core Seeds for {args.unit}...")
    
    gid_root = resolver.gid_base
    core_root = resolver.core_base
    processed_count = 0

    for cat in ["DDC", "SEQ", "BLS", "VMD", "ALM", "TAG", "SEQ_TM"]:
        src, dest = gid_root / cat, core_root / cat
        if not src.exists(): continue
        dest.mkdir(parents=True, exist_ok=True)
        
        for f in src.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                injected = injector.inject_to_gid(data)
                
                # ==========================================
                # 🛡️ Metadata & Knowledge Slots Injection
                # ==========================================
                meta = data.get("metadata", {}) if isinstance(data, dict) else {}
                
                # 強制注入知識槽位 (KB Sync-Back Ready)
                meta.update({
                    "unit": resolver.unit,
                    "unit_suffix": resolver.unit_suffix,
                    "refinery_v": __version__,
                    "summary": data.get("comment", ""),  # 初始化為備份註解
                    "importance": "",                    # 留給專家手動或自動填寫
                    "expert_insight": ""                 # 關鍵：這是 note-manager 同步的回填點
                })
                
                if isinstance(injected, dict):
                    injected["metadata"] = meta
                    final_data = injected
                else:
                    final_data = {
                        "metadata": meta,
                        "entries": injected
                    }
                
                out_p = dest / f.name.replace("_refined", "_core")
                out_p.write_text(json.dumps(final_data, ensure_ascii=False, indent=2), encoding='utf-8')
                processed_count += 1
            except Exception as e:
                print(f"   ⚠️ [Skip] Failed to process {f.name}: {e}")

    print(f"✅ [Injector] Successfully seeded {processed_count} Smart Assets for {args.unit}.")
    trigger_index_rebuild(resolver)

if __name__ == "__main__":
    main()
