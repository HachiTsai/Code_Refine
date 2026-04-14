import sys
from pathlib import Path
import pytest

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.parsers.tag_parser import HitachiTagParser

def test_tag_parser_r301_filtering(tmp_path):
    # 建立測試檔案
    content = """TAG COMMENT	C
[TIC-101] R101 Temp Control
[PIC-200] N2 Pressure
[LIA-301] R-301 Level Indication
(RESERVE)
[TIC-301] R301 Jacket Temp
"""
    f = tmp_path / "test_tags.txt"
    f.write_text(content, encoding='utf-8')
    
    parser = HitachiTagParser()
    results = parser.parse_file(f, "ai")
    
    # 預期結果：只有 TIC-101, PIC-200, LIA-301, TIC-301 被選中 (HitachiTagParser 目前不依賴關鍵字篩選)
    # 而是依據有效性 (非空, 非 W/0/1)
    
    assert len(results) == 4
    
    tags = [r['tag'] for r in results]
    assert "TIC-101" in tags
    assert "LIA-301" in tags
    assert "TIC-301" in tags
