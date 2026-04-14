import pytest
from pathlib import Path
import sys
import json

# 設定導入路徑
TEST_DIR = Path(__file__).resolve().parent
SKILL_ROOT = TEST_DIR.parent
sys.path.append(str(SKILL_ROOT))

from src.parsers.bls_parser import HitachiBLSParser

@pytest.fixture
def parser():
    schema_path = SKILL_ROOT / "references" / "bls_schema.json"
    return HitachiBLSParser(schema_path=schema_path)

def test_bls_parser_basic_structure(parser, tmp_path):
    """驗證基礎結構解析 (BLSNO, Comment, Action)"""
    content = """BLSNO.: BL001 
Action: Always
Comment: R101 DATA SET1
Statement:
IF IN305==1 
THEN PIC101.P=R101DATA1.K2;
========================================
"""
    file_path = tmp_path / "BL001.txt"
    file_path.write_text(content, encoding='utf-8')
    
    result = parser.parse(file_path)
    
    assert result['bls_no'] == "BL001"
    assert result['comment'] == "R101 DATA SET1"
    assert result['action'] == "Always"

def test_bls_parser_semantic_translation(parser, tmp_path):
    """驗證語意翻譯功能 (是否關聯了 Schema 中的中文說明)"""
    content = """BLSNO.: BL002
Statement:
WB000=CLR(4)
IN001=UNIT(AI001)
"""
    file_path = tmp_path / "BL002.txt"
    file_path.write_text(content, encoding='utf-8')
    
    result = parser.parse(file_path)
    
    clr_stmt = next(s for s in result['statements'] if "CLR" in s['raw'])
    assert "清除" in clr_stmt['translation']
    
    unit_stmt = next(s for s in result['statements'] if "UNIT" in s['raw'])
    assert "工業單位變換" in unit_stmt['translation']

def test_bls_parser_if_logic(parser, tmp_path):
    """驗證 IF/THEN 邏輯區塊的提取 (支援多行)"""
    content = """BLSNO.: BL003
Statement:
IF IN131==1 
THEN GOTO 40
ELSE RTN
"""
    file_path = tmp_path / "BL003.txt"
    file_path.write_text(content, encoding='utf-8')
    
    result = parser.parse(file_path)
    
    if_block = next(s for s in result['statements'] if s['type'] == 'IF_CONDITION')
    assert if_block['condition'] == "IN131==1"
    assert "GOTO 40" in if_block['then_actions']
    assert "RTN" in if_block['else_actions']