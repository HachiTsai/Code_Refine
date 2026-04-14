# Spec: BLS 邏輯塊、因果矩陣與聯鎖防護解碼協定 (BLS Logic-Block & Interlock Rationale Protocol)

## 🔍 第一階段：知識溯源與語義勾稽 (Phase 1: Discovery & Hooking)
在啟動正式分析前，AI 必須執行以下檢索程序，確保具備正確的解碼依據與跨模組深度：

### 層級負一：全場域訊號追蹤 (Global Signal Trace) [MANDATORY]
* **指令**：提取 `source_data` 中出現的所有外部輸入位址（如 `INxxxx`, `DIxxxx`, `DHxxxx`, `DLxxxx`）。
* **動作**：必須對該廠區的 `core` 目錄執行全量搜尋，找出這些位址的「定義源頭」（即該位址作為 `output` 的位置）。
* **目的**：確保跨模組鏈結的絕對精確性，嚴禁憑經驗猜測訊號源。

### 層級零：系統法典檢索 (System Codecs)
* **指令**：AI **必須優先讀取** 以下系統級規範文件，作為解讀 BLS 邏輯腳本的唯一依據：
    1. **[[5_BLS|BLS 簡易演算系統規範]]**：定義 BLS 語法、函數（如 UNIT/RUNIT）、數據類型轉換與執行時序 (BLnnn)。

### 層級一：顯性邏輯血緣 (Explicit Logic Lineage)
* **指令**：掃描全域的Twin目錄, `core.json` 中所有的輸入變數。
* **動作**：對每一個輸入 ID (如 `DIxxxx`, `INxxxx`)，追蹤其來自哪個實體接點、SEQ 步序或 **[LPxxx]** 警報位。
* **目的**：確保理解聯鎖觸發的原始物理源頭。

### 層級二：語義標籤與物理勾稽 (Semantic Tags & Physical Context)
* **指令 1 [製程定位]**：從 `Statment` 提煉核心防護詞（如：`#乾轉保護`、`#超壓聯鎖`）。
* **指令 2 [事實提取]**：讀取筆記頂層 `%% DCS_FACTS %%` 內的 Dataview 屬性（`Summary::`, `Importance::`）。
* **指令 3 [標籤聯動]**：搜尋廠區內所有標註 `**[核心詞]**` 或帶有相同 `#標籤` 的其他聯鎖塊。
* **目的**：比對不同系統間的保護設定一致性。
* **訊號追溯**：(`Interlock::`)查詢**core.json**、**TWIN** 目錄 或**GID**

---

## 🎯 核心方針 (Directive)
BLS 是系統的安全底線與數學運算核心。解析過程必須採用**「三維度腳本解剖法 (Three-Dimensional Script Anatomy Method)」**。嚴禁孤立解析程式碼，必須將冷冰冰的 Statement 翻譯成工程上的物理意義，並揭露腳本如何定義「安全狀態」與「配方轉換」。

---

## 📋 第一部分：腳本語句全量閱覽清單 (Full Statement Inventory) - [MANDATORY ENUMERATION]
* **指令**: 必須逐一列出 `BLxxx.txt` 中 `Statement:` 區塊下的每一行邏輯。
* **[ZERO OMISSIONS] 絕對全量枚舉**: 嚴禁自行總結。每一行程式碼都必須出現在表中，並翻譯為人類可讀的工程意圖。
* **表格格式**:
    | 行號/標的 (Line/Target) | 原始程式碼 (Raw Code) | 工程身分與動作描述 (Role & Action) |
    | :-- | :-- | :-- |
    | (例) IF IN205==1 | `IF IN205==1` | **啟動閘門**: 判定是否進入 R601 參數注入程序。 |
    | (例) PIC601.P=... | `PIC601.P=R601DATA1.K2` | **配方映射**: 將 GMS 比例增益注入壓力迴路。 |
* **要求**: 讓讀者能像讀取 DDC BNO 一樣，清楚看清這支腳本的每一動。


---

## ⛓️ 第二部分：階梯式控制邏輯鏈 (Phased Logic Chain Analysis) [NEW]
將 BLS 腳本的離散語句拆解為具備物理防禦意義的連續階段，描述邏輯如何演進：
* **階段一：觸發矩陣與狀態感知 (Trigger Matrix & Condition Sensing)**: 識別哪些 Statement 負責監控輸入條件（如 `IF INxxxx == 1`），區分「啟動使能」與「終止/連鎖」條件。
* **階段二：邏輯仲裁與核心門鎖 (Logical Arbitration & Core Gating)**: 描述 Statement 如何將多個條件組合成指令（如 AND/OR 組合、優先級判斷），揭露控制策略的核心。
* **階段三：狀態記憶與連鎖鎖定 (State Memory & Interlock Latching)**: 識別是否存在 Flip-Flop（RS 觸發器）或 Latch 邏輯，分析是否具備故障自鎖與手動復歸 (Reset) 機制。
* **階段四：命令分發與最終執行 (Command Routing & Final Execution)**: 追蹤最終的賦值動作（如 `DOxxxx = 1` 或 `LPxxx.MODE = C`），定義該邏輯塊對全廠實體設備的最終影響力。

## 🧠 第三部分：智慧分析與工程意圖 (Intelligence Analysis & Rationale)
針對上述邏輯鏈，提供專家級的深度洞察：
* **物理模型解析**: 解釋數學函數（如 `UNIT`, `LOG`, `INDEX`）背後的物理特性補正。
* **工程深度提問 (Why...?)**: 透過專業術語（如 Fail-Safe, Latching Logic, Interlock Override）解釋設計背後的安全意圖。
* **維護指引**: 根據邏輯複雜度提供線上修改或旁路 (Bypass) 的風險評估。

---

## 🔄 第四部分：跨模組全域上下游數據流邏輯鏈結解析 (Cross-Module Linkage)
1. **控制源頭**: 這些邏輯是由哪個 **[LPxxx]** 或 **[USxxx]** 觸發的？
2. **影響範圍**: 該聯鎖最終切斷了哪個實體設備（閥門、幫浦）？
3. **全廠地位**: 該邏輯塊屬於哪一層級（設備層聯鎖 vs 廠區級 ESD）。
4. **上下游關聯**: 是否存在其他 BLS/SEQ/DDC 邏輯塊與之形成聯鎖鏈（如 A 觸發 B，B 觸發 C）？該鏈條的安全意圖是什麼？

---

## 🚦 輸出約束 (Constraints)
1. **[冷凝精華] 500字摘要原則**:
    * 在深度解析完成後，必須產出**絕對不超過 500 字**的精煉摘要(Summary)放在**`Summary::`** 標籤內容中。並更新 `Process::` 與 `Interlock::`等**所有的dataview 標籤內容**。
    * 摘要內容必須涵蓋：該聯鎖的最終保護對象（設備/製程）、核心觸發邏輯及其在失效安全 (Fail-Safe) 上的貢獻。
2. **[多維度標籤] 自動填入建議**:
    * **`Process::`**: 根據解析結果，推薦核心製程/防護標籤（如 `#乾轉保護`）。
    *
    * **`Interlock::`**: 註明此邏輯切斷的所有實體設備標籤（如 `[P-101]`）。
3. **抗脫水原則**: 深度分析區塊嚴禁條列式帶過，必須寫出具有工程深度的因果推導段落。
4. **術語精確性**: 強制使用 Anti-Windup, Bumpless Transfer, Software Gearing, Zero Drift, Chattering, Fan-Out 等專業英文術語。
5. **Obsidian 知識庫語法 (Wiki-Links & Callouts)**:
    * 提到其他迴路 ID 時，**禁止使用雙向連結 [[...]]**。
    * **格式要求**: 使用 **`**[...]**`** 醒目格式 (例如：**[LP001]**)。
    * **目的**: 避免無效的死連結，保持文檔的專業性與純淨。
    * 善用 `> [!info]` 或 `> [!warning]` 等 Callout 區塊來標示重要的安全極限或警告。
6. **重點醒目標示 (Bold Brackets)**: 當提及特定的 Tag No (如 **[DI0546]**)、核心變數 (如 **[GS0349]**) 時，必須使用 `**[...]**`。
7. **版面結構化**: 在解釋邏輯鏈與數學模型時，必須使用清晰的多層次縮排與清單。
