import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# ==============================================================================
# 🛡️ [v2.1] Type Shield & Skeleton Contract
# ==============================================================================
__version__ = "v5.5 (Refined Metadata Injection)"

class SkeletonContract:
    """[v2.1] 邏輯契約：驗證知識類型定義與骨架注入的完整性。"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """驗證 knowledge_types.json 結構是否完整。"""
        if not config: return False
        # 檢查是否至少包含基本類型
        required = ["idea", "knowhow", "spec"]
        return all(k in config for k in required)

    @staticmethod
    def validate_injected_content(content: str) -> bool:
        """驗證注入後的內容是否具備 YAML 邊界。"""
        return content.startswith("---") and content.count("---") >= 2

# ==============================================================================
# 🏗️ Skeleton Injector Core
# ==============================================================================

class SkeletonInjector:
    """負責為原子化知識資產注入 YAML 元數據與 Dataview 欄位。"""
    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root if project_root else Path.cwd()
        # 嘗試從多個可能路徑載入配置 (相容性增強)
        potential_configs = [
            self.root / ".gemini/skills/kb-capture/assets/knowledge_types.json",
            self.root / ".gemini/skills/daily-log-workflow/assets/knowledge_types.json"
        ]
        self.config_path = next((p for p in potential_configs if p.exists()), potential_configs[0])
        self.tz = timezone(timedelta(hours=8))
        self.knowledge_types = self._load_types()

    def _load_types(self) -> Dict[str, Any]:
        """讀取知識類型設定 (v5.5 Dynamic Asset)。"""
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text(encoding="utf-8"))
                if SkeletonContract.validate_config(config):
                    return config
            except Exception as e:
                print(f"   ⚠️ [Skeleton] Warning: Failed to load configuration: {e}")
        return {}

    def generate_id(self, k_type: str, topic: str) -> str:
        """生成唯一 ID: KB-[TYPE]-[TOPIC_UPPER]-[YYMMDD]。"""
        prefix = self.knowledge_types.get(k_type, {}).get("id_prefix", f"KB-{k_type.upper()}")
        # 清洗 Topic，僅保留字母與數字，防止路徑注入
        safe_topic = re.sub(r'[^a-zA-Z0-9]', '_', topic.upper())
        short_date = datetime.now(self.tz).strftime("%y%m%d")
        return f"{prefix}-{safe_topic}-{short_date}"

    def inject_metadata(self, content: str, k_type: str, topic: str, summary: Optional[str] = None, importance: Optional[str] = None, strategic_positioning: Optional[str] = None) -> str:
        """核心注入邏輯 (v5.5: 強化缺失 Metadata 的警示占位)。"""
        # --- YAML 碰撞偵測 (Collision Detection) ---
        content = content.strip()
        has_existing_yaml = content.startswith("---") and content.count("---") >= 2

        if has_existing_yaml:
            print(f"   ℹ [Skeleton] Existing YAML detected in '{topic}', skipping duplicate injection.")
            return content

        meta = self.knowledge_types.get(k_type, {})
        full_date = datetime.now(self.tz).strftime("%Y-%m-%d")

        # 使用傳入的參數或警示性預設佔位符
        final_summary = summary or f"⚠️ [MISSING] 請手動執行智慧提煉並定義摘要。"
        final_importance = importance or f"⚠️ [MISSING] 請定義此資產的戰略地位與因果影響。"
        final_positioning = strategic_positioning or f"⚠️ [PENDING] 待補充。"

        # 1. 構建 YAML (SSOT Metadata & Semantic Fields)
        yaml = [
            "---",
            f"id: {self.generate_id(k_type, topic)}",
            f"type: {k_type.capitalize()}",
            "status: Incubation",
            f"tags:\n  - {k_type}",
            f"summary: \"{final_summary}\"",
            f"importance: \"{final_importance}\"",
            f"strategic_positioning: \"{final_positioning}\"",
            f"created: {full_date}",
            f"updated: {full_date}",
            "---"
        ]

        # 2. 注入「智慧綜述報告結構 (Agent-Driven Scaffold)」
        scaffold = ""
        if k_type in ["knowhow", "spec", "research"] and "#" not in content[:50]:
            scaffold = f"# 🏗️ {topic.upper()} 專家級解析報告\n\n"
            scaffold += "## 📊 1. 核心參數與基準 (Control Baseline)\n| 參數 | 數值 | 工程意圖與設計理由 |\n| :--- | :---: | :--- |\n| [待補全] | [值] | [理由] |\n\n"
            scaffold += "## 🧬 2. 邏輯行為模擬 (Behavioral Simulation)\n- **預期表現**: \n- **關鍵指標**: \n\n"
            scaffold += "## 💡 3. 技師心得與戰略診斷\n\n"

        # 3. 組合內容
        final_md = "\n".join(yaml) + "\n\n" + scaffold + content

        return final_md


