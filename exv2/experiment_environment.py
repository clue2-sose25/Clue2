from requests import get
from typing import Protocol

class WorkloadAutoConfig(Protocol):
    def set_workload(self, exp:"ExperimentEnvironment"):
        pass


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

        self.workload_settings = {}
        self.timeout_duration = 60*60 # at most we wait 60 minutes
        self.wait_before_workloads = 60
        self.wait_after_workloads = 120

        self.tags = []

    def total_duration(self):
        return self.timeout_duration + 30 #TODO make this more sensable but not based on the worklaod settings

    def set_workload(self, conf: WorkloadAutoConfig):
        conf.set_workload(self)
    