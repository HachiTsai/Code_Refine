import os
import re
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Union, Tuple

# ==========================================
# 🏗️ kb-capture: Archiver Service (v5.5)
# 職責：實作知識路徑路由、骨架注入與 Inbox 清理邏輯。
# 協定：遵循「智慧提煉優先」協定，確保資產元數據完整。
# ==========================================
__version__ = "v5.5 (Modularized Archiver)"

# 強制 UTF-8 輸出環境 (Win32 誠信防線)
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class ArchiverContract:
    """[v2.1] 邏輯契約：驗證歸檔任務的路由、骨架注入與清理完整性。"""

    @staticmethod
    def validate_content(inbox_path: Path, direct_content: Optional[str] = None) -> bool:
        """驗證是否有可供捕捉的內容。"""
        has_inbox = inbox_path.exists() and inbox_path.stat().st_size > 5
        if not has_inbox and not direct_content:
            print(f"   ❌ [Contract] Error: No content found in Inbox or --content argument.")
            return False
        return True

    @staticmethod
    def validate_capture(target_file: Path) -> bool:
        """驗證捕捉後的知識資產是否包含骨架 (YAML) 且物理存在。"""
        if not target_file.exists():
            print(f"   ❌ [Contract] Error: Capture failed, file not created: {target_file}")
            return False
        content = target_file.read_text(encoding="utf-8")
        if "---" not in content or "id:" not in content:
            print(f"   ⚠️ [Contract] Warning: Asset may be missing YAML skeleton: {target_file}")
            return False
        return True

# ==============================================================================
# 🏗️ Archiver Service Core
# ==============================================================================

class ArchiverService:
    """[v5.1] 核心日誌歸檔服務。"""
    def __init__(self, project_root: Optional[Union[str, Path]] = None) -> None:
        # 自動尋找根目錄
        if project_root:
            self.root = Path(project_root).resolve()
        else:
            curr = Path(__file__).resolve()
            found_root = None
            for parent in curr.parents:
                if (parent / "GEMINI.md").exists() and (parent / "conductor").exists():
                    found_root = parent
                    break
            self.root = found_root if found_root else Path.cwd()

        self.inbox_path = self.root / "00_Inbox" / "AskGemini.md"
        self.tz = timezone(timedelta(hours=8))
        
        # 導入 SkeletonInjector (模組化導入)
        try:
            from .skeleton import SkeletonInjector
            self.injector = SkeletonInjector(project_root=self.root)
        except (ImportError, ValueError):
            # Fallback for standalone execution
            from skeleton import SkeletonInjector
            self.injector = SkeletonInjector(project_root=self.root)

    def run_capture(self, k_type: Optional[str] = None, topic: Optional[str] = None, content: Optional[str] = None, custom_date: Optional[str] = None, summary: Optional[str] = None, importance: Optional[str] = None, strategic_positioning: Optional[str] = None) -> None:
        """執行收割流程的主入口。"""
        k_type = k_type or "log"
        topic = topic or "general"
        
        if k_type == "log":
            self.capture_log(topic, direct_content=content, summary=summary, importance=importance, strategic_positioning=strategic_positioning)
        else:
            self.capture_knowledge(k_type, topic, direct_content=content, custom_date=custom_date, summary=summary, importance=importance, strategic_positioning=strategic_positioning)

    def capture_knowledge(self, k_type: str, topic: str, custom_dir: Optional[str] = None, direct_content: Optional[str] = None, custom_date: Optional[str] = None, summary: Optional[str] = None, importance: Optional[str] = None, strategic_positioning: Optional[str] = None) -> None:
        """[Action] 將內容收割為具備骨架的獨立知識資產。"""
        if not ArchiverContract.validate_content(self.inbox_path, direct_content):
            return

        final_content = ""
        if self.inbox_path.exists():
            final_content = self.inbox_path.read_text(encoding="utf-8").strip()

        if direct_content:
            separator = "\n\n---\n\n" if final_content else ""
            final_content += separator + direct_content.strip()

        # 路由邏輯：直接使用 k_type 作為目錄名
        if custom_dir:
            target_dir = self.root / custom_dir
        else:
            target_dir = self.root / "20_Knowledge_Base" / "0_Worklogs" / k_type

        target_dir.mkdir(parents=True, exist_ok=True)

        # 檔名生成 (支援 custom_date)
        short_date = custom_date if custom_date else datetime.now(self.tz).strftime("%y%m%d")
        file_name = f"{k_type}-{short_date}-{topic.lower().replace(' ', '-')}.md"
        target_file = target_dir / file_name

        if target_file.exists():
            file_name = f"{k_type}-{short_date}-{topic.lower().replace(' ', '-')}-{datetime.now(self.tz).strftime('%H%M%S')}.md"
            target_file = target_dir / file_name

        # 骨架注入
        md_content = self.injector.inject_metadata(final_content, k_type, topic, summary=summary, importance=importance, strategic_positioning=strategic_positioning)
        target_file.write_text(md_content.strip() + "\n", encoding="utf-8")

        if ArchiverContract.validate_capture(target_file):
            print(f"✅ [Archiver] Content captured: {target_file}")
            if self.inbox_path.exists():
                self.inbox_path.write_text("", encoding="utf-8")
                print("   🧹 Inbox cleared.")
            self.handshake()

    def capture_log(self, topic: str = "general-log", direct_content: Optional[str] = None, **kwargs) -> None:
        """[System Note] 僅收割至 00_sys-notes，排他性路由。"""
        # 明確指定 custom_dir，這會在 capture_knowledge 中覆蓋預設的 worklogs 路徑
        self.capture_knowledge("knowhow", topic, custom_dir="conductor/archive/00_sys-notes", direct_content=direct_content, **kwargs)

    def handshake(self) -> None:
        """通知系統更新快取。"""
        try:
            manager_path = self.root / ".gemini/skills/workflow-orchestrator/scripts/skill_manager.py"
            if manager_path.exists():
                subprocess.run([sys.executable, str(manager_path), "--update-cache"], check=False, capture_output=True)
                print("   ✅ [Handshake] Skill cache updated.")
        except Exception as e:
            print(f"   ⚠️ [Handshake] Failed: {e}")

# ==============================================================================
# 🏁 Standalone Entry (Deprecated - use manager.py)
# ==============================================================================

if __name__ == "__main__":
    print("⚠️ Warning: Running src/archiver.py directly is deprecated. Please use scripts/manager.py.")
    service = ArchiverService()
    # 這裡保留基本的 capture 供緊急使用
    service.run_capture()
