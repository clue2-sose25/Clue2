import datetime
from prometheus_api_client import PrometheusConnect
from clue_deployer.src.logger import logger
from threading import Timer
from kubernetes import client, config
import copy 
from queue import Queue


#TODO: make a cluster cunfig class that can be used to configure the tracker, it should allow to specifiy the prometheus url, the k8s api url, the namespaces to track, the update interval, and the queries to use for each metric. 
class NodeUsage:
        _fields = ["instance", "observation_time", "collection_time", "cpu_usage", "memory_usage", "network_usage", "wattage", "num_processes", "wattage_kepler", "wattage_scaph","wattage_auxilary","temperture"]

        def __init__(self, instance):
            self.instance = instance
            self.observation_time = None
            self.collection_time = None
            self.cpu_usage = None
            self.memory_usage = None
            self.network_usage = None
            self.wattage = -1
            self.num_processes = -1
            self.wattage_kepler = None
            self.wattage_scaph = None
            self.wattage_auxilary = None
            self.temp = None
            
    
        def to_dict(self):
            return {
                "instance": self.instance,
                "observation_time": self.observation_time,
                "collection_time": self.collection_time,
                "cpu_usage": self.cpu_usage,
                "memory_usage": self.memory_usage,
                "network_usage": self.network_usage,
                "wattage": self.wattage,
                "num_processes": self.num_processes,
                "wattage_kepler": self.wattage_kepler,
                "wattage_scaph": self.wattage_scaph,
                "wattage_auxilary": self.wattage_auxilary,
                "temperture": self.temp
            }

        def __str__(self) -> str:
            return self.to_dict().__str__()

class PodUsage:
    _fields = ["collection_time","observation_time", "name","namespace","cpu_usage", "memory_usage", "network_usage", "instance", "wattage_kepler", "wattage_scaph"]

    def __init__(self):
        self.collection_time = None
        self.observation_time = None
        self.name = None
        self.namespace = None
        self.cpu_usage = None
        self.memory_usage = None
        self.network_usage = None
        self.instance = None
        self.kepler_consumtion = None
        self.scaphandre_consumtion = None

    def to_dict(self):
        return {
            "collection_time": self.collection_time,
            "observation_time": self.observation_time,
            "name": self.name,
            "namespace": self.namespace,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "network_usage": self.network_usage,
            "instance": self.instance,
            "wattage_kepler": self.kepler_consumtion,
            "wattage_scaph": self.scaphandre_consumtion
        }

class RepeatTimer(Timer):

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class ResourceTracker:

    def __init__(self, 
                 prometheus_url :str , 
                 node_channel:Queue, 
                 pod_channel:Queue,
                 namespaces=["default"], 
                 interval=30,
                 ):
        

        self.sumby = "instance" # or node

        self.prometheus_url = prometheus_url
        if self.prometheus_url:
            self.prm = PrometheusConnect(url=self.prometheus_url, disable_ssl=True)
            if not self.prm.check_prometheus_connection():
                raise ValueError("Could not connect to Prometheus.")
            self.node_channel = node_channel
            self.pod_channel = pod_channel
            self.UPDATE_INTERVAL = interval
            self.timer = RepeatTimer(interval, self.update)
            self.namespaces = namespaces
            self.initialize_and_validate_metrics()

            try:
                config.load_incluster_config()
            except Exception as e:
                config.load_kube_config()
            self.k8s_api_client = client.CoreV1Api()
            logger.info("Resource Tracker initialized.")
        else:
            self.prm = None
            logger.error(f"No prometheus_url provided. {self.__class__.__name__} will be inactive.")


    def initialize_and_validate_metrics(self):
        available = set(self.prm.all_metrics())

        #check node_exporter metrics - cpu/memory
        required = {"node_memory_MemFree_bytes", "node_memory_MemTotal_bytes", "node_cpu_seconds_total","node_memory_Cached_bytes", "kepler_container_joules_total", 
                    "node_network_receive_bytes_total", "node_network_transmit_bytes_total", "container_cpu_usage_seconds_total", "container_memory_working_set_bytes"}
        
        if not required.issubset(available):
            raise ValueError("Prometheus does not provide the required metrics.")

        #check if prometheus is managing a kubernetes cluster on container or node level
        if "container_network_transmit_bytes_total" in available:
            self.network_metric = "container_network"
        elif "node_network_transmit_bytes_total" in available:
            self.network_metric = "node_network"
        else:
            raise ValueError("Prometheus does not provide a vaild network metric.")
        
        if "kube_node_info" in available:
            info = self.prm.get_current_metric_value("kube_node_info")
            self.node_map = dict(map(lambda x: (x["internal_ip"], x["node"]), map(lambda x: x["metric"], info)))
        else:
            self.node_map = {}

    def update(self):
        try:
            self.track()
        except Exception as e:
            logger.error("Error while updating resource tracker: " + str(e))

    def fetch_pods(self):
        pods = {}
        for namespace in self.namespaces:
            pods_request = self.k8s_api_client.list_namespaced_pod(namespace)
            for pod in pods_request.items:
                uid = pod.metadata.uid
                uid = uid[uid.rindex("-")+1:]
                pods[uid] = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "ip": pod.status.pod_ip,
                    "containers" : []
                }
                
                if pod.status.container_statuses is None:
                    logger.warning("error in pod %s, status %s", pod.metadata.name, pod.status)
                    continue

                for c in pod.status.container_statuses:
                    if c.container_id is None:
                        logger.debug(f"found container {c.name} without container_id. Skipping.")
                        continue
                    if not c.started:
                        continue
                    cid = c.container_id.split("//")[1]
                    pods[uid]["containers"].append({
                        "name": c.name,
                        "id":c.container_id,
                        "cid":cid
                    })
                    #prepare fast lookup
                    pods[cid] = pods[uid]

            logger.debug(f"found {len(pods)} pods")
        return pods

    def _query_nodes(self):
        memory = f"sum by ({self.sumby}) ((1 - ((avg_over_time(node_memory_MemFree_bytes[1m]) + avg_over_time(node_memory_Cached_bytes[1m]) + avg_over_time(node_memory_Buffers_bytes[1m])) / avg_over_time(node_memory_MemTotal_bytes[1m]))))" # Memory usage ratio (0 - 1) percentaage
        cpu = f"sum by ({self.sumby}) (rate(node_cpu_seconds_total{{mode!=\"idle\"}}[1m]))" # CPU seconds ratio (1 ~ 1 full core used)
        network = f"sum by ({self.sumby}) (rate(node_network_receive_bytes_total[1m])+rate(node_network_transmit_bytes_total[1m]))/1e6" # MB/s
        kepler = f"sum by ({self.sumby}) (irate(kepler_node_core_joules_total[60s])) + sum by ({self.sumby}) (irate(kepler_node_uncore_joules_total[60s])) +sum by ({self.sumby}) (irate(kepler_node_package_joules_total[60s])) + sum by ({self.sumby}) (irate(kepler_node_dram_joules_total[60s]))" # Watt
        scaphandre = f"sum by ({self.sumby}) (scaph_host_power_microwatts/1e6)" # Watt
        tapo = f"tapo_total_wattage"
        pods = f"sum by ({self.sumby}) (kubelet_working_pods)"
        auxilary_wattage = f"sum by ({self.sumby}) (scaph_process_power_consumption_microwatts{{container_id=\"\"}} > 0)/1e6"
        temp = f"max by ({self.sumby}) (node_thermal_zone_temp)"

        mem_result = self.get_node_metrics(self.prm.custom_query(memory))
        cpu_result = self.get_node_metrics(self.prm.custom_query(cpu))
        network_result = self.get_node_metrics(self.prm.custom_query(network))
        kepler_result = self.get_node_metrics(self.prm.custom_query(kepler))
        scaphandre_result = self.get_node_metrics(self.prm.custom_query(scaphandre))
        tapo_result = self.get_node_metrics(self.prm.custom_query(tapo))
        pods_result = self.get_node_metrics(self.prm.custom_query(pods))
        auxilary_wattage_result = self.get_node_metrics(self.prm.custom_query(auxilary_wattage))
        temp_result = self.get_node_metrics(self.prm.custom_query(temp))

        nodes = []
        keys = set().union(mem_result.keys(), cpu_result.keys(), network_result.keys(), kepler_result.keys(), scaphandre_result.keys(), tapo_result.keys(), temp_result.keys())
        for node in keys:
            n = NodeUsage(node)
            n.collection_time = datetime.datetime.now().replace(microsecond=0)
            n.cpu_usage = cpu_result.get(node, {"value":0})["value"]
            n.memory_usage = mem_result.get(node, {"value":0})["value"]
            n.network_usage = network_result.get(node, {"value":0})["value"]
            n.wattage_kepler = kepler_result.get(node, {"value":0})["value"]
            n.wattage_scaph = scaphandre_result.get(node, {"value":0})["value"]
            n.wattage_auxilary = auxilary_wattage_result.get(node, {"value":0})["value"]
            n.wattage = tapo_result.get(node, {"value":0})["value"]
            n.observation_time = cpu_result.get(node, {"timestamp":None})["timestamp"]
            if n.observation_time is None:
                continue
            n.observation_time = n.observation_time.replace(microsecond=0)
            
            n.num_processes = pods_result.get(node, {"value":0})["value"]
            n.temp = temp_result.get(node, {"value":0})["value"]

            nodes.append(n)

        return nodes

    def _query_pods(self, namespace:str, pod_index = {}):
        """
        Query Prometheus for the current resource usage of pods. Assuming kepler and scaphandre are availible as well as kube metrics.
        """
        kepler_consumtion = f'sum by (pod_name, node) (irate(kepler_container_package_joules_total{{container_namespace="{namespace}"}}[1m])) + sum by (pod_name, node)  (irate(kepler_container_core_joules_total{{container_namespace="{namespace}"}}[1m])) + sum by (pod_name, node)  (irate(kepler_container_dram_joules_total{{container_namespace="{namespace}"}}[1m]))'#f'sum by (pod_name, node) (irate(kepler_container_joules_total{{container_namespace="{namespace}"}}[1m]))'
        scraphandre_consumtion = f'sum by (container_id, node) (scaph_process_power_consumption_microwatts/1e6)'
        
        # cpu_pod = f'sum by (pod, instance) (irate(container_cpu_usage_seconds_total{{namespace="{namespace}", container!=""}}[1m]))'
        # memory_pod = f'avg by (pod,instance) (container_memory_working_set_bytes{{namespace="{namespace}", container!=""}}/ 1e6)'
        cpu_pod = f'sum by (pod, instance) (irate(container_cpu_usage_seconds_total{{namespace="{namespace}"}}[1m]))'
        memory_pod = f'avg by (pod,instance) (container_memory_working_set_bytes{{namespace="{namespace}"}}/ 1e6)'
        network_pod = f'sum by (pod, instance) (rate(container_network_transmit_bytes_total{{pod!="",namespace="{namespace}"}}[1m]) + rate(container_network_receive_bytes_total{{pod!="",namespace="{namespace}"}}[1m]))/1e6 '
        
        cpu_pod_result = self.get_pod_metrics(self.prm.custom_query(cpu_pod))
        memory_pod_result = self.get_pod_metrics(self.prm.custom_query(memory_pod))
        network_pod_result = self.get_pod_metrics(self.prm.custom_query(network_pod))
        kepler_consumption_result = self.get_pod_metrics(self.prm.custom_query(kepler_consumtion),instance_name="node", pod_name="pod_name")
        scaphandre_consumption_result = self.get_scaphandre_metrics(self.prm.custom_query(scraphandre_consumtion), pod_index)

        pods = []
        keys = set().union(scaphandre_consumption_result.keys(), kepler_consumption_result.keys(), cpu_pod_result.keys(), memory_pod_result.keys())
        
        # helper function to get the value from the result
        def get_value(key, result):
            val = result.get(key, {"value":0.0, "timestamp":datetime.datetime.now(), "instance":"unknown"})
            return val
        
        for process in keys:
            pod = PodUsage()
            pod.collection_time = datetime.datetime.now().replace(microsecond=0)
            pod.name = process
            pod.namespace = namespace
            
            cpu = get_value(process, cpu_pod_result)
            memory = get_value(process, memory_pod_result)
            kepler = get_value(process, kepler_consumption_result)
            scaphandre = get_value(process, scaphandre_consumption_result)
            
            pod.cpu_usage = float(cpu["value"])
            pod.memory_usage =  float(memory["value"])
            pod.kepler_consumtion =  float(kepler["value"])
            pod.scaphandre_consumtion =  float(scaphandre["value"])
            pod.network_usage = get_value(process, network_pod_result)["value"]
            # XXX warining assumtion instance is the same for all metrics
            instance = set([cpu["instance"], memory["instance"], kepler["instance"], scaphandre["instance"]])
            instance.discard("unknown")
            assert len(instance) == 1, f"Instance mismatch: {instance}"
            pod.instance = instance.pop()
            observation_time = min(cpu["timestamp"], memory["timestamp"], kepler["timestamp"], scaphandre["timestamp"])
            pod.observation_time = observation_time.replace(microsecond=0)
            pods.append(pod)
        return pods

    def get_node_metrics(self, _results):
        results = {}
        for node in _results:

            metric = node['metric']

            if 'node' in metric:
                name = metric['node']
            elif 'instance' in metric:
                name = metric['instance']
            else:
                logger.warning("metric has neither instance nor node info: %s", node)
                continue
            
            # if 'node' not in node['metric']:
            #     name = node['metric']['instance']
            # else :
            #     name = node['metric']['node']
                
            results[name] = {
                "timestamp": datetime.datetime.fromtimestamp(node['value'][0]),
                "value": node['value'][1]
            }
        return results

    def get_pod_metrics(self, _results, instance_name="instance",pod_name="pod"):
        results = {}
        for pod in _results:
            if instance_name not in pod['metric']:
                logger.warning("unknown instance name %s in pod %s", instance_name, pod_name)
                continue 

            results[pod['metric'][pod_name]] = {
                "timestamp":datetime.datetime.fromtimestamp(pod['value'][0]),
                "value":pod['value'][1],
                "instance":pod['metric'][instance_name]
            }
        return results
    
    def get_scaphandre_metrics(self,_results, pod_index={}):
        results = {}
        
        for pod in _results:
            if "container_id" not in pod['metric']:
                continue # not sure what these metrics are ...
            container_id = pod['metric']['container_id']
            if container_id in pod_index:
                pod_name = pod_index[container_id]["name"]
            elif container_id.startswith("cri-containerd-") and container_id[15:] in pod_index:
                pod_name = pod_index[container_id[15:]]["name"]
            else:
                continue
            results[pod_name] = {
                "timestamp":datetime.datetime.fromtimestamp(pod['value'][0]),
                "value":pod['value'][1],
                "instance":pod['metric']['node']
            }
        return results

    def track(self):
        if self.prm:
            pod_index = self.fetch_pods()
            nodes = self._query_nodes()
            for node in nodes:
                self.node_channel.put(node)
                
            pods = []
            for namespace in self.namespaces:
                pods = pods + self._query_pods(namespace, pod_index)

            #insert the data
            for p in pods:
                self.pod_channel.put(p)

    def start(self):
        if self.prm:
            logger.debug("Starting resource tracker.")
            self.timer.start()

    def stop(self):
        if self.prm:
            logger.debug("Stopping resource tracker.")
            self.timer.cancel()


class FixedQueue(Queue):
    """
    A fixed size queue that removes the oldest item when a new one is added if the queue is full.
    """
    def __init__(self, size):
        super().__init__()
        self.maxsize = size

    def put(self, item):
        if super().full():
            super().get_nowait()
        super().put(item)

    def take(self, n):
        for _ in range(n):
            yield super().get()

    def elements(self):
        return copy.deepcopy(self.queue)
