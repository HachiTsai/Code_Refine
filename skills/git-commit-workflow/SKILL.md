---
name: git-commit-workflow
description: 自動化與結構化 Git 提交流程管理器，強制讀取 SSOT 並驅動 Agent 產出符合規範的 Commit Message。
metadata:
  version: v1.5
  governance: "[[../../conductor/tech-stack.md|系統標準指令集]]"
---

# Git Commit Workflow Skill

## 📋 觸發指令
- `開始提交流程`
- `python .gemini/skills/git-commit-workflow/src/committer.py`

## 🎯 核心職能
1. **防呆防漏**：腳本自動排除 `*.json` 等雜訊，提取精確的 staged diff。
2. **SSOT 強制綁定**：腳本內建讀取 `conductor/spec-git-commit-protocol.md`，並將規則直接輸出給 Agent 執行。
3. **安全提交**：強制要求 Agent 將結果寫入 `.git/COMMIT_MSG_TEMP`，並使用 `git commit -F` 執行。

## 🛡️ 安全規範
1. 嚴禁在此流程中查詢 `git log` 或處理歷史。
2. Agent 拿到腳本輸出的提示詞後，必須提供 2 個選項讓使用者挑選。
3. 提交完成後必須自動執行 `git push`（除非使用者拒絕）。

## 🚫 禁止事項
1. 禁止 Agent 擅自使用 `git commit -m` 提交長篇結構化內容。
2. 禁止 Agent 憑記憶草擬 Commit Message，必須依賴 `committer.py` 產出的標準框架。

---
*Last Updated: 2026-04-11 | System Version: v8.6*
