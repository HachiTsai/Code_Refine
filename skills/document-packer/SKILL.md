---
name: document-packer
description: 整合多個 Markdown/TXT/CSV 檔案為單一結構化報告，支援遞歸搜尋、元數據解析與 DCS 全方位打包。
metadata:
  version: v2.1
  governance: "[[../../conductor/tech-stack.md|系統標準指令集]]"
---

# 文件打包專家 (Document Packing Skill)

## 📋 觸發指令

使用以下任一關鍵字啟動此 Skill：

- `打包 [目錄路徑]`：一般打包（通用模式）。
- `請打包RAW,GID,TWIN --site [SITE] --plant [PLANT]`：**[全方位資產打包]** 執行標準化 DCS 打包流程。
- `整合檔案 [目錄路徑]`
- `產生打包報告`
- `pack [path]`

---

## 🎯 適用範圍

此 Skill 適用於需要快速彙整大量分散文檔的場景：

| 場景類型 | 適用性 | 說明 |
| :--- | :---: | :--- |
| **研究資料彙整** | ⭐⭐⭐⭐⭐ | 將多個 .md 研究心得整合成一份大報告 |
| **單元資產交付** | ⭐⭐⭐⭐⭐ | 透過 `DCS 模式` 一次性導出 RAW/GID/TWIN 完整資產 |
| **系統配置備份** | ⭐⭐⭐⭐ | 打包特定目錄下的所有 .txt 或 .csv 配置 |
| **全廠位號診斷** | ⭐⭐⭐⭐⭐ | 整合多個單元的 TAG 資料夾進行全域檢索 |

---

## 🔄 執行流程

```mermaid
graph TD
    A[啟動 packer.py] --> B{檢查參數}
    B -->|指定 site/plant| C[DCS 模式]
    B -->|指定路徑| D[通用模式]
    C -->|Step 1| E[Pack Filtered RAW]
    C -->|Step 2| F[Pack GID]
    C -->|Step 3| G[Pack TWIN (Core+Index)]
    D --> H[按指定路徑執行掃描]
    E & F & G & H --> I[自動建立 80_packed_report 並寫入]
    I --> J[執行 Handshake 同步快取]
```

---

## 📝 詳細步驟

### 步驟 1: 分析請求

- **通用模式**：識別來源 `<目錄路徑>` 或多個檔案路徑。
- **DCS 模式**：識別 `--site/--plant` 參數，自動定位數位孿生資產路徑。

### 步驟 2: 執行工具

統一使用整合後的 `packer.py`：

```bash
# 通用模式 (多路徑打包)
python .gemini/skills/document-packer/scripts/packer.py "path/to/dir1" "path/to/dir2" -r

# DCS 模式 (全方位打包)
python .gemini/skills/document-packer/scripts/packer.py --site Johor --plant MLC02
```

- `-r`: 啟用遞歸搜尋（Recursive）。
- `--filter-zeros`: 移除無效零行（RAW 數據專用）。
- `--handshake`: 成功後通知系統更新狀態。

### 步驟 3: 定位輸出

- 腳本會自動將報告儲存至：`00_Inbox/80_packed_report/`。
- **智慧命名**：
    - 多路徑 TAG 打包：`0_packed_GLOBAL_TAGS_[DATE].txt`
    - 單一單元打包：`packed_[PLANT]_[TYPE]_[DATE].txt`

---

## 🚫 禁止事項

1. **禁止直接刪除來源檔案**：打包僅為讀取與整合，不得移動或刪除原始文件。
2. **禁止處理非文字檔案**：僅支援 `.md`, `.txt`, `.csv`, `.json` 格式。
3. **禁止在報告中洩露敏感憑證**：若路徑包含 `credentials/`，必須發出警告。

---

## 📝 版本歷史

- **v2.1** (2026-03-28):
    - **SYNC**: 同步文檔雜湊以修復 Mode B 漂移。
- **v2.0** (2026-03-18):
    - **MAJOR**: 整合 `bundle_packer.py` 與 `convert_md_to_txt.py` 為單一 `packer.py`。
    - **ENHANCEMENT**: 支援 Python 類型收窄 (Type Narrowing)，修復 Pyright 報錯。
    - **UX**: 實作智慧路徑自動建立與多目錄打包命名規範。
- **v1.3** (2026-03-09): 新增 `bundle_packer.py` 支援三層級資產打包。
- **v1.2** (2026-02-16): 實作動態握手機制。
- **v1.0** (2026-01-22): 初始功能發布。

---
*Last Updated: 2026-04-11 | System Version: v8.6*
