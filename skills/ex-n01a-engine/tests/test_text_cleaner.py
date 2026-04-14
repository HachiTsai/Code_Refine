import sys
from pathlib import Path
import pytest

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.cleaners.text_cleaner import TextCleaner

def test_clean_line():
    cleaner = TextCleaner()
    
    # Test encoding noise removal
    assert cleaner.clean_line("?gTIC101") == "TIC101"
    
    # Test whitespace
    assert cleaner.clean_line("  Test  ") == "Test"
    
    # Test reserve
    assert cleaner.clean_line("(RESERVE)") == ""
    
    # Test internal spacing
    assert cleaner.clean_line("A   B") == "A B"