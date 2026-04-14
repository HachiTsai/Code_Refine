# Refinery Model Specification (數據煉製模型規格)

## 1. 核心理念

本專案採用「三階段煉製管線 (Three-Stage Refinery Pipeline)」，旨在將工業控制系統 (DCS) 的原始文本轉化為高價值的知識圖譜與數位孿生資產。所有資產必須遵循 `<Client>/<Site>/<Plant>` 的多廠區鏡像結構。

---

## 2. 煉製階段定義與技能分工

### 階段 1：原始提取 (Extraction)
* **職責歸屬**: `ex-n01a-engine`
* **路徑映射**: `_assets/00_Raw/...` -> `_assets/05_GID/...`
* **核心目標**: 將 DCS 原始文字檔案 (SEQ, DDC, BLS, SEQ_TM) 轉化為純淨、結構化的 JSON 數據。
* **工具規範**:
    * `unit_refinery.py`: 統一調度全量提取。
    * 解析器必須繼承 `parsers.base.BaseParser`。
* **關鍵組件**: `seq_tm_parser.py` 必須先於其他邏輯解析執行，以確立時基語義。
* **輸出格式**: `*_refined.json` (數據骨架)。
* **不變量 (Invariant)**: 嚴禁在此階段添加人工解釋，僅執行語法轉譯。

### 階段 2：智慧提煉與語義織入 (Enrichment & Propagation)
* **職責歸屬**: `ex-n01a-engine`
* **路徑映射**: `_assets/05_GID/...` -> `_assets/30_Digital_Twin/core/...`
* **核心目標**: 注入領域知識、建立全廠因果網路，並自動傳遞語義。
* **工具規範**:
    * `semantic_injector.py`: 注入單元身份與基礎元數據。
    * `causal_builder.py`: 建立跨模組因果圖譜 (SEQ -> DDC/BLS -> ALM)。
    * `semantic_propagator.py`: 根據因果圖譜，將上游邏輯的專家知識 (Expert Insight) 自動倒灌至下游節點。
* **產出**: `*_core.json` (具備大腦與記憶的數位孿生實體)。

### 階段 3：知識交付與索引 (Delivery & Indexing)
* **職責歸屬**: `note-manager` (交付) & `ex-n01a-engine` (索引)
* **路徑映射**: `_assets/30_Digital_Twin/core/...` -> `20_Knowledge_Base/...` (與 Search Index)
* **核心目標**:
    1. 將數位孿生數據轉換為人類可讀、AI 可檢索的 Markdown/Mermaid 資產 (`note-manager`)。
    2. 重建全廠訊號追蹤地圖 (`IndexBuilder`)。
* **工具規範**: 透過 `note-manager` 的 Orchestrator 進行 `deep-analyze` 與 `update-summary` 雙向同步。

---

## 3. 系統交互與守護

* **動態握手 (Handshake)**: 每個煉製階段結束，必須主動呼叫總機更新技能快取，確保 SSoT 同步。
* **語義歸一化 (Normalization)**: 強制使用 `PathResolver` 進行跨層級導航，並於存取 `core.json` 前自動剝離站號後綴 (如 S01/S02)。
* **防呆機制**: 任何對 Core JSON 的寫入必須支援增量更新，避免覆蓋已注入的專家知識。

---
*Last Updated: 2026-03-16 | Architecture v6.9 (Aligned with unit-refinery v1.1) | SSOT Authority: Conductor*
