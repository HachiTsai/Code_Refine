import subprocess
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# ==============================================================================
# 🛡️ [v2.0] Type Shield & Logic Contract
# ==============================================================================
__version__ = "v1.6 (Commit-Workflow Hardening)"

class CommitContract:
    """[v2.0] 邏輯契約：驗證 Git 暫存狀態與規格書 SSOT 完整性。"""
    
    @staticmethod
    def validate_staged_changes() -> bool:
        """驗證是否有已暫存 (staged) 的變更。"""
        try:
            status_check = subprocess.run(["git", "diff", "--staged", "--quiet"], capture_output=True)
            if status_check.returncode == 0:
                print("   ⚠️ [Contract] Warning: No staged changes found. Please `git add` first.")
                return False
            return True
        except Exception as e:
            print(f"   ❌ [Contract] Error checking git status: {e}")
            return False

    @staticmethod
    def validate_spec(spec_path: Path) -> bool:
        """驗證 SSOT 規格書是否存在。"""
        if not spec_path.exists():
            print(f"   ❌ [Contract] Error: Git commit protocol spec not found: {spec_path}")
            return False
        return True

# ==============================================================================
# 🛠️ Utility Functions
# ==============================================================================

def get_git_diff() -> Optional[str]:
    """取得過濾 json 後的 staged diff"""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--", ".", ":(exclude)*.json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ [Git] Error getting diff: {e}", file=sys.stderr)
        return None

def get_git_stats() -> str:
    """取得變更統計數據"""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--stat", "--", ".", ":(exclude)*.json"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return "N/A"

def read_spec(spec_path: Path) -> str:
    """讀取 SSOT 規格書"""
    try:
        return spec_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ [Spec] Error reading spec: {e}", file=sys.stderr)
        return "WARNING: spec-git-commit-protocol.md not found!"

# ==============================================================================
# 🚀 Main Logic
# ==============================================================================

def main() -> None:
    print(f"🚀 [Commit Workflow] Initializing {__version__}...")
    
    # Step 1: Logic Contract Check (Staged Changes)
    if not CommitContract.validate_staged_changes():
        sys.exit(0)

    spec_path = Path(".gemini/skills/git-commit-workflow/references/spec-git-commit-protocol.md")
    
    # Step 2: Logic Contract Check (Spec SSOT)
    if not CommitContract.validate_spec(spec_path):
        sys.exit(1)

    diff_content = get_git_diff()
    stats = get_git_stats()
    spec_content = read_spec(spec_path)
    
    # Step 3: Construct Agent Directive
    agent_prompt = f"""
==============================================================================
🔴 AGENT 強制執行指令 (MANDATORY DIRECTIVE v7.5) 🔴
==============================================================================
身為 Gemini CLI，你現在被 `git-commit-workflow` 技能接管。
請嚴格根據下方的 [Git 變更內容] 與 [規格書要求]，草擬 2 個 Commit Message 選項給使用者。

### 你的標準作業程序 (SOP):
1. **[理解]** 閱讀下方的 `diff` 與 `stats`，深度理解本次變更的「意圖」與「架構影響」。
2. **[合規]** 閱讀 `SSOT 規格書`，確認 `Type`、`Scope` 與 `Body 結構`。
3. **[溯源]** **Commit Body 必須包含「研發決策理由」與「Pending Tasks」，以利明日審計。**
4. **[交互]** 在終端機印出 2 個草案。當使用者選定後，將最終版本寫入 `.git/COMMIT_MSG_TEMP`。
5. **[提交]** 執行 `git commit -F .git/COMMIT_MSG_TEMP`。
6. **[同步]** 提交成功後，執行 `git push`。

------------------------------------------------------------------------------
📂 [Git 變更統計 (Stats)]
{stats}

------------------------------------------------------------------------------
📄 [Git 變更內容 (Diff, excludes JSON, max 3000 chars)]
{diff_content[:3000] if diff_content else "None"}

------------------------------------------------------------------------------
📜 [SSOT 規格書 (spec-git-commit-protocol.md)]
{spec_content}
==============================================================================
"""
    print(agent_prompt)

if __name__ == "__main__":
    main()
