import pytest
from pathlib import Path
import sys
import json

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.models.ddc_model import DDCLoop

def test_ddc_loop_model_logic(tmp_path):
    """驗證 DDCLoop 模型能正確封裝端子連線並產出 Mermaid"""
    # 建立臨時的 FNO Catalog
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({
        "F02": {"meta": {"name_zh": "輸入處理"}},
        "F05": {"meta": {"name_zh": "PID"}},
        "F07": {"meta": {"name_zh": "輸出處理"}}
    }), encoding='utf-8')

    raw_data = {
        'loop_id': 'LP015',
        'blocks': [
            {
                'bno': 5, 'fno': 2, 'fnm': 'AINP',
                'terminals': {'TERM1': {'lno': 'AI0014', 'addr': '', 'is_external': True}}
            },
            {
                'bno': 25, 'fno': 5, 'fnm': 'CPID',
                'terminals': {'TERM1': {'lno': '', 'addr': '5', 'is_external': False}}
            },
            {
                'bno': 35, 'fno': 7, 'fnm': 'COUT',
                'terminals': {
                    'TERM1': {'lno': '', 'addr': '25', 'is_external': False},
                    'TERM4': {'lno': 'AO003', 'addr': '', 'is_external': True}
                }
            }
        ],
        'parameters': {
            'PV': [{'bno': 5, 'value': None, 'cv': 'V'}],
            'MV': [{'bno': 35, 'value': None, 'cv': 'V'}]
        }
    }
    
    loop = DDCLoop(raw_data, catalog_path=catalog_path)
    
    # 驗證 PV 來源追蹤
    pv_info = loop.get_pv_signal()
    assert pv_info['tag'] == 'AI0014'
    assert pv_info['fnm'] == 'AINP'
    
    # 驗證 MV 輸出追蹤
    mv_info = loop.get_mv_signal()
    assert mv_info['tag'] == 'AO003'
    
    # 驗證 Mermaid 語法產出
    mermaid = loop.to_mermaid()
    assert "B5 --> B25" in mermaid
    assert "B25 --> B35" in mermaid
    assert "subgraph LP015" in mermaid
