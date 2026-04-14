import sys
from pathlib import Path
import json
import pytest

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.parsers.seq_tm_parser import SEQTimerParser

def test_parsing():
    # 修正 mock 檔案路徑
    mock_file = TEST_DIR / "mock_data/seq/seq_tm_mock.txt"
    parser = SEQTimerParser()
    results = parser.parse(str(mock_file))
    
    print(f"Parsed {len(results)} valid timers.")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Expected: 2 timers (No 1 and No 6)
    assert len(results) == 2
    assert results[0]["TIMER_ID"] == "TD001"
    assert results[1]["TIMER_ID"] == "TD006"
    print("Test Passed!")

if __name__ == "__main__":
    test_parsing()
