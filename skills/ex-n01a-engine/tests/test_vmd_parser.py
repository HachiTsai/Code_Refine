import sys
from pathlib import Path
import pytest

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.parsers.vmd_parser import HitachiVMDParser

def test_vmd_vm_status_mapping(tmp_path):
    # 建立測試資料 (Tab separated)
    # Header: No, TAGNO, SERVICE, C, TYPE, OUT1, OUT2, ANS1, ANS2, TRIP
    content = "No\tTAGNO\tSERVICE\tC\tTYPE\tOUT1\tOUT2\tANS1\tANS2\tTRIP\n"
    content += "57\tV101\tPump Control\t0\tVM\t101\t102\t201\t202\t10\n"
    
    f = tmp_path / "vmd_vm.txt"
    f.write_text(content, encoding='utf-8')
    
    parser = HitachiVMDParser()
    results = parser.parse_vm(f)
    
    assert len(results) == 1
    vm = results[0]
    assert vm["No"] == "57"
    assert "status_signals" in vm
    assert vm["status_signals"]["VS"] == "VS0057"
    assert vm["status_signals"]["VD"] == "VD0057"
    assert vm["status_signals"]["VI"] == "VI0057"
    assert vm["status_signals"]["VR"] == "VR0057"
    assert vm["status_signals"]["VE"] == "VE0057"

def test_vmd_vm_invalid_filtering(tmp_path):
    # 測試無效資料過濾
    content = "No\tTAGNO\tSERVICE\tC\tTYPE\tOUT1\tOUT2\tANS1\tANS2\tTRIP\n"
    content += "58\tV102\tInvalid VM\t0\tVM\tW\t0\t1\t \t10\n"
    
    f = tmp_path / "vmd_vm_invalid.txt"
    f.write_text(content, encoding='utf-8')
    
    parser = HitachiVMDParser()
    results = parser.parse_vm(f)
    
    # 預期結果：因為 OUT1~ANS2 都是無效值 (W, 0, 1, 空格)，該項目應被過濾
    assert len(results) == 0
