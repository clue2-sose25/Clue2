from experiment_environment import ExperimentEnvironment


LOADGENERATOR_DURATION = 160
LOADGENERATOR_MAX_DAILY_USERS = 1000



class ShapredWorkload():
    def set_workload(self, exp: ExperimentEnvironment):
        """
            Uses custom loadshape behavior with max users for duration
        """
        exp.workload_settings = {
            # workload
            "LOADGENERATOR_STAGE_DURATION": LOADGENERATOR_DURATION//8,  # runtime per load stage in seconds
            "LOADGENERATOR_MAX_DAILY_USERS": LOADGENERATOR_MAX_DAILY_USERS,  # the maximum number of daily users to simulate
            "LOCUST_LOCUSTFILE": "./consumerbehavior.py,./loadshapes.py",  # 8 different stages
        }
        exp.tags.append("shaped")
        exp.timeout_duration = LOADGENERATOR_DURATION+60

class RampingWorkload():
    def set_workload(self, exp: ExperimentEnvironment):
        """
            ramps up the workload by 3 users a second until max users for duration
        """
        exp.workload_settings = {
            "LOCUST_LOCUSTFILE": "./locustfile.py",
            "LOCUST_RUN_TIME": f'{LOADGENERATOR_DURATION}s',
            "LOCUST_SPAWN_RATE": 3,
            "LOCUST_USERS": LOADGENERATOR_MAX_DAILY_USERS,
        }
        exp.tags.append("rampup")
        exp.timeout_duration = LOADGENERATOR_DURATION+60
    
class PausingWorkload():
    def set_workload(self, exp: ExperimentEnvironment):
        """
            starts 20 pausing users, no rampup for duration
        """
        exp.workload_settings = {
            "LOCUST_LOCUSTFILE": "./pausing_users.py",
            "LOCUST_RUN_TIME": f'{LOADGENERATOR_DURATION}s',
            "LOCUST_SPAWN_RATE": 1,
            "LOCUST_USERS": 20,
        }
        exp.timeout_duration = LOADGENERATOR_DURATION+60
        exp.tags.append("pausing")

class FixedRampingWorkload():
    def set_workload(self, exp:ExperimentEnvironment):
        """
            starts a ramoing workload up till max users for at most 1000 requests (failed or successful) running at most duration long
        """
        exp.workload_settings = {
            "LOCUST_LOCUSTFILE": "./fixed_requests.py",
            "LOCUST_RUN_TIME": f'{LOADGENERATOR_DURATION}s',
            "LOCUST_SPAWN_RATE": 3,
            "LOCUST_USERS": LOADGENERATOR_MAX_DAILY_USERS,
            "MAX_REQUESTS": 1000,
        }
        exp.tags.append("fixed")
        exp.timeout_duration = LOADGENERATOR_DURATION+60