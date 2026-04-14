#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移除 Excalidraw/Markdown 檔案中的 HTML <br> 標籤,替換為真正的換行符號

使用方式:
    python fix_br_tags.py <檔案路徑>

範例:
    python fix_br_tags.py "c:\\path\\to\\file.md"
"""

import re
import sys
import os
import shutil
import subprocess
from pathlib import Path

# ==============================================================================
# 🛡️ [v2.1] Excalidraw Toolkit & Type Shield
# ==============================================================================
__version__ = "v2.1 (Toolkit Hardening)"





def fix_br_tags(file_path):
    """替換檔案中的 <br> 和 <br/> 標籤為換行符號"""

    file_path = Path(file_path)

    # 檢查檔案是否存在
    if not file_path.exists():
        print(f"❌ 錯誤: 檔案不存在 - {file_path}")
        return False

    # 讀取檔案
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 錯誤: 無法讀取檔案 - {e}")
        return False

    # 計算替換前的數量
    matches = re.findall(r"<br\s*/?>", content)
    count = len(matches)

    if count == 0:
        print(f"✅ 檔案中沒有找到 <br> 標籤")
        return True

    print(f"🔍 找到 {count} 個 <br> 標籤")

    # 替換所有 <br> 和 <br/> 標籤為換行符號
    new_content = re.sub(r"<br\s*/?>", "\n", content)

    # 寫回檔案
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ 替換完成!已將 {count} 個 <br> 標籤替換為換行符號")
        print(f"📄 處理檔案: {file_path.name}")
        # Trigger handshake
        return True
    except Exception as e:
        print(f"❌ 錯誤: 無法寫入檔案 - {e}")
        return False


def main():
    """主程式入口"""

    # 檢查命令列參數
    if len(sys.argv) < 2:
        print(f"\n{'='*60}")
        print(f"🔧 移除 HTML <br> 標籤工具")
        print(f"{'='*60}\n")
        print(f"❌ 錯誤: 未指定檔案路徑")
        print(f"使用方式: python fix_br_tags.py <檔案路徑>")
        return 1
    
    file_path = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"🔧 移除 HTML <br> 標籤工具")
    print(f"{'='*60}\n")

    success = fix_br_tags(file_path)

    print(f"\n{'='*60}")
    if success:
        print(f"✅ 處理完成")
    else:
        print(f"❌ 處理失敗")
    print(f"{'='*60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
