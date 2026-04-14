---
name: ex-n01a-engine
description: Hitachi EX-N01A DCS 逆向工程核心引擎，負責執行數據煉製管線 (P1-P3)。
metadata:
  version: v6.7
  governance: "[[../../conductor/tech-stack.md|系統標準指令集]]"
  standards: "[[references/spec-refinery-model.md|數據煉製模型規格書]]"
---

# Skill: EX-N01A Digital Twin (核心數位孿生引擎)

本技能為 Hitachi EX-N01A 數位孿生的實作核心，負責將原始 DCS 數據轉化為具備因果邏輯的核心資產。

---

## 📋 執行管線 (Execution Pipeline)

本引擎嚴格遵循 **[[references/spec-refinery-model.md|數據煉製模型 (v6.7)]]**。以下為具體操作指令：

### Phase 1: 一鍵全量提煉 (Orchestration)

將指定單元的 Raw Data 轉化為 GID 數據骨架（包含計時器解析）。

- **指令**: `python .gemini/skills/ex-n01a-engine/scripts/unit_refinery.py --unit <UNIT>`
- **核心修復**: 已解決 v6.5 中 `unit_refinery` 對 `index_builder` 的匯入依賴報錯。

### Phase 2: 語義織入 (Semantic Enrichment)

將 GID 提升為具備單元身份與上下游語義的 Core JSON。

- **指令**: `python .gemini/skills/ex-n01a-engine/src/semantic_injector.py --unit <UNIT>`

### Phase 3: 索引與追蹤重建 (Delivery & Indexing)

產出相對路徑索引並更新全廠訊號追蹤地圖。

- **指令**: `python .gemini/skills/ex-n01a-engine/scripts/index_builder.py --plant <UNIT>`

---

## 🛠️ 原子工具指南 (Core Toolset)

### 3.1 數據解析器 (Parsers)

當需要單獨執行特定模組解析時使用：

- `tag_parser.py`: 提取位號定義。
- `seq_tm_parser.py`: **[新]** 提取計時器與計數器語義。
- `ddc_parser.py`, `seq_parser.py`, `bls_parser.py`: 提取核心邏輯。
- `extract_single.py`: 統一抽取引擎 (支援 DDC, SEQ, BLS 單檔快速萃取)。

### 3.2 系統維護工具

- **PathResolver**: 跨層級路徑導航，支援 `unit_suffix` 動態查詢。
- **SemanticInjector**: 執行 GID -> Core 的智慧提升。
- **CausalGraphBuilder**: 構建全廠因果圖譜 (SEQ -> DDC/BLS -> ALM)。
- **SemanticPropagator**: 執行知識自動「倒灌」與語義繼承。

---

## 🛡️ 操作規範 (Protocols)

1. **單元語義對齊**: 所有執行必須攜帶 `--unit` 參數，嚴禁跨單元污染。
2. **SSOT 鎖定**: 所有解析行為必須參考 `references/` 下的 FNO Catalog 與 Schemas。
3. **原子寫入**: 解析器繼承 `BaseParser` 以確保 `tmp` 驗證與編碼守護機制。

---

## 5. 版本紀錄 (Changelog)

- **v6.8 (2026-04-12)**:
  - **FEATURE**: 正式將 `extract_single.py` 收編為統一抽取引擎，支援 DDC/SEQ/BLS 單檔跨環境除錯。
- **v6.7 (2026-03-28)**:
  - **SYNC**: 同步文檔雜湊以修復 Mode B 漂移。
- **v6.7 (2026-03-26)**:
  - **FIX**: 修復 SEQ 引擎中 Shift 與 Correction 邏輯渲染錯誤，確保 `logic` 子物件正確解析。
  - **FEAT**: 優化 Markdown 渲染可讀性，合併相同邏輯的步序欄位。
- **v6.6 (2026-03-24)**:
  - **ARCH**: 執行微創對齊 (Alignment)，統一全引擎腳本的 `__version__` 為 `v6.6 (Engine Hardening)`。
  - **FEATURE**: 正式於 `utils.py` 等核心腳本套用 `RefineryContract` 進行邏輯自檢防呆。
- **v6.5 (2026-03-24)**:
  - **TEST**: 完成 Mode B 誠信偵測測試，文件與邏輯同步。
- **v6.5 (2026-03-22)**:
  - **FIX**: 修復 `unit_refinery.py` 的匯入崩潰問題，實作 `run_indexing` Facade 介面。
  - **ARCH**: 統一對齊 Conductor v8.0 與解析器 v16.5 規範。
- **v6.3 (2026-03-16)**:
  - **FEATURE**: 正式引入 `scripts/unit_refinery.py` 調度器。
- **v15.2 (2026-03-13)**:
  - **FEATURE**: 實作全域語義傳播器與因果圖譜閉環。

*Last Updated: 2026-04-12 | System Version: v8.6*
