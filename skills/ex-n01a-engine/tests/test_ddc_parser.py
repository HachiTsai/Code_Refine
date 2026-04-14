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

def test_ddc_parser_loop_logic(parser, tmp_path):
    """驗證 DDC 解析器能提取端子連線與參數映射"""
    # 模擬精確的 LP015.txt 內容 (使用 TAB 分隔)
    # BNO(0) FNO(1) FNM(2) T1L(3) T1A(4) T2L(5) T2A(6) T3L(7) T3A(8) T4L(9) T4A(10)
    header = "BNO\tFNO\tFNM\tTERM1-LNO\tTERM1-RADDR\tTERM2-LNO\tTERM2-RADDR\tTERM3-LNO\tTERM3-RADDR\tTERM4-LNO\tTERM4-RADDR\tY\tX\tPARAM"
    line1 = "1\t1\tESTS\tIN0013\t\t\t\t\t\t\t\t2\t0" # T1L=IN0013 (External)
    line3 = "3\t27\tARTA\t\tIN0001\t\tIN0131\t\t\t\t\t2\t1" # T1A=IN0001 (Internal), T2A=IN0131
    line5 = "5\t2\tAINP\tAI0014\t\t35\t\t\t\t\t\t0\t0" # T1L=AI0014, T2L=35
    
    content = f"{header}\n{line1}\n{line3}\n{line5}\n\n<Parameter>\nTYPE\tBNO\tC/V\tPARA\tDATA\nSV\t3\tC\t1\t50.0\n"
    
    lp_path = tmp_path / "LP015.txt"
    lp_path.write_text(content, encoding='utf-8')
    
    result = parser.parse_loop(lp_path)
    
    # 驗證 BNO 1 的外部連線
    bno1 = next(b for b in result['blocks'] if b['bno'] == 1)
    assert bno1['terminals']['TERM1']['lno'] == "IN0013"
    
    # 驗證 BNO 3 的內部連線 (TERM1-RADDR)
    bno3 = next(b for b in result['blocks'] if b['bno'] == 3)
    assert bno3['terminals']['TERM1']['addr'] == "IN0001"
    assert bno3['terminals']['TERM1']['is_external'] is False
    assert bno3['terminals']['TERM2']['addr'] == "IN0131"

def test_ddc_parser_index(parser, tmp_path):
    """驗證 ddcinst.txt 索引解析"""
    content = """"NO"	"TAG"	"SERVICE"
"1"	"LP001"	"REACT FEED"
"2"	"LP002"	"REACT TEMP"
"""
    inst_path = tmp_path / "ddcinst.txt"
    inst_path.write_text(content, encoding='utf-8')
    
    loops = parser.parse_index(inst_path)
    assert len(loops) == 2
    assert loops[0]['tag'] == "LP001"
