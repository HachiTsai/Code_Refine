import pytest
from pathlib import Path
import sys

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.parsers.ddc_parser import HitachiDDCParser

@pytest.fixture
def parser():
    return HitachiDDCParser()

def test_aswh_enable_signals(parser, tmp_path):
    """驗證 ASWH (FNO 13) 是否能正確提取 14-17 欄位的啟動訊號"""
    header = "BNO\tFNO\tFNM\tTERM1-LNO\tTERM1-RADDR\tTERM2-LNO\tTERM2-RADDR\tTERM3-LNO\tTERM3-RADDR\tTERM4-LNO\tTERM4-RADDR\tY\tX\tPARAM\tE1\tE2\tE3\tE4"
    # BNO 2: 有啟動訊號
    line2 = "2\t13\tASWH\tGS0256\t\tGS0257\t\tGS0258\t\tGS0259\t\t0\t0\t0.000\tIN0140\tIN0141\tIN0142\tIN0143"
    # BNO 22: 部分啟動訊號為 NOUSE 或空
    line22 = "22\t13\tASWH\t\t20\tGS0422\t\t\t\t\t\t5\t1\t0.000\tIX001\tIN0322\tNOUSE\tNOUSE"
    
    content = f"{header}\n{line2}\n{line22}\n\n<Parameter>\n"
    
    lp_path = tmp_path / "LP107.txt"
    lp_path.write_text(content, encoding='utf-8')
    
    result = parser.parse_loop(lp_path)
    
    # 驗證 BNO 2
    bno2 = next(b for b in result['blocks'] if b['bno'] == 2)
    assert bno2['terminals']['TERM1']['enable'] == "IN0140"
    assert bno2['terminals']['TERM2']['enable'] == "IN0141"
    assert bno2['terminals']['TERM3']['enable'] == "IN0142"
    assert bno2['terminals']['TERM4']['enable'] == "IN0143"
    
    # 驗證 BNO 22 (過濾 NOUSE)
    bno22 = next(b for b in result['blocks'] if b['bno'] == 22)
    assert bno22['terminals']['TERM1']['enable'] == "IX001"
    assert bno22['terminals']['TERM2']['enable'] == "IN0322"
    # TERM3 and TERM4 have no LNO/ADDR in mock data, so they shouldn't exist
    assert 'TERM3' not in bno22['terminals']
    assert 'TERM4' not in bno22['terminals']
