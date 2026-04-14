import re
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

# ==========================================
# 🏗️ Core Logic: Hitachi Tag Parser (v5.5)
# ==========================================
# 職責：位號 (Tag) 定義解析。處理 tag_*.txt 原始碼並建立全局位號字典。
# 語義：還原 DCS 的物理位址、語義位號與工程描述之間的對應關係。
# ==========================================

__version__ = "v6.6 (Engine Hardening)"

try:
    from .base import BaseParser
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from parsers.base import BaseParser

class HitachiTagParser(BaseParser):
    def __init__(self):
        # ==========================================
        # 🗺️ Initialization
        # ==========================================
        super().__init__(description="Hitachi Tag Parser v5.5")

    def parse_file(self, file_path: Path, prefix: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """解析單一位號定義檔案"""
        # ==========================================
        # 📂 Tag Definition Extraction
        # ==========================================
        if not file_path.exists(): return []
            
        refined_tags = []
        content = self.read_text(file_path)
        lines = content.splitlines()
        extracted_count = 0
        
        for index, line in enumerate(lines[1:]):
            if limit is not None and extracted_count >= limit: break
            
            # 物理 ID (例如 AI0000)
            no = index 
            internal_id = f"{prefix}{no:04d}"
            parts = line.split('\t')
            raw_field = parts[0].strip() if len(parts) > 0 else ""
            
            if not raw_field or raw_field in ["W", "0", "1"]:
                continue
            if raw_field == "TAG COMMENT": continue
            
            # 解析：[TAG]Description
            match = re.match(r'\[(.*?)\]\s*(.*)', raw_field)
            if match:
                tag_id, description = match.group(1).strip(), match.group(2).strip()
            else:
                tag_id, description = raw_field, ""
            
            tag_id = self.standardize(tag_id)
            refined_tags.append({
                "no": no, "internal_id": self.standardize(internal_id), 
                "tag": tag_id, "description": description, "prefix": prefix
            })
            extracted_count += 1
            
        print(f"   Parsed {len(refined_tags)} tags from {file_path.name}")
        return refined_tags

    def run_batch_registry(self):
        # ==========================================
        # 🚜 Batch Registry Build Protocol
        # ==========================================
        print(f"🚀 Starting Tag Registry Build for {self.resolver.context_path}...")
        raw_dir, gid_dir = self.resolver.get_raw("TAG"), self.resolver.get_gid("TAG")
        
        configs = [
            {"file": "tag_aitag.txt", "p": "AI"}, {"file": "tag_aotag.txt", "p": "AO"},
            {"file": "tag_ditag.txt", "p": "DI"}, {"file": "tag_dotag.txt", "p": "DO"},
            {"file": "tag_evtag.txt", "p": "EV"}, {"file": "tag_bltag.txt", "p": "BL"},
            {"file": "tag_ogtag.txt", "p": "OG"}, {"file": "tag_uatag.txt", "p": "UA"},
            {"file": "tag_intag.txt", "p": "IN"}, {"file": "tag_gltag.txt", "p": "GL"},
            {"file": "tag_gstag.txt", "p": "GS"}, {"file": "tag_gxtag.txt", "p": "GX"},
            {"file": "tag_zotag.txt", "p": "ZO"}, {"file": "tag_ixtag.txt", "p": "IX"}
        ]
        
        global_registry, total_tags = {}, 0
        for c in configs:
            src = raw_dir / c["file"]
            tags = self.parse_file(src, c["p"])
            if tags:
                for t in tags:
                    global_registry[t["internal_id"]] = {"tag": t["tag"], "description": t["description"], "prefix": t["prefix"], "offset": t["no"]}
                total_tags += len(tags)
                out_name = c["file"].replace("tag_", "").replace(".txt", "_refined.json")
                self.save_json(tags, gid_dir / out_name)
        
        self.save_json(global_registry, self.resolver.build_base / "GEN_tag_registry.json")
        
        # --- 🤝 Final Handshake ---
        self.handshake(total_tags, status="Success")

if __name__ == "__main__":
    parser = HitachiTagParser()
    if parser.args.action in ["batch-registry", "run"]: parser.run_batch_registry()
