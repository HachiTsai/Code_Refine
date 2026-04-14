"""
🧠 Intelligence Navigator: Behavior Physical Model (v1.0)
============================================================
職責：模擬閥門 (Valve) 與馬達 (Motor) 的物理動態特性。
邏輯來源：6_Valve_Motor.md 與 10_signal.md。
美學：遵循 Aesthetic Hardening v2.0 規範。
"""

class ValvePhysicalModel:
    """模擬調節閥的物理特性"""
    def __init__(self, stroke_time=15.0, deadband=0.5, resolution=6000):
        self.stroke_time = stroke_time # 全行程時間 (sec)
        self.deadband = deadband       # 不感帶 (%)
        self.resolution = resolution   # 10_signal.md 定義的 0-6000 分辨率
        
        self.current_actual_pos = 0.0  # 真實物理位置 (%)
        self.prev_target_mv = 0.0

    def update(self, target_mv, dt=1.0):
        """
        根據目標 MV 更新真實位置。
        target_mv: 來自 PID 的指令 (0-100)
        dt: 模擬步長 (sec)
        """
        # 1. 模擬不感帶 (Deadband)
        if abs(target_mv - self.current_actual_pos) < self.deadband:
            return self.current_actual_pos

        # 2. 模擬行程速度限制 (Slew Rate)
        # 速度 = 100% / stroke_time
        max_change = (100.0 / self.stroke_time) * dt
        
        diff = target_mv - self.current_actual_pos
        if diff > max_change:
            self.current_actual_pos += max_change
        elif diff < -max_change:
            self.current_actual_pos -= max_change
        else:
            self.current_actual_pos = target_mv

        # 3. 模擬 10_signal.md 的數位解析度
        # 將連續值模擬為 0-6000 的階梯
        internal_code = round((self.current_actual_pos / 100.0) * self.resolution)
        self.current_actual_pos = (internal_code / self.resolution) * 100.0

        return self.current_actual_pos

class SignalConverter:
    """模擬 10_signal.md 的訊號轉換規格"""
    @staticmethod
    def to_internal(eng_value, zero=0.0, full=100.0):
        """工業單位 -> 0-6000 內部碼"""
        norm = (eng_value - zero) / (full - zero)
        return max(0, min(6000, round(norm * 6000)))

    @staticmethod
    def to_eng(internal_code, zero=0.0, full=100.0):
        """0-6000 內部碼 -> 工業單位"""
        return (internal_code / 6000.0) * (full - zero) + zero

class SelectionLogic:
    """模擬 6_SEL.md 的一點選擇開關邏輯"""
    def __init__(self, notch_count=16):
        self.notches = [0] * notch_count
        self.current_active = 0 # Notch 1-16 (0 表示無)

    def select(self, notch_no):
        """執行互斥選擇"""
        if 1 <= notch_no <= len(self.notches):
            self.notches = [0] * len(self.notches)
            self.notches[notch_no - 1] = 1
            self.current_active = notch_no
            return True
        return False

    def get_status(self):
        return self.notches
