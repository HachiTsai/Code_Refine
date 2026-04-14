import json
import re
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ==========================================
# 🏗️ Core Logic: Knowledge Enhancer (v1.6: Unit-Centric)
# ==========================================
# 職責：深度知識增強。從外部知識報告 (Markdown) 提取語義，反哺至數位孿生核心。
# 變更紀錄:
#   v1.6: 全面遷移 plant -> unit 參數，對齊 PathResolver v7.0。
# ==========================================

# 🛠️ v6.3 標準：注入技能根目錄，使 src.utils 可被解析
scripts_path = Path(__file__).resolve().parent
skill_root = scripts_path.parent
if str(skill_root) not in sys.path:
    sys.path.insert(0, str(skill_root))

from src.utils import PathResolver, system_handshake

__version__ = "v1.6"

class KnowledgeEnhancer:
    def __init__(self, resolver: PathResolver):
        self.resolver = resolver

    def extract_knowledge(self, source_content: str) -> dict:
        knowledge: Dict[str, Any] = {}
        # 1. 提取 Dataview Inline Fields
        summary_match = re.search(r"Summary::\s*(.*)", source_content)
        if summary_match: knowledge["summary"] = summary_match.group(1).strip()
            
        importance_match = re.search(r"Importance::\s*(.*)", source_content)
        if importance_match: knowledge["importance"] = importance_match.group(1).strip()

        # 2. 提取 Expert Insight (Callout)
        insight_match = re.search(r"> [!INFO] AGENT 深度解析.*?\n(.*?)(?=\n---|#|$)", source_content, re.DOTALL | re.IGNORECASE)
        if insight_match:
            content = insight_match.group(1).strip()
            # 移除 Markdown 引用標籤
            knowledge["expert_insight"] = re.sub(r'^> ', '', content, flags=re.MULTILINE).strip()

        return knowledge

    def inject_to_core(self, loop_id: str, source_path: Path, category: str = "DDC"):
        if not source_path.exists(): return

        core_filepath = self.resolver.get_core(f"{category}/{loop_id}{self.resolver.unit_suffix}_core.json")
        if not core_filepath.exists(): return

        # 1. 讀取與提取
        source_content = source_path.read_text(encoding='utf-8')
        with open(core_filepath, 'r', encoding='utf-8') as f:
            core_data = json.load(f)

        extracted = self.extract_knowledge(source_content)
        if not extracted: return
            
        # 2. 注入 Metadata (同步更新)
        if "metadata" not in core_data: core_data["metadata"] = {}
        core_data["metadata"].update(extracted)
        
        # 3. 寫回檔案
        with open(core_filepath, 'w', encoding='utf-8') as f:
            json.dump(core_data, f, ensure_ascii=False, indent=2)
            
        print(f"✨ Enhanced {loop_id} core with existing KB wisdom.")

    def batch_backfeed(self, source_dir: Path):
        print(f"📡 [Batch-Backfeed] Scanning KB for {self.resolver.unit}...")
        for md_file in source_dir.rglob("*.md"):
            if md_file.name.startswith("00_") or "Dashboard" in md_file.name: continue
            
            # 解析檔名 ID (例如 LP001S02_TICAXXX.md -> LP001)
            match = re.match(r'^([A-Z0-9]+)', md_file.name)
            if not match: continue
            
            raw_id = match.group(1)
            loop_id = re.sub(r'S\d+$', '', raw_id)
            
            # 決定類別
            category = "DDC"
            if loop_id.startswith("US"): category = "SEQ"
            elif loop_id.startswith("BL"): category = "BLS"
            
            self.inject_to_core(loop_id=loop_id, source_path=md_file, category=category)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Knowledge Enhancer v1.6")
    parser.add_argument("--batch", help="Markdown 目錄路徑")
    parser.add_argument("--client", default="RCMT")
    parser.add_argument("--site", default="Johor")
    parser.add_argument("--unit", required=True)
    
    args = parser.parse_args()
    resolver = PathResolver(client=args.client, site=args.site, unit=args.unit)
    enhancer = KnowledgeEnhancer(resolver=resolver)
    
    if args.batch:
        enhancer.batch_backfeed(Path(args.batch))
    
    system_handshake(project_root=resolver.project_root)
