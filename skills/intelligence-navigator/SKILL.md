---
name: intelligence-navigator
description: 語義導航者與 RAG 專家。負責跨文檔語義搜尋、專家診斷報告、標籤分類治理 (Taxonomy) 與邏輯偏移偵測。
metadata:
  version: v5.0 (Graph VM & Context Enabled)
  governance: "[[../../conductor/tech-stack.md|系統標準指令集]]"
---

# 🧠 Intelligence Navigator (語義導航者)

## 📋 職責說明 (Mission)

本技能負責 DCS 知識庫的 **「靈魂與語義 (Intelligence & Semantics)」**。它支持跨廠區 (Context-Aware) 的語義檢索與高度動態解析。

### 📜 核心公式 (The Sovereign Formula)

$$ (\text{向量庫} + \text{全域 core.json}) \times \text{AGENT 智慧解析 (含 Graph VM)} = \text{專家報告} $$

- **觸發協定 (Trigger Protocol)**: 本技能是系統唯一授權處理 **`DCS QUERY:`** 指令的門戶。當接收到該前綴時，必須執行 `search` 並進行語義綜述。

### 🛡️ 執行準則 (Guidelines)
1. **數據挖掘 (Extraction)**：系統應自動從 ChromaDB (語義) 與 Core JSON (物理) 提取所有關聯鏈結。
2. **智慧倍增 (Analysis)**：AGENT 嚴禁直接轉發數據；必須對數據執行「由上而下」的邏輯合成，產出具備工程意圖的結論。
3. **戰略綜述 (Synthesis)**：報告應聚焦於「全場定位」、「上下游因果」與「設計意圖」。

## 🎯 核心職能 (Core Functions)

| 職能群組 | 核心職責 | 關鍵腳本 |
| :--- | :--- | :--- |
| **Intelligence Hub** | 負責向量化搜尋與跨文檔 RAG 邏輯綜述。 | `expert_consultant.py` |
| **Taxonomy Master** | 負責 `TAG_TAXONOMY.md` 的維護與自動標籤建議。 | `index_engine.py` |
| **Behavior Engine (Graph VM)** | 依據 `core.json` 動態重組 IEC 61131-3 拓撲，執行全擬真時域推演。 | `behavior_graph_engine.py` |
| **Risk Auditor** | 偵測全廠相似設備間的邏輯設計偏移。 | `logic_drift_detector.py` |

## 🛠️ 標準指令 (Command Registry)

本技能採用標準化入口架構 (v5.0 已廢除 `--action` 參數，改用子指令直接觸發)：

| 指令集 | 功能說明 | 類別 |
| :--- | :--- | :---: |
| `python .gemini/skills/intelligence-navigator/scripts/manager.py index` | 重建全域語義索引 (ChromaDB)。 | ⚙️ 維護 |
| `python .gemini/skills/intelligence-navigator/scripts/manager.py search --query "<query>"` | 執行語義搜尋。 | 🔍 檢索 |
| `python .gemini/skills/intelligence-navigator/scripts/manager.py simulate --loop "<loop_id>"` | **[DCS Simulate]** 執行圖節點動態控制行為模擬。 | 🧪 預測 |
| `python .gemini/skills/intelligence-navigator/scripts/manager.py consult --topic "<topic>"` | 執行 RAG 專家診斷。 | 🧪 診斷 |
| `python .gemini/skills/intelligence-navigator/scripts/manager.py drift --keyword "<keyword>"` | 執行跨設備邏輯偏移偵測。 | 🚨 風險 |

## 🏗️ 核心架構
- **Search Engine**: ChromaDB (Vector DB)
- **Simulation Engine**: **Hitachi Graph Simulator** (支援多源仲裁與開環/閉環動態推演)
- **Embedding Model**: `models/gemini-embedding-2-preview` (透過 Google SDK 批次處理)
- **Knowledge Base**: `20_Knowledge_Base/`
- **Taxonomy**: `10_Obsidian_System/90_Tags_Management/TAG_TAXONOMY.md`

## 🔗 聯動關係
- **Git Workflow**: 在提交前自動執行 `index` 子指令。
- **Daily Log**: 歸檔時自動推薦相關語義連結與模擬結果。

---
*Version: 5.0 (Graph VM Enabled) | Status: Active | Last Updated: 2026-04-11 | System Version: v8.6*