from requests import get


class ExperimentEnvironment:

    def __init__(self):
        # files / io
        self.teastore_path = "teastore"  # where the repo with the teastore is located

        public_ip = get("https://api.ipify.org").content.decode("utf8")
        self.local_public_ip = public_ip if public_ip else "130.149.158.80"  #

        self.local_port = 8888
        # infra
        self.docker_user = (
            "tawalaya"  # the docker user to use for pushing/pulling images
        )
        self.remote_platform_arch = "linux/amd64"  # the target platform to build images for (kubernetes node architecture)
        self.local_platform_arch = "linux/amd64"  # the local architecture to use for local latency measurements

        self.resource_limits = (
            {  # the resource limits to use for the experiment (see below)
                "teastore-auth": {"cpu": 450, "memory": 1024},
                "teastore-webui": {"cpu": 1000, "memory": 1500},
                "teastore-recommender": {"cpu": 2000, "memory": 1024},
                "teastore-image": {"cpu": 1000, "memory": 1500},
            }
        )

        self.workload_settings = {
            # workload
            "LOADGENERATOR_STAGE_DURATION": 60,  # runtime per load stage in seconds
            "LOADGENERATOR_MAX_DAILY_USERS": 1000,  # the maximum number of daily users to simulate
            "LOCUSTFILE": "./consumerbehavior.py,./loadshapes.py",  # 8 different stages
        }

        self.num_stages = 8  # do not change unless the locustfile changed
        self.wait_before_workloads = 25
        self.wait_after_workloads = 75

        self.tags = []

    def total_duration(self):
        return 60 * 60 # at most we wait 60 minutes

    def set_rampup(self):
        lin_workload = {
            "workload": {
                "LOCUSTFILE": "./locustfile.py",
                "RUN_TIME": f'{self.workload_settings["LOADGENERATOR_STAGE_DURATION"] * self.num_stages}s',
                "SPAWN_RATE": 3,
                "USERS": self.workload_settings["LOADGENERATOR_MAX_DAILY_USERS"],
            }
        }

        self.workload_settings = self.workload_settings | lin_workload
        self.tags.append("rampup")
