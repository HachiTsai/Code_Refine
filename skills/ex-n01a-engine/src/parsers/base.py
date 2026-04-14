import json
import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

# ==========================================
# 🏗️ Core Logic: Hitachi Parser Base (v6.7)
# ==========================================
# 職責：解析器基類。提供原子化寫入、編碼守護、握手協議與站點隔離標準。
# 語義：定義所有 Hitachi DCS 解析器的共同行為準則與路徑解析基準。
# ==========================================

__version__ = "v6.7 (Interface Alignment)"

# 確保能匯入 utils
try:
    from ..utils import PathResolver, trigger_index_rebuild, IDStandardizer
except ImportError:
    # 修復路徑問題，確保可從 script 直接執行
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from utils import PathResolver, trigger_index_rebuild, IDStandardizer

class BaseParser:
    def __init__(self, description: str):
        # ==========================================
        # 🗺️ Initialization & Context Context
        # ==========================================
        self.args = self._parse_args(description)
        # 初始化 PathResolver，注入 CLI 傳入的上下文 (plant -> unit)
        self.resolver = PathResolver(
            client=self.args.client,
            site=self.args.site,
            unit=self.args.unit
        )
        self.specs = {}
        # 注入單元語義資訊
        self.unit_suffix = self.resolver.unit_suffix
        self.global_scope = self.resolver.global_scope

    def standardize(self, raw_id: str, unit: Optional[str] = None) -> str:
        """位號標準化捷徑：自動注入當前單元的站點後綴"""
        target_unit = unit if unit else str(self.args.unit)
        return IDStandardizer.standardize(raw_id, unit=target_unit)

    def _parse_args(self, description: str):
        """標準化 CLI 參數解析 (Align with Note-Manager)"""
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument('--client', default='RCMT', help='Client Name')
        parser.add_argument('--site', default='Johor', help='Site Location')
        parser.add_argument('--unit', default='MLC01', help='Unit ID (e.g. MLC01)')
        parser.add_argument('--action', default='run', help='Action to perform')
        return parser.parse_args()

    def load_specs(self, filename: str):
        # ==========================================
        # 📜 Specification Loading
        # ==========================================
        path = self.resolver.get_ref(filename)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.specs = json.load(f)
        else:
            print(f"⚠️ Warning: Spec file not found: {path}")

    def read_text(self, file_path: Path) -> str:
        """編碼守護讀取：嘗試 UTF-8，失敗則嘗試 Shift-JIS (日立原生)"""
        # ==========================================
        # 📂 Secure Text Reading (Multi-Encoding)
        # ==========================================
        if not file_path.exists():
            return ""
        
        try:
            return file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to Shift-JIS for legacy Hitachi files
                content = file_path.read_text(encoding='shift_jis')
                return content
            except Exception as e:
                print(f"❌ Encoding Error reading {file_path}: {e}")
                return ""

    def save_json(self, data: Any, file_path: Path):
        """原子化寫入：先寫入 tmp，驗證後覆寫"""
        # ==========================================
        # 💾 Atomic Persistence & Metadata Injection
        # ==========================================
        # 1. 確保目錄存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 1.1 自動注入 Metadata (僅針對 Core JSON 的 dict 格式)
        if isinstance(data, dict):
            if "metadata" not in data:
                data["metadata"] = {}
            
            if "unit_suffix" not in data["metadata"]:
                data["metadata"]["unit_suffix"] = self.unit_suffix
            if "global_scope" not in data["metadata"]:
                data["metadata"]["global_scope"] = self.global_scope
            if "unit" not in data["metadata"]:
                data["metadata"]["unit"] = self.resolver.unit
        
        # 2. 寫入暫存檔
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.tmp', dir=file_path.parent) as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp.name)
            
        # 3. 驗證完整性
        try:
            with open(tmp_path, 'r', encoding='utf-8') as f:
                json.load(f)
            
            # 4. 原子覆寫 (Atomic Move)
            if file_path.exists():
                file_path.unlink()
            tmp_path.rename(file_path)
            print(f"✅ Saved: {file_path.name}")
            
        except Exception as e:
            print(f"❌ Save Failed (Validation Error): {e}")
            if tmp_path.exists():
                tmp_path.unlink()

    def handshake(self, output_count: int, status="Success"):
        """與 Workflow Orchestrator 握手回報"""
        # ==========================================
        # 🤝 Orchestration Handshake & Linkage
        # ==========================================
        print(f"🤝 Handshaking with Orchestrator (Status: {status}, Output: {output_count})...")
        
        orch_script = self.resolver.project_root / ".gemini/skills/workflow-orchestrator/scripts/skill_manager.py"
        
        if orch_script.exists():
            try:
                subprocess.run([sys.executable, str(orch_script), "--update-cache"], check=False, capture_output=True)
                print("   ✅ Handshake successful.")
            except Exception as e:
                print(f"   ⚠️ Handshake failed: {e}")
        
        # [核心連動] 完成提煉後，自動觸發索引重建 (Signal Trace / Logic Index)
        trigger_index_rebuild(self.resolver)
