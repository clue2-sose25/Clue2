from requests import get


class ExperimentEnvironment:

    def __init__(self):
        # files / io
        self.teastore_path = "teastore"  # where the repo with the teastore is located

        public_ip = get("https://api.ipify.org").content.decode("utf8")
        self.local_public_ip = public_ip if public_ip else "130.149.158.80"  #

        self.local_port = 8888
        # infra
        self.docker_user = "tawalaya"  # the docker user to use for pushing/pulling images
        self.remote_platform_arch = "linux/amd64"  # the target platform to build images for (kubernetes node architecture)
        self.local_platform_arch = "linux/amd64"  # the local architecture to use for local latency measurements
        
        self.resource_limits = {  # the resource limits to use for the experiment (see below)
            "teastore-auth": {"cpu": 450, "memory": 700},
            "teastore-webui": {"cpu": 300, "memory": 800},
            "teastore-recommender": {"cpu": 450, "memory": 1024},
            "teastore-image": {"cpu": 300, "memory": 1024},
        }

        self.workload_settings =  {
            # workload
            "LOADGENERATOR_STAGE_DURATION": 120,  # runtime per load stage in seconds
            "LOADGENERATOR_MAX_DAILY_USERS": 6000,  # the maximum number of daily users to simulate
            "LOCUSTFILE": "./consumerbehavior.py,./loadshapes.py",
        }

        self.num_stages = 8
        self.wait_before_workloads = 120
        self.wait_after_workloads = 120


        def total_duration():
            return self.num_stages * self.workload_settings["LOADGENERATOR_STAGE_DURATION"] + self.wait_after_workloads
        