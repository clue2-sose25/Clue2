#! /usr/bin/env python3
from enum import Enum
from queue import Queue,Empty
import os
from os import path
import math
import subprocess
import tarfile
from tempfile import TemporaryFile
import docker

from kubernetes import client, config, watch
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException
import time
import signal
import base64
from requests import get

DIRTY = False
SKIPBUILD = False

ip = get('https://api.ipify.org').content.decode('utf8')

# setup clients
config.load_kube_config()
docker_client = docker.from_env()

#gloabls to drive the experiment 
env = {
    #files / io
    "tea_store_path":"teastore",  #where the repo with the teastore is located
    "local_public_ip":ip if ip else "130.149.158.80", #
    "local_port":8888,
    #infra
    "docker_user":"tawalaya", # the docker user to use for pushing/pulling images
    "remote_platform_arch":"linux/amd64", # the target platform to build images for (kubernetes node architecture)
    "local_platform_arch":"linux/amd64", # the local architecture to use for local latency measurements
    "resouce_limits":  # the resource limits to use for the experiment (see below)
    {
        "teastore-auth":        {"cpu": 450,"memory": 700},
        "teastore-webui":       {"cpu": 300,"memory": 800},
        "teastore-recommender": {"cpu": 450,"memory": 1024},
        "teastore-image":       {"cpu": 300,"memory": 1024},
    }, 
    #workload
    "workload_runtime":120, # runtime per load stage in seconds
    "workload_max_users":6000, # the maximum number of daily users to simulate
    "workloads":"./consumerbehavior.py,./loadshapes.py"
}

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
                 namespace:str,
                 colocated_workload:bool=False,
                 patches:list=[],
                 prometheus_url:str="http://localhost:9090",
                 autoscaleing:ScalingExperimentSetting=None,
                 env_patches:dict = {}):
        # metadata
        self.name = name
        self.target_branch = target_branch
        self.namespace = namespace
        self.patches = patches

        # observability data
        self.prometheus = prometheus_url
        self.colocated_workload = colocated_workload
        self.autoscaling = autoscaleing
        self.env_patches = env_patches


    def __str__(self) -> str:
        if self.autoscaling:
            return f"{self.name}_{self.target_branch}_{self.autoscaling}".replace("/","_")
        else:
            return f"{self.name}_{self.target_branch}".replace("/","_")
        
    def createJson(self, env:dict = {}):
        import json
        description = {
            "name": self.name,
            "target_branch":self.target_branch,
            "namespace":self.namespace,
            "patches":self.patches,
            "workload": "colocated" if self.colocated_workload else "local",
            "scaling": str(self.autoscaling),
            "env_patches":self.env_patches,
        }
        description = description | env
        return json.dumps(description)


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
    platform = env["local_platform_arch"]if exp.colocated_workload else env["remote_platform_arch"]
    
    build = subprocess.check_call(["docker", "buildx", "build", "--platform", platform, "-t", f"{env['docker_user']}/loadgenerator", "."],cwd=path.join("loadgenerator"))
    if build != 0:
         raise RuntimeError(f"failed to build {wokload_branch}")

    docker_client.images.push(f"{env['docker_user']}/loadgenerator")

def build_images(exp:Experiment):
    """
        build all the images for the experiment and push them to the docker registry.

        perfrom some patching of the build scripts to use buildx (for multi-arch builds)
    """
    git = subprocess.check_call(["git", "switch", exp.target_branch], cwd=path.join(env["tea_store_path"]))
    if git != 0:
        raise RuntimeError(f"failed to swich git to {exp.target_branch}")

    print(f"deploying {exp.target_branch}")

    # ensure mvn build ...
    #docker run -v foo:/mnt --rm -it --workdir /mnt  maven mvn clean install -DskipTests
    mvn = docker_client.containers.run(image="maven", 
                                 auto_remove=True,
                                 volumes={path.abspath(path.join(env["tea_store_path"])): {'bind': '/mnt', 'mode': 'rw'}},
                                 working_dir="/mnt",
                                 command="mvn clean install -DskipTests")
    if "BUILD SUCCESS" not in mvn.decode("utf-8"):
        raise RuntimeError("failed to build teastore. Run mvn clean install -DskipTests manually and see why it fails")
    else:
        print("rebuild java deps")
    
    # patch build_docker.sh to use buildx 
    with open(path.join(env["tea_store_path"],"tools","build_docker.sh"),"r") as f:
        script = f.read()
    
    if "buildx" in script:
        print("buildx already used")
    else:
        script = script.replace("docker build",f"docker buildx build --platform {env['remote_platform_arch']}")
        with open(path.join(env["tea_store_path"],"tools","build_docker.sh"),"w") as f:
            f.write(script)


    # 2. cd tools && ./build_docker.sh -r <env["docker_user"]/ -p && cd ..
    build = subprocess.check_call(["sh","build_docker.sh", "-r", f"{env['docker_user']}/", "-p"],cwd=path.join(env['tea_store_path'],"tools"))

    if build != 0:
        raise RuntimeError("failed to build docker images. Run build_docker.sh manually and see why it fails")
        
    print(f"build {env['docker_user']}/* images")

def setup_autoscaleing(exp:Experiment):
    if exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND or exp.autoscaling == ScalingExperimentSetting.BOTH:
        raise NotImplementedError("memory bound autoscaling not implemented in cluster yet")
    print(f"setting up hpa scaleing")
    # create a list of statefulsets to scale
    # for each statefulset: set memory and cpu limites/requests per service
    # then create hpa for each statefulset with the given target based on the experiment setting
    apps = client.AppsV1Api()
    hpas = client.AutoscalingV1Api()
    sets:client.V1StatefulSetList = apps.list_namespaced_stateful_set(exp.namespace)
    for set in sets.items:
        if set.metadata.name in env["resouce_limits"]:
            limit = env["resouce_limits"][set.metadata.name]
        else: 
            continue
        set.spec.template.spec.containers[0].resources = client.V1ResourceRequirements(
            requests={
                "cpu":f'{limit["cpu"]}m',
                "memory":f'{limit["memory"]}Mi'
            },
            limits={
                "cpu":f'{int(math.floor(limit["cpu"]*1.5))}m',
                "memory":f'{int(math.floor(limit["memory"]*1.5))}Mi',
            }
        )
        try:
            resp = apps.patch_namespaced_stateful_set(set.metadata.name,exp.namespace,set)
            resp = hpas.create_namespaced_horizontal_pod_autoscaler(
                body=client.V1HorizontalPodAutoscaler(
                    metadata=client.V1ObjectMeta(
                        name=set.metadata.name,
                        namespace=exp.namespace
                    ),
                    spec=client.V1HorizontalPodAutoscalerSpec(
                        scale_target_ref=client.V1CrossVersionObjectReference(
                            api_version="apps/v1",
                            kind="StatefulSet",
                            name=set.metadata.name
                        ),
                        min_replicas=1,
                        max_replicas=3,
                        target_cpu_utilization_percentage=80
                    )
                ),
                namespace=exp.namespace
            )
        except ApiException as e:
            if e.status == 409:
                print(f"HPA for {set.metadata.name} already exsist")
            else:
                raise e 

def cleanup_autoscaleing(exp:Experiment):
    hpas = client.AutoscalingV1Api()
    _hpas = hpas.list_namespaced_horizontal_pod_autoscaler(exp.namespace)
    for set in _hpas.items:
        hpas.delete_namespaced_horizontal_pod_autoscaler(
            name=set.metadata.name,
            namespace=exp.namespace
        )

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
    with open(path.join(env["tea_store_path"],"examples","helm","values.yaml"),"r") as f:
        values = f.read()
        values = values.replace("descartesresearch", env["docker_user"])
        # ensure we only run on nodes that we can observe
        values = values.replace(r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}')
        values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
        values = values.replace(r'tag: ""', r'tag: "latest"')
        if exp.autoscaling:
            values = values.replace(r"enabled: false","enabled: true")
            #values = values.replace(r"clientside_loadbalancer: false",r"clientside_loadbalancer: true")
            if exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                values = values.replace(r"targetCPUUtilizationPercentage: 80",r"# targetCPUUtilizationPercentage: 80")
                values = values.replace(r"# targetMemoryUtilizationPercentage: 80",r"targetMemoryUtilizationPercentage: 80")
            elif exp.autoscaling == ScalingExperimentSetting.BOTH:
                values = values.replace(r"# targetMemoryUtilizationPercentage: 80",r"targetMemoryUtilizationPercentage: 80")



    from yaml_patch import patch_yaml
    patch_yaml(values, exp.patches)

    with open(path.join(env["tea_store_path"],"examples","helm","values.yaml"), "w") as f:
        f.write(values)

    #write copy of used values to observations
    with open(path.join(observations,"values.yaml"), "w") as f:
        f.write(values)

    helm_deploy = subprocess.check_output(["helm", "install", "teastore", "-n",exp.namespace,"."], cwd=path.join(env["tea_store_path"],"examples","helm"))
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
        
        with open(path.join(observations,"experiment.json"),"w") as f:
            f.write(exp.createJson(env))
        
        # 5. start workload
        # start resouce tracker
        tracker.start()
        def cancle():
            tracker.stop()
            observations_channel.flush()
            signal.raise_signal(signal.SIGUSR1) # raise signal to stop workload
            print("workload timeout reached.")

        signal.signal(signal.SIGALRM,cancle) 
        
        #MAIN timeout to kill the experiment after 2 min after the workload should be compleated
        signal.alarm(8*env["workload_runtime"] + 120 ) # 8 stages + 2 minutes to deploy and cleanup
        
        # deploy workload on differnt node or localy and wait for workload to be compleated (or timeout)
        if exp.colocated_workload:
            _run_remote_workload(exp,observations)
        else:
           _run_local_workload(exp,observations)
        # stop resource tracker
        tracker.stop()
        observations_channel.flush()
        signal.alarm(0) # cancel alarm

def _run_remote_workload(exp:Experiment,observations:str="data"):
    core = client.CoreV1Api()
    def cancle():
        core.delete_collection_namespaced_pod(namespace=exp.namespace, label_selector="app=loadgenerator",timeout_seconds=0,grace_period_seconds=0)
    signal.signal(signal.SIGUSR1,cancle) 
    
    core.create_namespaced_pod(
        namespace=exp.namespace,
        body=client.V1Pod(
            metadata=client.V1ObjectMeta(
                name="loadgenerator",
                namespace=exp.namespace,
                labels={
                    "app":"loadgenerator"
                }
            ),
            spec=client.V1PodSpec(
                containers=[
                        client.V1Container(
                            name="loadgenerator",
                            image=f"{env['docker_user']}/loadgenerator",
                            env=[
                                client.V1EnvVar(
                                    name="LOADGENERATOR_MAX_DAILY_USERS",
                                    value=str(env['workload_max_users'])
                                ),
                                client.V1EnvVar(
                                    name="LOADGENERATOR_STAGE_DURATION",
                                    value=str(env["workload_runtime"])
                                ),
                                client.V1EnvVar(
                                    name="LOADGENERATOR_USE_CURRENTTIME",
                                    value="n"
                                ),
                                client.V1EnvVar(
                                    name="LOADGENERATOR_ENDPOINT_NAME",
                                    value="Vanilla"
                                ),
                                client.V1EnvVar(
                                    name="LOCUST_HOST",
                                    value=f"http://teastore-webui/tools.descartes.teastore.webui/"
                                ),
                                client.V1EnvVar(
                                    name="LOCUSTFILE",
                                    value=env["workloads"]
                                )
                            ],
                            command=[
                                "sh", "-c",
                                "locust --csv teastore --csv-full-history --headless --only-summary 1>/dev/null 2>erros.log || tar zcf - teastore_stats.csv teastore_failures.csv teastore_stats_history.csv erros.log | base64 -w 0", 
                            ],
                            working_dir="/loadgenerator",
                        )
                    ],
                    # run this on a differnt node
                affinity=client.V1Affinity(
                        node_affinity=client.V1NodeAffinity(
                            required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                                node_selector_terms=[
                                    client.V1NodeSelectorTerm(
                                        match_expressions=[
                                            client.V1NodeSelectorRequirement(
                                                key="scaphandre",
                                                operator="DoesNotExist"
                                            )
                                        ])])),),
                restart_policy="Never",
            )
    ))
    
    w = watch.Watch()
    for event in w.stream(core.list_namespaced_pod, exp.namespace, label_selector="app=loadgenerator",timeout_seconds=env["workload_runtime"]*8 + 60):
        pod = event['object']
        if pod.status.phase == 'Succeeded' or pod.status.phase == 'Completed':
            _download_results("loadgenerator",exp.namespace,observations)
            print("container finished, downloading results")
            w.stop()
        elif pod.status.phase == 'Failed':
            print("worklaod could not be started...",pod)
            w.stop()
    #TODO: deal with still running workloads    

    core.delete_namespaced_pod(name="loadgenerator",namespace=exp.namespace)

def _download_results(pod_name:str, namespace:str, destination_path:str):
    try:
        core = client.CoreV1Api()
        resp = core.read_namespaced_pod_log(name=pod_name,namespace=namespace)
        log_contents = resp
        if not log_contents or len(log_contents) == 0:
            print(f"{pod_name} in namespace {namespace} has no logs, workload failed?")
        with TemporaryFile() as tar_buffer:
            tar_buffer.write(base64.b64decode(log_contents))
            tar_buffer.seek(0)
            
            with tarfile.open(fileobj=tar_buffer, mode='r:gz',) as tar:
                tar.extractall(path=destination_path)
    except ApiException as e:
        print(f"failed to get log from pod {pod_name} in namespace {namespace}",e)
    except tarfile.TarError as e:
        print(f"failed to extract log",e,log_contents)

def _run_local_workload(exp:Experiment,observations:str="data"):

    forward = subprocess.Popen(["kubectl","-n",exp.namespace,"port-forward","--address","0.0.0.0","services/teastore-webui",f"{env['local_port']}:80"],stdin=subprocess.PIPE, stderr=subprocess.PIPE)


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
            image=f"{env['docker_user']}/loadgenerator",
            auto_remove=True,
            environment={
                "LOADGENERATOR_MAX_DAILY_USERS":env['workload_max_users'], #The maximum daily users.
                "LOADGENERATOR_STAGE_DURATION":env["workload_runtime"], #The duration of a stage in seconds.
                "LOADGENERATOR_USE_CURRENTTIME":"n", #using current time to drive worload (e.g. day/night cycle)
                "LOADGENERATOR_ENDPOINT_NAME":"Vanilla",#the workload profile
                "LOCUST_HOST":f"http://{env['local_public_ip']}:{env['local_port']}/tools.descartes.teastore.webui", #endoint of the deployed service,
                "LOCUSTFILE":env["workloads"]
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
            os.makedirs(observations,exist_ok=DIRTY)
        except OSError:
            raise RuntimeError("data for this experiment already exsist, skipping")
        
        # 3. rewrite helm values with <env["docker_user"]> && env details as nessary (namespace ...)
        
        deploy_branch(exp,observations)

        # 4. run collection agent (fetch prometeus )
        time.sleep(120) # wait for 120s before stressing the workload
        _run_experiment(exp,observations)
    except RuntimeError as e:
        print(e)
    finally:
        cleanup(exp)

def cleanup(exp:Experiment):
    if exp.autoscaling:
        cleanup_autoscaleing(exp)
    
    if exp.colocated_workload:
        core = client.CoreV1Api()
        try:
            core.delete_namespaced_pod(name="loadgenerator",namespace=exp.namespace)
        except:
            pass
    
    subprocess.run(["helm", "uninstall", "teastore", "-n",exp.namespace])
    subprocess.run(["git","checkout","examples/helm/values.yaml"], cwd=path.join(env["tea_store_path"]))
    subprocess.run(["git","checkout","tools/build_docker.sh"], cwd=path.join(env["tea_store_path"]))

if __name__ == "__main__":
    scale = ScalingExperimentSetting.CPUBOUND

    
    exps = [
        Experiment(name="baseline",target_branch="vanilla",patches=[], namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="jvm",target_branch="jvm-impoove",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="norec",target_branch="feature/norecommendations",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="lessrec",target_branch="feature/lessrecs",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="obs",target_branch="feature/object-storage",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="dbopt",target_branch="feature/db-optimization",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="car",target_branch="Carbon-Aware-Retraining",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
        # Experiment(name="sig",target_branch="ssg+api-gateway",patches=[],namespace="bench",colocated_workload=True,prometheus_url="http://130.149.158.143:30041",autoscaleing=scale),
    ]
    master_env = env.copy()
    for scale in [ScalingExperimentSetting.CPUBOUND, None]:
        
        for exp in exps:
            env = master_env.copy()
            for k,v in exp.env_patches.items():
                env[k] = v 
            
            exp.autoscaling = scale
            if not SKIPBUILD:
                build_workload(exp)
                build_images(exp)
            for i in range(1):
                run_experiment(exp,i)
