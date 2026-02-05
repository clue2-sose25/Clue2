import datetime
import logging
import math
from locust import LoadTestShape
import config as CFG

class DailyLoadShape(LoadTestShape):
    def __init__(self):
        super().__init__()

        
        self.warmup_duration = CFG.warmup_duration
        self.warmup_percentage = CFG.warmup_percentage
        
        self.warmup_users = int(CFG.max_daily_users * self.warmup_percentage)
        self.stage_duration = CFG.stage_duration

        self.stages = [
            {"users_percentage":0.02},
            {"users_percentage":0.05},
            {"users_percentage":0.08},
            {"users_percentage":0.06},
            {"users_percentage":0.06},
            {"users_percentage":0.05},
            {"users_percentage":0.01},
            {"users_percentage":0.01}
        ]

        self.num_stages = len(self.stages)    
        self.scaling_factor = (24 - 1) / (self.num_stages - 1)

    def tick(self):
        run_time = self.get_run_time()
        kill_time = min(max((CFG.stage_duration / 10), 2), 30)
        spawn_rate = max(2, min(100, CFG.max_daily_users / 1000))
        
        # during Warmup
        if run_time < self.warmup_duration:
            return (self.warmup_users, spawn_rate)

        effective_run_time = run_time - self.warmup_duration
        to_kill = False
        if CFG.use_real_time:
            current_time = datetime.datetime.now()
            mapped_index = round(current_time.hour / self.scaling_factor)
            mapped_index = min(mapped_index, self.num_stages - 1)
            current_stage = mapped_index
            if current_time.minute >= 59:
                to_kill = True
        else:
            passed_stages = math.floor(effective_run_time / self.stage_duration)
            stage_run_time = effective_run_time - (passed_stages * self.stage_duration)
            current_stage = passed_stages % self.num_stages

            if stage_run_time > self.stage_duration - kill_time:
                to_kill = True
                
        if to_kill:
            if current_stage == self.num_stages - 1:
                return None 
            return (0, 100)

        try:
            stage = self.stages[current_stage]
            user_count = int(CFG.max_daily_users * stage["users_percentage"])
            return (user_count, spawn_rate)
        except Exception as e:
            logging.error(f"Error in stage {current_stage}: {e}")
            return (0, 100)