"""
🧠 Intelligence Navigator: Behavior Orchestrator (v1.0)
============================================================
職責：協調 SEQ、BLS 與 DDC 引擎，執行全場級同步模擬。
美學：遵循 Aesthetic Hardening v2.0 規範。
"""

from behavior_simulator import HitachiDDCSimulator
from behavior_graph_engine import HitachiGraphSimulator
from behavior_seq_engine import HitachiSEQSimulator
from behavior_bls_engine import HitachiBLSSimulator
from behavior_physical_model import ValvePhysicalModel, SelectionLogic # 新增選擇邏輯
from behavior_alarm_monitor import AlarmMonitor # 新增警報監控
import json

class DCSOrchestrator:
    """數位孿生同步協調中樞 (v5.0 - Graph VM Integration)"""
    def __init__(self, ddc_params, us_data, bls_data=None, dt=1.0):
        # 判斷是否為 Graph VM 格式 (有 blocks 陣列且不為空)
        self.is_graph_vm = bool(ddc_params.get('blocks'))
        
        if self.is_graph_vm:
            self.ddc = HitachiGraphSimulator(ddc_params, dt=dt)
        else:
            self.ddc = HitachiDDCSimulator(ddc_params, dt=dt)
            
        self.seq = HitachiSEQSimulator(us_data)
        self.bls = HitachiBLSSimulator(bls_data) if bls_data else None
        self.valve = ValvePhysicalModel(stroke_time=15.0, deadband=0.5)
        self.sel = SelectionLogic(notch_count=5) # 模擬 5 點選擇開關
        
        # 模擬警報配置
        alarm_configs = {
            "IN0001": {"tag": "UA001", "level": 1, "msg": "R301 CRITICAL HIGH TEMP"}
        }
        self.monitor = AlarmMonitor(alarm_configs)
        
        self.dt = dt
        self.history = []
        self.triggered_events = []
        
        self.registry = {
            "TICA301.SV": 30.0,
            "TICA301.PV": 30.0,
            "TICA301DATA1.SV": 30.0,
            "PICA301DATA1.SV": 0.0,
            "VALVE.ACTUAL_POS": 0.0,
            "IN0001": 0 # 初始無高溫警報
        }

    def run_batch_simulation(self, steps_to_simulate=3600):
        """執行具備安全感知與選擇邏輯的全鏈路模擬"""
        print(f"🎬 啟動全場同步模擬 (SEQ + BLS + DDC + Safety + SEL)...")
        if self.is_graph_vm:
            print("🚀 [VM Mode] 已掛載 Graph VM 圖節點虛擬機！")
        else:
            print("⏳ [Legacy Mode] 降級使用傳統 PID 公式計算器。")
            
        self.seq.is_active = True
        
        for t in range(steps_to_simulate):
            # 1. 邏輯層 (SEQ/BLS)
            self.seq.update(self.dt)
            if self.seq.current_step == 5:
                self.registry["TICA301DATA1.SV"] = 70.0
            
            if self.bls:
                self.registry = self.bls.execute(self.registry)
            
            # 2. 安全監控層 (Alarm Check)
            # 模擬：若溫度超過 75 度，觸發 IN0001
            if self.registry["TICA301.PV"] > 75.0:
                self.registry["IN0001"] = 1
            
            new_alarms = self.monitor.check(self.registry)
            if new_alarms:
                for a in new_alarms:
                    print(f"🚨 [ALARM TRIGGERED] {a['tag']}: {a['message']}")
                    self.triggered_events.append(a)
            
            # 3. 控制層 (DDC)
            if self.is_graph_vm:
                # 注入測試用的初始狀態
                if t == 0:
                    self.registry['IN2015S03'] = 1.0  # 觸發 Cascade 模式
                    self.registry['DI0149S03'] = 0.0  # 實體開關就緒
                    self.registry['LC137S03'] = 1.0   # 迴路允許
                    self.registry['AI0095S03'] = 0.0  # 初始轉速 0
                    self.registry['LP137SVS03'] = 50.0 # 目標轉速 50%
                    
                # Graph VM 讀取與寫入全域 Registry
                self.registry = self.ddc.step(self.registry)
                
                # 從 COUT 模組 (或目標 AO) 提取輸出
                target_mv = self.registry.get("AO0027S03", 0.0)
                pv = self.registry.get("AI0095S03", 0.0)
                sv = self.registry.get("LP137SVS03", 0.0)
            else:
                # Legacy PID Mode
                sv = self.registry.get("TICA301DATA1.SV", 30.0)
                pv = self.registry.get("TICA301.PV", 30.0)
                target_mv = self.ddc.step(pv, sv)
            
            # 4. 物理執行層 (Valve)
            actual_mv = self.valve.update(target_mv, self.dt)
            self.registry["VALVE.ACTUAL_POS"] = actual_mv
            
            # 5. 物理過程更新
            if self.is_graph_vm:
                # 模擬馬達轉速響應 (簡單一階模型)
                k_process = 1.0
                tau_process = 5.0
                pv += (self.dt / tau_process) * (k_process * actual_mv - pv)
                self.registry["AI0095S03"] = pv
            else:
                k_process = 0.8
                tau_process = 300.0
                pv += (self.dt / tau_process) * (k_process * actual_mv - (pv - 30.0))
                self.registry["TICA301.PV"] = pv
            
            # 6. 記錄歷史
            if t % 60 == 0:
                self.history.append({
                    "min": t // 60,
                    "step": self.seq.current_step,
                    "pv": round(pv, 2),
                    "sv": sv,
                    "alarms": len(self.monitor.active_alarms)
                })
                
        return self.history
