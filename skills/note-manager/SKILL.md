---
name: note-manager
description: 高品質筆記總管與知識產出引擎。負責 DCS 數位孿生資產 (P3) 的規格化生成、注入與反向同步。
metadata:
  version: v17.6
  governance: "[[../../conductor/tech-stack.md|系統標準指令集]]"
---

# Skill: Note Manager (筆記總管)

## 📋 核心指令集 (Master Commands v16.7)

👉 **SSOT 指令集: [[conductor/tech-stack#5.2 系統治理 (System Governance)|系統標準指令集]]**

| 類別 | 任務說明 | 標準指令 (CLI) |
| :--- | :--- | :--- |
| **自檢** | 執行全量邏輯契約自檢 (V2) | `python .gemini/skills/note-manager/scripts/manager.py --self-check` |
| **煉金** | **[V3 高效入口]** 一鍵物理還原與全域收割 | `python .gemini/skills/note-manager/scripts/manager.py --action auto-refine --loop <LOOP>` |
| **同步** | **[V3 終點]** 將 Markdown 智慧反向同步至 Core JSON | `python .gemini/skills/note-manager/scripts/manager.py --action sync-back --loop <LOOP>` |
| **骨架** | 手動觸發引擎建立標竿骨架 | `python .gemini/skills/note-manager/scripts/manager.py --action create-skeleton --loop <LOOP>` |
| **更新** | 僅更新 Summary 與 Facts 標籤 | `python .gemini/skills/note-manager/scripts/manager.py --action update-summary --loop <LOOP> --summary <TEXT>` |

---

## 🔄 V3: DCS 數位孿生資產煉製 SOP (Standardized Pipeline)

本技能採用「最強引擎調度」與「零暫存檔」工作流，必須嚴格遵守以下三階段：

1. **第一階段：全自動收割 (Auto-Refine)**
    - **動作**：執行 `--action auto-refine`。
    - **目標**：自動偵測位號類型 (DDC/SEQ/BLS)，啟動最強引擎產出「物理骨架」，並繪製「全域引用地圖 (Global Reference Map)」。
    - **新功能 (v16.5)**：支援 **[路徑自癒]** 與 **[Sxx 命名預判]**，自動定位正確的單元路徑。
2. **第二階段：智慧織入 (Direct Injection)**
    - **動作**：Agent 利用 `replace` 工具直接在 Markdown 檔案中作業。
    - **原則**：必須遵循 `spec-analyze-*.md` (DDC 升級為 **v14.0 階梯分析**) 規範，重點標註 **「戰略地位 (Strategic Positioning)」** 與 **「聯鎖血緣」**。
3. **第三階段：反向同步 (Back-Sync)**
    - **動作**：執行 `--action sync-back`。
    - **目標**：從 Markdown 提取最新智慧結論，自動回寫至數位孿生 Core JSON，達成 SSOT 閉環。

---

## 🏗️ 系統架構 (Architecture)

- **`src/core_resolver.py`**: 數據中樞 (v16.5: 支援路徑自癒與 Sxx 命名慣例預判)。
- **`src/ddc_engine.py`**: DDC 專屬引擎 (v14.0: 支援階梯式邏輯鏈 Phase 1-4 與全量 BNO 表格)。
- **`src/bls_engine.py`**: BLS 專屬引擎 (v1.0: 支援語法解析與階梯分析)。
- **`src/seq_engine.py`**: SEQ 專屬引擎 (v1.9: 支持複雜步序矩陣還原與邏輯表格渲染優化)。
- **`src/knowledge_injector.py`**: 知識織入器 (v16.0: 支援錨點注入與反向同步)。

---

## 🛡️ 原子化鐵律 (Atomic Operation Protocol)

1. **原子化修改**：嚴禁暴力覆寫，所有變更必須精確導向。
2. **原子化注入**：織入內容必須位於 `## 🧭 深度邏輯解析` 標題與物理表格之間，不得破壞數據結構。
3. **戰略優先**：解析品質不接受單純的功能描述，必須揭露「指揮官」、「終 端」與「安全基準」地位。

---

## 5. 版本紀錄 (Changelog)

- **v16.7 (2026-03-28)**:
    - **SYNC**: 同步文檔雜湊以修復 Mode B 漂移。
- **v16.7 (2026-03-26)**:
    - **SEQ**: 修復 `seq_engine.py` 中 `Correction` 區塊邏輯解析錯誤，優化 Markdown 表格渲染品質。
    - **ARCH**: 統一對齊 `ex-n01a-engine` v6.7 標準。
- **v16.6 (2026-03-24)**:
    - **CLEANUP**: 徹底移除過時的 `handshake` 技能快取同步機制。
    - **ARCH**: 統一全引擎腳本版本號為 `v16.6` 並實施標準化標頭治理。
- **v16.5 (2026-03-22)**:
    - **RESOLVER**: 實作路徑自癒與 Sxx -> MLCxx 命名慣例預判邏輯。
    - **DDC**: 升級 DDC 引擎至 v14.0，全面導入「階梯式邏輯鏈 (Phase 1-4)」分析協定。
- **v16.0 (2026-03-21)**:
    - **ARCH**: 實作 V3「直接織入與反向同步」管線，廢除暫存檔模式。
    - **FEATURE**: 實作 DDC 與 BLS 專屬引擎，支援 BNO 全量枚舉。
    - **FEATURE**: Resolver 升級全域引用偵測與物理探針邏輯。
    - **GOV**: 正式固化「原子化鐵律」與「戰略地位解析」標準。
- **v15.11 (2026-03-13)**: 實作智慧煉金管線初稿。

---
*Last Updated: 2026-04-11 | System Version: v8.6*
