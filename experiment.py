#! /usr/bin/env python3
from enum import Enum
from queue import Queue,Empty
import os
from os import path
import sys
import subprocess
import docker

from kubernetes import client, config
from kubernetes.stream import portforward
import time
import signal

#gloabls to drive the experiment 
tea_store="teastore" #where the repo with the teastore is located
workload_runtime = 120
docker_user = "tawalaya" # the docker user to use for pushing/pulling images
remote_platform_arch = "linux/amd64" # the target platform to build images for (kubernetes node architecture)
local_platform_arch = "linux/amd64" # the local architecture to use for local latency measurements
local_public_ip = "130.149.158.80" # TODO: XXX this we need find out automatically
local_port = 8888
MAX_EXPERIMENT_RUNTIME = 8*workload_runtime + 120 # 8 stages + 2 minutes to deploy and cleanup
# setup clients
config.load_kube_config()
docker_client = docker.from_env()

class ScalingExperimentSetting(Enum):
    MEMORYBOUND = 1
    CPUBOUND = 2 
    BOTH = 3

    def __str__(self) -> str:
        if self == ScalingExperimentSetting.MEMORYBOUND:
            return "mem"
        elif self == ScalingExperimentSetting.CPUBOUND:
            return "cpu"
        elif self == ScalingExperimentSetting.BOTH:
            return "full"
        else:
            return "none"



class Experiment:
    def __init__(self, 
                 name:str, 
                 target_branch:str, 
                 patches:list,
                 namespace:str,
                 colocated_workload:bool=False,
                 prometheus_url:str="http://localhost:9090",
                 autoscaleing:ScalingExperimentSetting=None):
        # metadata
        self.name = name
        self.target_branch = target_branch
        self.namespace = namespace
        self.patches = patches

        # observability data
        self.prometheus = prometheus_url
        self.colocated_workload = colocated_workload
        self.autoscaling = autoscaleing


    def __str__(self) -> str:
        if self.autoscaling:
            return f"{self.name}_{self.target_branch}_{self.autoscaling}".replace("/","_")
        else:
            return f"{self.name}_{self.target_branch}".replace("/","_")

from csv import DictWriter
class FlushingQeueu(Queue):
    def __init__(self, filename:str,buffer_size=60,fields=[]) -> None:
        super().__init__(2*buffer_size)
        self.buffer_size = buffer_size
        self.filename = filename
        self.fields = fields
    
    def put(self, item):
        if self.qsize() >= self.buffer_size:
            self.flush()
        super().put(item)

    def flush(self):
        if not os.path.isfile(self.filename):
            with open(self.filename,"w") as f:
                DictWriter(f,fieldnames=self.fields).writeheader()
        with open(self.filename,"a") as f: 
            writer = DictWriter(f, fieldnames=self.fields)
            for _ in range(self.buffer_size):
                try:
                    writer.writerow(self.get(block=False,timeout=None).to_dict())
                except Empty:
                    break

def build_workload(exp:Experiment,wokload_branch:str= "priv/lierseleow/loadgenerator"):
    """
      build the workload image as a docker image, either to be deployed localy or collocated with the service
    """
    git = subprocess.check_call(["git", "switch",wokload_branch],cwd=path.join(tea_store))
    if git != 0:
        raise RuntimeError(f"failed to switch git to {wokload_branch}")

    platform = local_platform_arch if exp.colocated_workload else remote_platform_arch
    
    build = subprocess.check_call(["docker", "buildx", "build", "--platform", platform, "-t", f"{docker_user}/loadgenerator", "."],cwd=path.join(tea_store,"loadgenerator"))
    if build != 0:
         raise RuntimeError(f"failed to build {wokload_branch}")

    docker_client.images.push(f"{docker_user}/loadgenerator")
    # subprocess.check_call(["docker", "push", f"{docker_user}/loadgenerator"])

def build_images(exp:Experiment):
    """
        build all the images for the experiment and push them to the docker registry.

        perfrom some patching of the build scripts to use buildx (for multi-arch builds)
    """
    git = subprocess.check_call(["git", "switch", exp.target_branch], cwd=path.join(tea_store))
    if git != 0:
        raise RuntimeError(f"failed to swich git to {exp.target_branch}")

    print(f"deploying {exp.target_branch}")

    # ensure mvn build ...
    #docker run -v foo:/mnt --rm -it --workdir /mnt  maven mvn clean install -DskipTests
    mvn = docker_client.containers.run(image="maven", 
                                 auto_remove=True,
                                 volumes={path.abspath(path.join(tea_store)): {'bind': '/mnt', 'mode': 'rw'}},
                                 working_dir="/mnt",
                                 command="mvn clean install -DskipTests")
    if "BUILD SUCCESS" not in mvn.decode("utf-8"):
        raise RuntimeError("failed to build teastore. Run mvn clean install -DskipTests manually and see why it fails")
    else:
        print("rebuild java deps")
    
    # patch build_docker.sh to use buildx 
    with open(path.join(tea_store,"tools","build_docker.sh"),"r") as f:
        script = f.read()
    
    if "buildx" in script:
        print("buildx already used")
    else:
        script = script.replace("docker build",f"docker buildx build --platform {remote_platform_arch}")
        with open(path.join(tea_store,"tools","build_docker.sh"),"w") as f:
            f.write(script)


    # 2. cd tools && ./build_docker.sh -r <docker_user>/ -p && cd ..
    build = subprocess.check_call(["sh","build_docker.sh", "-r", f"{docker_user}/", "-p"],cwd=path.join(tea_store,"tools"))

    if build != 0:
        raise RuntimeError("failed to build docker images. Run build_docker.sh manually and see why it fails")
        
    print(f"build {docker_user}/* images")

def deploy_branch(exp:Experiment,observations:str="data/default"):
    """
        deploy the helm chart with the given values.yaml,
        patching the values.yaml before deployment:
            - replace the docker user with the given user
            - replace the tag to ensure images are pulled
            - replace the node selector to ensure we only run on nodes that we can observe (require nodes to run scaphandre)
            - apply any patches given in the experiment (see yaml_patch)
        
        wait for the deployment to be ready, or timeout after 3 minutes
    """
    with open(path.join(tea_store,"examples","helm","values.yaml"),"r") as f:
        values = f.read()
        values = values.replace("descartesresearch", docker_user)
        #ensure we only run on nodes that we can observe
        values = values.replace(r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}')
        values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
        values = values.replace(r'tag: ""', r'tag: "latest"')
        if exp.autoscaling:
            values = values.replace(r"enabled: false","enabled: true")
            if exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                values = values.replace(r"targetCPUUtilizationPercentage: 80",r"# targetCPUUtilizationPercentage: 80")
                values = values.replace(r"# targetMemoryUtilizationPercentage: 80",r"targetMemoryUtilizationPercentage: 80")
            elif exp.autoscaling == ScalingExperimentSetting.BOTH:
                values = values.replace(r"# targetMemoryUtilizationPercentage: 80",r"targetMemoryUtilizationPercentage: 80")



    from yaml_patch import patch_yaml
    patch_yaml(values, exp.patches)

    with open(path.join(tea_store,"examples","helm","values.yaml"), "w") as f:
        f.write(values)

    #write copy of used values to observations
    with open(path.join(observations,"values.yaml"), "w") as f:
        f.write(values)

    helm_deploy = subprocess.check_output(["helm", "install", "teastore", "-n",exp.namespace,"."], cwd=path.join(tea_store,"examples","helm"))
    helm_deploy = helm_deploy.decode("utf-8")
    if not "STATUS: deployed" in helm_deploy:
        raise RuntimeError("failed to deploy helm chart. Run helm install manually and see why it fails")

    wait_until_ready(["teastore-auth","teastore-registry","teastore-webui"], 180, namespace=exp.namespace)

    if exp.autoscaling:
        setup_autoscaleing(exp)
    

def wait_until_ready(services, timeout, namespace="default"):
   
    v1 = client.AppsV1Api()
    ready_services = set()
    start_time = time.time()
    services = set(services)
    while len(ready_services) < len(services) and time.time() - start_time < timeout:
        for service in services.difference(ready_services): #only check services that are not ready yet
            try:
                service_status = v1.read_namespaced_stateful_set_status(service, namespace)
                if  service_status.status.ready_replicas and service_status.status.ready_replicas > 0:
                    ready_services.add(service)
            except Exception as e:
                print(e)
                pass
        if services == ready_services:
            return True
        time.sleep(1)
        print("waiting for deployment to be ready")
    raise RuntimeError("Timeout reached. The following services are not ready: " + str(list(set(services) - set(ready_services))))

def _run_experiment(exp:Experiment,observations:str="data/default"):
        from psc import ResourceTracker, NodeUsage
        from datetime import datetime
        datafile = path.join(observations,f"measurements_{datetime.now().strftime('%d_%m_%Y_%H_%M')}.csv")
        observations_channel = FlushingQeueu(datafile,buffer_size=32,fields=NodeUsage._fields)
        tracker = ResourceTracker(exp.prometheus, observations_channel, exp.namespace, 10)
        
        # 5. start workload
        # start resouce tracker
        tracker.start()
        def cancle():
            tracker.stop()
            observations_channel.flush()
            signal.raise_signal(signal.SIGUSR1) # raise signal to stop workload
            print("workload timeout reached.")

        signal.signal(signal.SIGALRM,cancle) 
        signal.alarm(MAX_EXPERIMENT_RUNTIME)
        # TODO: XXX deploy workload on differnt node or localy and wait for workload to be compleated (or timeout)
        if exp.colocated_workload:
            #TODO: deploy to a differnt node on kubernetes
            pass
        else:
           _run_local_workload(exp,observations)
        # stop resource tracker
        tracker.stop()
        observations_channel.flush()
        signal.alarm(0) # cancel alarm

def _run_local_workload(exp:Experiment,observations:str="data"):

    forward = subprocess.Popen(["kubectl","-n",exp.namespace,"port-forward","--address","0.0.0.0","services/teastore-webui",f"{local_port}:80"],stdin=subprocess.PIPE, stderr=subprocess.PIPE)


    # create locost stats files
    mounts = {
            path.abspath(path.join(observations,"locost_stats.csv")): {'bind': '/loadgenerator/teastore_stats.csv', 'mode': 'rw'},
            path.abspath(path.join(observations,"locost_failures.csv")): {'bind': '/loadgenerator/teastore_failures.csv', 'mode': 'rw'},
            path.abspath(path.join(observations,"locost_stats_history.csv")): {'bind': '/loadgenerator/teastore_stats_history.csv', 'mode': 'rw'},
            path.abspath(path.join(observations,"locost_report.html")): {'bind': '/loadgenerator/teastore_report.html', 'mode': 'rw'},
    }
    for f in mounts.keys():
        if not os.path.isfile(f):
            with open(f,"w") as f:
                pass
    #TODO: XXX get local ip to use for locust host
    def cancle():
        forward.kill()
        try:
            docker_client.containers.get("loadgenerator").kill()
        except: 
            pass
        print("local workload timeout reached.")
    signal.signal(signal.SIGUSR1,cancle) 
    try:
        workload = docker_client.containers.run(
            image=f"{docker_user}/loadgenerator",
            auto_remove=True,
            environment={
                "LOADGENERATOR_MAX_DAILY_USERS":2000, #The maximum daily users.
                "LOADGENERATOR_STAGE_DURATION":workload_runtime, #The duration of a stage in seconds.
                "LOADGENERATOR_USE_CURRENTTIME":"n", #using current time to drive worload (e.g. day/night cycle)
                "LOADGENERATOR_ENDPOINT_NAME":"Vanilla",#the workload profile
                "LOCUST_HOST":f"http://{local_public_ip}:{local_port}/tools.descartes.teastore.webui" #endoint of the deployed service
            },
            stdout=True,
            stderr=True,
            volumes=mounts,
            name="loadgenerator"
        )
        with open(path.join(observations,"docker.log"),"w") as f:
            f.write(workload)
    except Exception as e:
        print("failed to run workload properly",e)
    forward.kill()
    
def run_experiment(exp:Experiment, run:int):
    # 0. create experiment folder
    out = "data"
    if exp.autoscaling:
        out+="_scale"
    observations = path.join(out,exp.__str__(),f"{run}")
    

    try:
        try:
            os.makedirs(observations,exist_ok=False)
        except OSError:
            raise RuntimeError("data for this experiment already exsist, skipping")
        
        # 3. rewrite helm values with <docker_user> && env details as nessary (namespace ...)
        
        deploy_branch(exp,observations)

        # 4. run collection agent (fetch prometeus )
        time.sleep(120) # wait for 120s before stressing the workload
        _run_experiment(exp,observations)
    except RuntimeError as e:
        print(e)
    finally:
        cleanup(exp)


def cleanup(exp:Experiment):
    subprocess.run(["helm", "uninstall", "teastore", "-n",exp.namespace])
    subprocess.run(["git","checkout","examples/helm/values.yaml"], cwd=path.join(tea_store))
    subprocess.run(["git","checkout","tools/build_docker.sh"], cwd=path.join(tea_store))

if __name__ == "__main__":
    scale = None
    exps = [
        #Experiment(name="baseline",target_branch="vanilla",patches=[], namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="jvm",target_branch="jvm-impoove",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="norec",target_branch="feature/norecommendations",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="lessrec",target_branch="feature/lessrecs",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="obs",target_branch="feature/object-storage",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="dbopt",target_branch="feature/db-optimization",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="car",target_branch="Carbon-Aware-Retraining",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        #Experiment(name="sig",target_branch="ssg+api-gateway",patches=[],namespace="bench",colocated_workload=False,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
    ]
    for exp in exps:
        build_workload(exp)
        build_images(exp)
        for i in range(3):
            run_experiment(exp,i)


def setup_autoscaleing(exp:Experiment):
    pass

def cleanup_autoscaleing(exp:Experiment):
    pass