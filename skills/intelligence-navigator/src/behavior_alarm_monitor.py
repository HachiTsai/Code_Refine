"""
🧠 Intelligence Navigator: Behavior Alarm Monitor (v1.0)
============================================================
職責：模擬日立 EX-N01A UA (User Alarm) 與 OG (Operator Guide)。
邏輯來源：7_ALM_OG.md。
美學：遵循 Aesthetic Hardening v2.0 規範。
"""

class AlarmMonitor:
    """模擬警報觸發與操作指南"""
    def __init__(self, alarm_configs=None):
        # 格式: {"IN0001": {"tag": "ALM001", "level": 1, "msg": "High Temp Alarm"}}
        self.configs = alarm_configs or {}
        self.active_alarms = set()
        self.alarm_history = []

    def check(self, global_registry):
        """掃描全域暫存器，偵測 0 -> 1 變化"""
        newly_triggered = []
        for addr, config in self.configs.items():
            current_val = global_registry.get(addr, 0)
            
            if current_val == 1 and addr not in self.active_alarms:
                # 觸發警報 (Positive Edge)
                self.active_alarms.add(addr)
                event = {
                    "tag": config.get("tag"),
                    "level": config.get("level", 3),
                    "message": config.get("msg", "Undefined Alarm"),
                    "status": "TRIGGERED"
                }
                self.alarm_history.append(event)
                newly_triggered.append(event)
            elif current_val == 0 and addr in self.active_alarms:
                # 警報解除
                self.active_alarms.remove(addr)
                
        return newly_triggered

    def get_summary(self):
        return self.alarm_history
