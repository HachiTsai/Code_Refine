"""
🧠 Intelligence Navigator: Behavior Blocks (v1.0)
============================================================
職責：定義 IEC 61131-3 虛擬機的所有功能塊 (FNO) 類別。
架構：Graph-based 拓撲模型，遵循「無狀態相依 (Stateless Dependency)」原則。
變更：由傳統硬編碼公式轉向動態實例化的圖節點引擎。
"""

import abc
import logging

class BaseBlock(abc.ABC):
    """
     IEC 61131-3 功能塊 (FNO) 抽象基底類別
     核心規範：此類別不得直接呼叫其他 Block，只能從 global_registry 讀寫資料。
    """
    def __init__(self, bno: int, fno: int, fnm: str, terminals: dict, params: str):
        self.bno = bno
        self.fno = fno
        self.fnm = fnm
        self.terminals = terminals # e.g. {"TERM1": {"lno": "LP137SVS03", ...}}
        self.params = params       # 原始的字串參數
        
        # 建立快速尋址映射表：將內部端子對應至 Global Registry 的 Key
        self.input_keys = {}
        for term_id, term_data in self.terminals.items():
            lno = term_data.get('lno')
            if lno:
                 self.input_keys[term_id] = lno
                 
    def _read_input(self, term_id: str, registry: dict, default_val=0.0):
        """輔助方法：安全地從 Registry 讀取腳位數值"""
        # 1. 嘗試從 LNO 讀取 (外部實體變數)
        lno = self.input_keys.get(term_id)
        if lno and lno in registry:
            return registry[lno]
            
        # 2. 嘗試從 ADDR 讀取 (內部 BNO 串接)
        term_data = self.terminals.get(term_id, {})
        addr = term_data.get('addr')
        if addr:
            bno_key = f"BNO_{addr}_OUT"
            if bno_key in registry:
                return registry[bno_key]
        
        # 3. 若沒有外部變數，嘗試讀取 enable 欄位作為常數
        enable_val = term_data.get('enable')
        if enable_val:
            # 優先嘗試從 registry 讀取 (如果 enable 是一個旗標如 IX0001S03)
            if isinstance(enable_val, str) and enable_val in registry:
                return float(registry[enable_val])
            try:
                return float(enable_val)
            except ValueError:
                # 處理布林常數等
                if str(enable_val).upper() == 'TRUE': return 1.0
                if str(enable_val).upper() == 'FALSE': return 0.0
                return enable_val # 回傳原始字串
                
        return default_val

    def _write_output(self, key: str, value, registry: dict):
        """輔助方法：安全地寫入運算結果至 Registry"""
        registry[key] = value

    @abc.abstractmethod
    def calculate(self, registry: dict, dt: float = 0.1):
        """
        核心運算方法，必須由子類別實作。
        :param registry: 全域狀態字典 (包含所有 PV, SV, 中間變數)
        :param dt: 掃描週期時間 (秒)
        """
        pass

class DummyBlock(BaseBlock):
    """降級防護功能塊 (Graceful Degradation Block)"""
    def __init__(self, bno: int, fno: int, fnm: str, terminals: dict, params: str):
        super().__init__(bno, fno, fnm, terminals, params)
        self.has_warned = False
        
    def calculate(self, registry: dict, dt: float = 0.1):
        if not self.has_warned:
            logging.warning(f"[Graph VM] BNO {self.bno} (FNO {self.fno} {self.fnm}) 尚未實作，已 Bypass。")
            self.has_warned = True

# ==========================================
# 🏭 Phase 2: MVP 核心 FNO 模組 (針對 LP137S03)
# ==========================================

class Block_F13_ASWH(BaseBlock):
    """
    F13 ASWH (Analog Switch / 類比選擇器)
    職責：多路選擇。依據各個端子的 Enable 信號，決定要輸出哪一個端子的輸入值。
    優先級：由後往前 (如 TERM3 > TERM2 > TERM1)。
    """
    def calculate(self, registry: dict, dt: float = 0.1):
        selected_val = 0.0
        # 由小到大遍歷，後面的會覆蓋前面的，達成「端子編號愈大優先權越高」
        for i in range(1, 9):
            term_key = f"TERM{i}"
            if term_key in self.terminals:
                term_data = self.terminals[term_key]
                enable_cond = term_data.get('enable')
                
                is_enabled = False
                if enable_cond:
                    if isinstance(enable_cond, str) and enable_cond in registry:
                        is_enabled = bool(registry[enable_cond])
                    else:
                        try:
                            is_enabled = bool(float(enable_cond))
                        except ValueError:
                            is_enabled = str(enable_cond).upper() == 'TRUE'
                            
                if is_enabled:
                    selected_val = self._read_input(term_key, registry)
                    
        self._write_output(f"BNO_{self.bno}_OUT", selected_val, registry)

class Block_F08_AHLA(BaseBlock):
    """
    F08 AHLA (Analog High/Low Alarm / 上下限警報器)
    職責：監控 TERM1 數值，若超越極限閾值則觸發警報旗標。
    """
    def calculate(self, registry: dict, dt: float = 0.1):
        val = self._read_input("TERM1", registry)
        
        # 實務上閾值應從 params 讀取，此處為開環動態保護預設 1.0/-1.0
        limit_h = 1.0
        limit_l = -1.0
        
        alarm_h = 1.0 if val > limit_h else 0.0
        alarm_l = 1.0 if val < limit_l else 0.0
        
        # 寫回 BNO 輸出與警報旗標
        self._write_output(f"BNO_{self.bno}_OUT", val, registry)
        self._write_output(f"BNO_{self.bno}_ALM_H", alarm_h, registry)
        self._write_output(f"BNO_{self.bno}_ALM_L", alarm_l, registry)

class Block_F02_AINP(BaseBlock):
    """F02 AINP (Analog Input / 類比輸入處理與濾波)"""
    def __init__(self, bno, fno, fnm, terminals, params):
        super().__init__(bno, fno, fnm, terminals, params)
        self.prev_val = 0.0

    def calculate(self, registry: dict, dt: float = 0.1):
        raw_val = self._read_input("TERM1", registry)
        # 簡單的一階低通濾波 (T1=0.010)
        tf = 0.010
        val = self.prev_val + (dt / (tf + dt)) * (raw_val - self.prev_val)
        self.prev_val = val
        self._write_output(f"BNO_{self.bno}_OUT", val, registry)

class Block_F07_COUT(BaseBlock):
    """F07 COUT (Analog Output / 輸出極限與變化率限制)"""
    def __init__(self, bno, fno, fnm, terminals, params):
        super().__init__(bno, fno, fnm, terminals, params)
        self.current_mv = 0.0

    def calculate(self, registry: dict, dt: float = 0.1):
        target_mv = self._read_input("TERM1", registry)
        
        # 解析 R1/R2 (LP137S03 要求 0.030)
        r1 = 0.030
        r2 = 0.030
        mh = 1.0
        ml = 0.0
        
        delta = target_mv - self.current_mv
        if delta > r1:
            next_mv = self.current_mv + r1
        elif delta < -r2:
            next_mv = self.current_mv - r2
        else:
            next_mv = target_mv
            
        final_mv = max(ml, min(mh, next_mv))
        self.current_mv = final_mv
        
        self._write_output(f"BNO_{self.bno}_OUT", final_mv, registry)
        
        # 同步寫回實體 AO (如 TERM4 定義)
        out_term = self.terminals.get("TERM4", {})
        out_lno = out_term.get('lno')
        if out_lno:
            self._write_output(out_lno, final_mv, registry)

class Block_F14_APRO(BaseBlock):
    """F14 APRO (Analog Profile / 雙軌斜坡發生器)"""
    def __init__(self, bno, fno, fnm, terminals, params):
        super().__init__(bno, fno, fnm, terminals, params)
        self.current_val = 0.0

    def calculate(self, registry: dict, dt: float = 0.1):
        target_sv = self._read_input("TERM1", registry)
        # BNO 46/47 會使用 TERM3 的 enable 當作斜率參數 (例如 0.100)
        rate = self._read_input("TERM3", registry, default_val=0.1)
        
        if self.current_val < target_sv:
            self.current_val = min(target_sv, self.current_val + rate * dt)
        elif self.current_val > target_sv:
            self.current_val = max(target_sv, self.current_val - rate * dt)
            
        self._write_output(f"BNO_{self.bno}_OUT", self.current_val, registry)

class Block_F04_CDEV(BaseBlock):
    """F04 CDEV (Control Deviation / 偏差計算)"""
    def calculate(self, registry: dict, dt: float = 0.1):
        pv = self._read_input("TERM1", registry)
        sv = self._read_input("TERM2", registry)
        self._write_output(f"BNO_{self.bno}_OUT", pv - sv, registry)

class Block_F12_ACON(BaseBlock):
    """F12 ACON (Analog Constant / 常數產生器)"""
    def calculate(self, registry: dict, dt: float = 0.1):
        # LP137S03 通常退避常數為 0.2 或自 params 讀取，預設 0.0
        val = 0.0
        try:
            if self.params: val = float(self.params)
        except: pass
        self._write_output(f"BNO_{self.bno}_OUT", val, registry)

class Block_F01_ESTS(BaseBlock):
    """F01 ESTS (Status Changer / 狀態變更器)"""
    def __init__(self, bno, fno, fnm, terminals, params):
        super().__init__(bno, fno, fnm, terminals, params)
        self.prev_trigger = 0.0

    def calculate(self, registry: dict, dt: float = 0.1):
        trigger = self._read_input("TERM1", registry)
        # 上升緣偵測 (Rising Edge)
        pulse = 1.0 if trigger > 0.5 and self.prev_trigger <= 0.5 else 0.0
        self.prev_trigger = trigger
        self._write_output(f"BNO_{self.bno}_OUT", pulse, registry)

class Block_F00_ALGC(BaseBlock):
    """F00 ALGC (Boolean Logic / 布林邏輯陣列)"""
    def calculate(self, registry: dict, dt: float = 0.1):
        t1 = self._read_input("TERM1", registry)
        t2 = self._read_input("TERM2", registry)
        
        # 簡單實作 AND (Parameter=0)
        mode = 0
        try:
            mode = int(self.params)
        except: pass
        
        if mode == 0: # AND
            out = 1.0 if t1 > 0.5 and t2 > 0.5 else 0.0
        elif mode == 8: # OR 或其他 (簡化)
            out = 1.0 if t1 > 0.5 or t2 > 0.5 else 0.0
        else:
            out = t1
            
        self._write_output(f"BNO_{self.bno}_OUT", out, registry)
