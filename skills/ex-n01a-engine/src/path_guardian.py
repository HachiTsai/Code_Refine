import json
import os
from pathlib import Path
from typing import Dict, List, Any

class PathGuardian:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_integrity(self, index_path: Path) -> List[str]:
        """檢查索引檔案中的路徑是否全都存在"""
        errors = []
        if not index_path.exists():
            return [f"Index file missing: {index_path}"]

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 根據資料格式檢查路徑
            if isinstance(data, list):
                # 處理 IDX_metadata.json
                for item in data:
                    path = self.project_root / item.get("source", "")
                    if not path.exists():
                        errors.append(f"Broken link in metadata: {item.get('source')}")
            elif isinstance(data, dict):
                # 處理 IDX_logic.index
                for obj_id, rel_path in data.items():
                    path = self.project_root / rel_path
                    if not path.exists():
                        errors.append(f"Broken link for {obj_id}: {rel_path}")
        except Exception as e:
            errors.append(f"Analysis error in {index_path.name}: {e}")
            
        return errors

if __name__ == "__main__":
    project_path = Path(__file__).resolve().parents[4]
    guardian = PathGuardian(project_path)
    index_dir = project_path / "_assets" / "30_Digital_Twin" / "index"
    
    print("--- 數位孿生健康檢查 (Integrity Check) ---")
    
    for idx_file in index_dir.glob("*"):
        if idx_file.suffix in [".index", ".json"]:
            print(f"Checking index: {idx_file.name}...")
            issues = guardian.check_integrity(idx_file)
            if not issues:
                print("  [PASS] All links are valid.")
            else:
                for err in issues:
                    print(f"  [FAIL] {err}")
    
    print("\n健康檢查完成。")