"""
🧠 Intelligence Navigator: Utilities (v2.1: Federated Path Edition)
============================================================
職責：語義導航技能的標準化工具組。提供跨平台路徑解析與 ID 歸一化。
美學：遵循 Aesthetic Hardening v3.0 規範。
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any

# ==========================================
# 🏗️ Core Logic: NavigatorPathResolver (v2.1: Federated Path Edition)
# ==========================================
# 職責：語義導航路徑解析。支援意圖驅動的動態參數注入與最後上下文暫存。
# 新增：COMMON 全域手冊路徑 + site_base 場區知識庫路徑。
# 邏輯優先級：CLI 參數 > 最後暫存 (Cache) > env_profiles.json (即將廢棄) > 硬編碼預設。
# ==========================================

class NavigatorPathResolver:
    """
    專為語義導航設計的路徑解析器。
    確保能從任何子目錄正確定位專案根目錄與數位孿生資產。
    """
    def __init__(self, client: Optional[str] = None, site: Optional[str] = None):
        self.project_root = self._find_project_root()
        self.cache_path = self.project_root / ".gemini/skills/intelligence-navigator/references/context_cache.json"
        
        # 1. 載入持久化或暫存上下文
        cached_context = self._load_context_cache()
        legacy_context = self._load_legacy_env_profiles()
        
        # 2. 確定當前上下文 (參數 > 暫存 > 舊有 > 預設)
        self.client = client or cached_context.get("client") or legacy_context.get("client") or "RCMT"
        self.site = site or cached_context.get("site") or legacy_context.get("site") or "Johor"
        
        # 3. 若有傳入新參數，自動更新暫存 (Context Mirroring)
        if client or site:
            self._save_context_cache({"client": self.client, "site": self.site})

        # 4. 建立數位孿生路徑 (SSoT)
        self.assets_base = self.project_root / "_assets"
        self.core_base = self.assets_base / "30_Digital_Twin" / "core" / self.client / self.site
        self.index_base = self.assets_base / "30_Digital_Twin" / "index" / self.client / self.site
        self.kb_base = self.project_root / "20_Knowledge_Base"

        # 5. 聯邦語義架構路徑 (Federated Semantic Architecture)
        self.manual_base = self.kb_base / "1_Hitachi_EX-N01A" / "0_Manual"
        self.common_index_base = self.assets_base / "30_Digital_Twin" / "index" / "COMMON"
        if self.site.upper() != "COMMON":
            self.site_base = self.kb_base / "1_Hitachi_EX-N01A" / f"1_{self.client}" / self.site
        else:
            self.site_base = self.manual_base

    def _find_project_root(self) -> Path:
        """尋找包含 GEMINI.md 的專案根目錄"""
        curr = Path(__file__).resolve()
        for parent in curr.parents:
            if (parent / "GEMINI.md").exists():
                return parent
        return Path(os.getcwd()).resolve()

    def _load_context_cache(self) -> Dict[str, str]:
        """讀取最後使用的上下文暫存"""
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception: return {}
        return {}

    def _save_context_cache(self, context: Dict[str, str]):
        """將當前上下文寫入暫存 (位於 references/ 目錄下)"""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"⚠️ [Cache] Failed to save context: {e}\n")

    def _load_legacy_env_profiles(self) -> Dict[str, str]:
        """[Legacy Support] 從 env_profiles.json 讀取業務上下文 (即將廢棄)"""
        env_file = self.project_root / "env_profiles.json"
        if not env_file.exists():
            return {}
        try:
            data = json.loads(env_file.read_text(encoding="utf-8"))
            return data.get("active_context", {})
        except Exception:
            return {}

    def get_db_path(self, create: bool = True) -> Path:
        """獲取 ChromaDB 物理路徑"""
        db_path = self.index_base / "chroma_db"
        if create:
            db_path.mkdir(parents=True, exist_ok=True)
        return db_path

    def get_global_db_path(self, create: bool = True) -> Path:
        """獲取全域技術手冊 COMMON ChromaDB 路徑"""
        db_path = self.common_index_base / "chroma_db"
        if create:
            db_path.mkdir(parents=True, exist_ok=True)
        return db_path

    def verify_context_exists(self) -> None:
        """驗證當前場區上下文的物理資料夾是否存在"""
        if self.site.upper() == "COMMON":
            # COMMON 模式無 core 目錄，改驗證 Manual 目錄
            if not self.manual_base.exists():
                raise FileNotFoundError(f"🛑 [架構錯誤] 找不到全域手冊目錄: {self.manual_base}")
            return
        if not self.core_base.exists():
            raise FileNotFoundError(f"🛑 [架構錯誤] 找不到廠區物理數據目錄: {self.core_base}\n請確認您指定的 Client/Site 是否正確。")
        
    def verify_db_exists(self) -> None:
        """驗證當前場區的語義索引庫是否已初始化"""
        db_path = self.get_db_path(create=False)
        # ChromaDB 至少會包含 sqlite 檔案
        sqlite_file = db_path / "chroma.sqlite3"
        if not db_path.exists() or not sqlite_file.exists():
            raise FileNotFoundError(f"🛑 [語義錯誤] 廠區 '{self.site}' ({self.client}) 的語義索引庫尚未建立。\n路徑: {db_path}\n若為新場區，請執行索引重建。")

# ==========================================
# 🏗️ Core Logic: NavigatorStandardizer
# ==========================================
class NavigatorStandardizer:
    """訊號位號與名稱的標準化工具"""
    @staticmethod
    def standardize_id(raw_id: str) -> str:
        """轉換為大寫並移除多餘空格"""
        return raw_id.strip().upper()

    @staticmethod
    def is_logic_loop(loop_id: str) -> bool:
        """判定是否為邏輯迴路 (LP/US/MPN/BL)"""
        p = loop_id.upper()
        return any(p.startswith(pref) for pref in ["LP", "US", "MPN", "BL"])

# ==========================================
# ⚖️ Compliance Check: NavigatorContract (V2)
# ==========================================
def _run_self_diagnostic():
    """執行 Navigator Utils 邏輯契約自檢"""
    print("\n🔍 [Self-Diagnostic] 啟動 Navigator Utils 契約驗證...")
    try:
        resolver = NavigatorPathResolver()
        # 驗證根目錄定位
        if not (resolver.project_root / "GEMINI.md").exists():
            raise FileNotFoundError("無法定位專案根目錄 (GEMINI.md 缺失)")
        
        # 驗證標準化邏輯
        test_id = " lp001 "
        if NavigatorStandardizer.standardize_id(test_id) != "LP001":
            raise ValueError("ID 標準化契約失效")
            
        print(f"   ✅ 專案根目錄定位: {resolver.project_root.name}")
        print("   ✅ 標準化工具驗證通過。")
        print("✨ [Self-Diagnostic] Navigator Utils 驗證完成。\n")
    except Exception as e:
        sys.stderr.write(f"🛑 [Navigator Contract Failure] {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    _run_self_diagnostic()
