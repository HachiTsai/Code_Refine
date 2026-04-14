import sys
from pathlib import Path
import pytest

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.cleaners.base import BaseCleaner

@pytest.fixture
def cleaner():
    return BaseCleaner()

def test_clean_line_noise_removal(cleaner):
    # 測試移除空行與空白
    assert cleaner.clean_common_noise("   ") == ""
    
    # 測試移除轉碼殘留 (Hitachi 特有)
    assert cleaner.remove_encoding_noise("?gTIC101") == "TIC101"
    assert cleaner.remove_encoding_noise("?hTemperature Sensor") == "Temperature Sensor"
    
    # 測試移除預留標籤
    assert cleaner.is_reserve_line("(RESERVE)") is True


