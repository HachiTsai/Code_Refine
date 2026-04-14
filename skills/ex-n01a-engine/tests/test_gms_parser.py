import pytest
from pathlib import Path
import sys
import json

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.parsers.gms_parser import HitachiGMSParser

@pytest.fixture
def parser():
    return HitachiGMSParser()

def test_gms_parser_300_limit(parser, tmp_path):
    """驗證 HitachiGMSParser 遵循 300 筆有效數據限制"""
    # 模擬 1000 行資料
    destin_lines = ["HEADER_D"] + [f"{i}\tADDR_{i}" for i in range(1, 501)]
    dtattr_lines = ["HEADER_A"] + [f"RECIPE_{i}" for i in range(1, 501)]
    
    destin_path = tmp_path / "destin1.txt"
    dtattr_path = tmp_path / "dtattr1.txt"
    
    destin_path.write_text("\n".join(destin_lines))
    dtattr_path.write_text("\n".join(dtattr_lines))
    
    results = parser.parse_set(destin_path, dtattr_path, set_id=1)
    
    # 應僅提取前 300 筆
    assert len(results) == 300
    assert results[0]["recipe_name"] == "RECIPE_1"
    assert results[299]["recipe_name"] == "RECIPE_300"

def test_gms_parser_star_g_detection(parser, tmp_path):
    """驗證 *G 標籤的動態定位功能"""
    # 在 500 行處插入 *G2
    destin_lines = ["*G1", "HEADER_D", "1\t1001"] + [""]*497 + ["*G2", "HEADER_D", "1\t2001"]
    dtattr_lines = ["*G1", "HEADER_A", "REC_1"] + [""]*497 + ["*G2", "HEADER_A", "REC_2"]
    
    destin_path = tmp_path / "destin1.txt"
    dtattr_path = tmp_path / "dtattr1.txt"
    
    destin_path.write_text("\n".join(destin_lines))
    dtattr_path.write_text("\n".join(dtattr_lines))
    
    results = parser.parse_set(destin_path, dtattr_path, set_id=1)
    
    # 遇到下一個 *G 應該停止
    assert len(results) == 1
    assert results[0]["address"] == "1001"

def test_gms_parser_invalid_data_filter(parser, tmp_path):
    """驗證無效數據 (W, 0, 空白) 的過濾"""
    destin_lines = ["HEADER", "1\t1001", "2\t0", "3\t2001"]
    dtattr_lines = ["HEADER", "REC_1", "W", "0"]
    
    destin_path = tmp_path / "destin1.txt"
    dtattr_path = tmp_path / "dtattr1.txt"
    
    destin_path.write_text("\n".join(destin_lines))
    dtattr_path.write_text("\n".join(dtattr_lines))
    
    results = parser.parse_set(destin_path, dtattr_path, set_id=1)
    
    # 只有第一筆有效 (REC_1)
    # 第二筆為 "W"，第三筆為 "0" (根據 HitachiGMSParser 邏輯應過濾)
    assert len(results) == 1
    assert results[0]["recipe_name"] == "REC_1"

def test_gms_save_baseline(parser, tmp_path):
    """驗證 Baseline JSON 的格式正確性"""
    data = [
        {"set_id": 1, "recipe_name": "TEST_REC", "data_no": "5", "address": "1234"}
    ]
    output_path = tmp_path / "baseline.json"
    parser.save_baseline_json(data, output_path)
    
    assert output_path.exists()
    content = json.loads(output_path.read_text(encoding='utf-8'))
    
    key = "GMS_S01_N005"
    assert key in content
    assert content[key]["recipe_name"] == "TEST_REC"
