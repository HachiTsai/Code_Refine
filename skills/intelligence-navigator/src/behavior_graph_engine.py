"""
🧠 Intelligence Navigator: Behavior Graph Engine (v1.0)
============================================================
職責：讀取 SSoT core.json，動態實例化 FNO 區塊，並執行基於 BNO 的掃描循環。
架構：IEC 61131-3 虛擬機 (Graph VM)
變更：雙軌並行階段，用於取代舊有的 HitachiDDCSimulator。
"""

import logging
from behavior_blocks import (
    BaseBlock, DummyBlock,
    Block_F13_ASWH, Block_F08_AHLA, Block_F02_AINP,
    Block_F07_COUT, Block_F14_APRO, Block_F04_CDEV,
    Block_F12_ACON, Block_F01_ESTS, Block_F00_ALGC
)

class HitachiGraphSimulator:
    """日立 DDC 圖形節點虛擬機 (Graph VM)"""
    
    # FNO 到 Block 類別的映射工廠
    BLOCK_FACTORY = {
        13: Block_F13_ASWH,
        8: Block_F08_AHLA,
        2: Block_F02_AINP,
        7: Block_F07_COUT,
        14: Block_F14_APRO,
        4: Block_F04_CDEV,
        12: Block_F12_ACON,
        1: Block_F01_ESTS,
        0: Block_F00_ALGC
    }

    def __init__(self, core_json_data: dict, dt: float = 1.0):
        self.dt = dt
        self.blocks = []
        self.build_graph(core_json_data)
        
    def build_graph(self, core_json_data: dict):
        """讀取 SSoT 陣列，動態實例化功能塊"""
        blocks_data = core_json_data.get('blocks', [])
        
        for b_data in blocks_data:
            bno = b_data.get('bno')
            fno = b_data.get('fno')
            fnm = b_data.get('fnm', 'UNKNOWN')
            terminals = b_data.get('terminals', {})
            params = b_data.get('raw_params', '')
            
            if bno is None or fno is None:
                continue
                
            # 查表實例化，若找不到則使用 DummyBlock (降級防護)
            block_class = self.BLOCK_FACTORY.get(fno, DummyBlock)
            block_instance = block_class(bno, fno, fnm, terminals, params)
            self.blocks.append(block_instance)
            
        # 核心規範：確保執行順序嚴格遵照 BNO 由小至大排序
        self.blocks.sort(key=lambda x: x.bno)
        logging.info(f"[Graph VM] 成功掛載 {len(self.blocks)} 個功能塊，已依 BNO 排序。")

    def step(self, global_registry: dict):
        """
        虛擬機核心掃描迴圈 (Scan Cycle)
        :param global_registry: 包含系統所有變數的狀態字典
        """
        # 依序執行每一個區塊的 calculate 方法
        for block in self.blocks:
            try:
                block.calculate(global_registry, self.dt)
            except Exception as e:
                logging.error(f"[Graph VM] BNO {block.bno} 執行異常: {e}")
                
        # 回傳當前的 global_registry 供外部（如 Orchestrator 或記錄器）讀取
        return global_registry
