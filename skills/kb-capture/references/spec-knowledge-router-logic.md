---
tags:
- specification
- architecture
- workflow
id: KB-SPEC-20260317
---
Summary:: 定義系統級的「知識分發與萃取管線」規範 (v1.1)，確立 00_sys-notes 為系統核心知識存放區。
Importance:: [關鍵角色] 確保系統級技術資產與 DCS 業務資產路徑隔離，提升知識庫治理效率。

# 📚 知識分發管線規格書 (Knowledge Router Specification)

## 1. 核心哲學 (Philosophy)
本規範旨在解決「知識流失」問題。透過**意圖感知 (Intent-Aware)** 與 **骨架自體化 (Self-Skeletonizing)** 機制，將「開發流水帳」轉化為「結構化技術資產」。

## 2. 系統架構 (Architecture)

### 2.1 數據流向
`AskGemini.md (Inbox)` ➔ `Daily Log Skill (Router)` ➔ `Target Directory` ➔ `Dataview Dashboard`

### 2.2 去耦合儲存規範
* **日誌 (Log)**：預設作為 `knowhow` 收割至 `00_sys-notes/`，保留執行脈絡與設定規範。
* **資產 (Asset)**：具備再利用價值的領域知識（Idea, KnowHow, Spec）存於 `20_Knowledge_Base/0_Worklogs/<type>/`。
* **系統核心 (System Core)**：系統架構、SOP 或非 DCS 關鍵技術筆記，強制存放於 `conductor/archive/00_sys-notes/`。

## 3. 設定檔驅動機制 (Config-Driven)

系統行為由 `.gemini/skills/daily-log-workflow/assets/knowledge_types.json` 唯一定義。

## 4. 鏈式聯鎖規範 (Chained Handshake v4.8)

1. **捕捉 (Capture)**：`daily-log-workflow` 建立 Markdown 檔案。
2. **骨架 (Skeleton)**：由 `skeleton.py` 自動注入 YAML 與 Dataview 欄位。
3. **聚合 (Aggregate)**：`Daily_WorkLog_Master.md` 透過 Dataview 自動呈現。

## 5. 命名與目錄標準
* **檔名格式**：`<type>-YYMMDD-<topic>.md` (時間前置以優化排序)
* **儲存路徑**：
    * 一般資產: `20_Knowledge_Base/0_Worklogs/<type>/` (註：`spec` 類型存於 `specs/`)
    * 系統資產: `conductor/archive/00_sys-notes/`

---
*Last Updated: 2026-03-17 | Version: v1.1*
