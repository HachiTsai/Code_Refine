import pytest
from pathlib import Path
import sys
import json

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
PROJECT_ROOT = SKILL_ROOT.parents[2]

sys.path.append(str(SKILL_ROOT))

from src.refinery.causal_graph_builder import CausalGraphBuilder

@pytest.fixture
def builder():
    return CausalGraphBuilder(PROJECT_ROOT)

def test_causal_chain_seq_to_ddc_to_gms(builder, tmp_path):
    """驗證因果鏈條：SEQ -> IN0140 -> LP107 ASWH -> GS0256 -> GMS Recipe"""
    
    # 1. 模擬 SEQ 數據 (包含控制開關)
    seq_data = {
        "unit_no": "2",
        "control_switches": ["IN0140", "IN0141"]
    }
    
    # 2. 模擬 DDC 數據 (LP107 的 BNO 18)
    lp_data = {
        "loop_id": "LP107",
        "blocks": [
            {
                "bno": 18, "fnm": "ASWH",
                "terminals": {
                    "TERM5": {"lno": "IN0140", "addr": "", "is_external": True}, # SL1
                    "TERM1": {"lno": "GS0256", "addr": "", "is_external": True}  # X1
                }
            }
        ]
    }
    
    # 3. 模擬 GMS 註冊表 (GS0256 對應 TICSV1)
    # 為了測試，我們手動注入 mock 註冊表
    builder.gms_registry = {
        "GS0256": {"recipe_name": "TICSV1", "address": "LP105PLS01"}
    }
    
    # 執行建構
    graph = builder.build_loop_impact_graph("R301", lp_data, seq_data)
    
    # 驗證結果
    assert len(graph["causal_links"]) > 0
    link = graph["causal_links"][0]
    assert link["from_seq_switch"] == "IN0140"
    assert link["to_ddc_block"] == "18 (ASWH)"
    assert "GS0256" in link["referenced_gs"]
    assert link["gms_recipes"][0]["recipe_name"] == "TICSV1"
