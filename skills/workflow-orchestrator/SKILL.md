---
name: workflow-orchestrator
description: Gemini 系統管理員與總機。負責技能全生命週期管理、組件 Hash 誠信治理、殭屍技能物理偵測，以及文檔與代碼的同步審計 (Mode B)。
metadata:
  version: v5.1
  governance: "[[../../conductor/tech-stack.md|系統標準指令集]]"
---

# Skill: Workflow Orchestrator ( Gemini 系統管理員 )

## 📋 觸發指令 (Trigger Commands)

本技能是系統的 **「運作核心」**，負責所有技能的生命週期、全域對齊與環境感知治理。

- `同步核心文件及版本` (SSOT 一鍵對齊)
- `全量組件 Hash 誠信審計` (更新 system_manifest.json)
- `上班技能審計` (on-work-audit, 包含 Hash 門禁與殭屍偵測校驗)
- `下班技能審計` (off-work-audit)

👉 **詳細指令集參考: [[conductor/tech-stack#5.2 系統治理 (Governance)|系統標準指令集]]**

---

## 🎯 核心職能 (Core Modules)

本技能採用模組化架構：`scripts/skill_manager.py` 為入口，`src/governance.py` 承載核心邏輯。

| 職能群組 | 核心職責 | 關鍵參數 (--action) |
| :--- | :--- | :--- |
| **Integrity (誠信)** | **[v5.0]** 實施 8 位短雜湊 (Short Hash) 組件追蹤，防止邏輯漂移。 | `--audit` |
| **Env-Aware (環境)** | **[v5.1]** 實作動態環境感知 (Win32/Darwin)，自動對位工具協定與編碼。 | `--on-work-audit` |
| **Zombie Audit (殭屍)** | **[v5.1]** 物理級偵測空殼技能目錄，自動拋出物理清理建議。 | `--update-cache` |
| **Gatekeeper (門禁)** | **[v5.0]** 實作 Mode B 文檔誠信偵測。當代碼更新但 `SKILL.md` 滯後時發出攔截警報。 | `--on-work-audit` |
| **SSOT Sync (對齊)** | 一鍵同步技能版本、日期至 README、憲法與技術棧。 | `--sync-all` |

---

## 🔄 誠信與同步自動化 SOP (Integrity & Alignment)

當執行 `同步核心文件及版本` (`--sync-all`) 時，系統按以下順序動作：

1. **Level 0 (Env Check)**: 透過 `OrchestratorContract` 偵測 OS 與 Conda 環境，鎖定 UTF-8 工具鏈。
2. **Level 1 (Hash Check)**: 遍歷所有技能的 `src/` 與 `scripts/`，計算 SHA-256 (8位) 雜湊。
3. **Level 2 (Doc Skew)**: 比對 `SKILL.md` 的 Hash，若代碼變動而文檔未變，標記 `doc_status = OUTDATED`。
4. **Level 3 (Manifest)**: 更新 `conductor/system_manifest.json`。
5. **Level 4 (Constitution)**: 將最新系統版本號與技能矩陣廣播至 `GEMINI.md`, `README.md`, `index.md` 與 `tech-stack.md`。

---

## 🛡️ 安全與規範 (Safety & Standards)

1. **單一事實來源 (SSoT)**：`system_manifest.json` 是唯一權威的組件清單，不再依賴手動維護的 Markdown 地圖。
2. **防呆攔截 (Active Prompting)**：只要審計中存在 `OUTDATED` 標籤的技能，Agent 必須強制閱讀警告並優先修復文件。
3. **Win32 誠信路徑**：在 Windows 環境下，強迫使用 `read_file` 與 `replace` 原生工具，嚴禁 Shell 管道 (Pipe) 導致的亂碼。

---

## 🚫 禁止事項

1. **禁止手動改版**：不要試圖手動編輯 Manifest 的 Hash 欄位，一律交由 `--audit` 計算。
2. **禁止涉入業務邏輯**：管理員不應包含 DCS 解析或數據清洗代碼，僅限系統治理。

---

## 📝 版本歷史

- **v5.1** (2026-04-07):
    - **FEATURE**: 升級治理核心至 **v1.2**，實施環境感知 (Environment-Aware) 與 Win32 工具硬化。
    - **FEATURE**: 強化殭屍技能物理偵測，整合元數據品質診斷 (Quality Gate)。
- **v5.0** (2026-03-28):
    - **SYNC**: 同步文檔雜湊以修復 Mode B 漂移。
    - **ARCH**: 實施模組化重構，對齊系統版本 v8.5。
- **v5.0** (2026-03-24):
    - **ARCH**: 實施模組化重構，切分出 `src/governance.py` 核心層。
    - **FEATURE**: 實作 Mode B 誠信門禁與攔截式警告區塊。
    - **DEPRECATE**: 廢除 `SKILL_MAP.md` 視覺化地圖，全面轉向 JSON Hash 追蹤。
- **v3.8** (2026-03-16):
    - **SYNC**: 實作全域元數據對齊邏輯，確保技能與指揮中心同步。

---
*Last Updated: 2026-04-11 | System Version: v8.6*
