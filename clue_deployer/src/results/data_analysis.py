import seaborn as sns # type: ignore
import pandas as pd# type: ignore
import matplotlib.pyplot as plt # type: ignore
import glasbey # type: ignore
import numpy as np # type: ignore
import warnings
import yaml # type: ignore
from clue_deployer.src.results.experiment_results import ExperimentResults
import pandas as pd # type: ignore
import dash # type: ignore
from dash import dcc, html, Input, Output, dash_table # type: ignore
import plotly.express as px # type: ignore
from datetime import time
from clue_deployer.src.logger import logger

class DataAnalysis:
    #Settings for plotting
    aggregation_maps = {
        "stats_history_aggregated": {
            "user_count": "sum",
            "rq_s": "mean",
            "frq_s": "mean",
            "rq": "sum",
            "frq": "sum",
            "mean_rsp_time": "mean",
            "mean_resp_size": "mean",
            "p50": "mean",
            "p90": "mean",
            "p95": "mean",
            "p99": "mean",
            "p999": "mean"
        },
        "pods": {
            "cpu_usage": "mean",
            "memory_usage": "mean",
            "network_usage": "mean",
            "wattage_kepler": "mean",
            "wattage_scaph": "mean"
        },
        "stats": {
            "Request Count": "sum",
            "Failure Count": "sum",
            "Median Response Time": "mean",
            "Average Response Time": "mean",
            "Min Response Time": "min",
            "Max Response Time": "max",
            "Average Content Size": "mean",
            "Requests/s": "mean",
            "Failures/s": "mean",
            "50%": "mean",
            "66%": "mean",
            "75%": "mean",
            "80%": "mean",
            "90%": "mean",
            "95%": "mean",
            "98%": "mean",
            "99%": "mean",
            "99.9%": "mean",
            "99.99%": "mean",
            "100%": "mean"
        },
        "nodes": {
            "cpu_usage": "mean",
            "memory_usage": "mean",
            "network_usage": "mean",
            "wattage": "mean",
            "num_processes": "mean",
            "wattage_kepler": "mean",
            "wattage_scaph": "mean",
            "wattage_auxilary": "mean",
            "temperture": "mean",
            "wattage_estimation": "mean"
        },
        "pods_energy": {
            "wattage_kepler": "mean",
            "wattage_scaph": "mean",
            "cpu_usage": "mean",
            "memory_usage": "mean",
            "wattage_kepler_avg": "mean",
            "wattage_scaph_avg": "mean",
            "cpu_usage_avg": "mean",
            "memory_usage_avg": "mean"
        },
        "run_stats": {
            "Request Count": "sum",
            "Failure Count": "sum",
            "Success Count": "sum",
            "reliability": "mean",
            "run_time": "mean",
            "total_rps": "mean",
            "success_rps": "mean"
        }
    }


    warnings.filterwarnings('ignore')
    pd.set_option('display.max_columns', None)
    sns.set_theme(rc={'figure.figsize':(12, 6)})
    sns.set_context("paper")
    sns.set_style("whitegrid")

    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42

    palette = glasbey.create_block_palette(
        [4, 3, 3, 2, 2],
        colorblind_safe=True,
        cvd_severity=90
    )
    sns.set_palette(palette)

    # Environment configuration and constants
    ws_price = 0.5 / 3_600_000 # based on germany mean kWh price
    # AWS cost-model
    serverless_price = 0.0000166667  # based on aws lambda price per GB-s  (frankfurt)
    memory_second_price = 0.00511 / 1024 / 60 # $/MBs based on AWS nfragate memory price per hour (frankfurt)
    vCPU_second_price = 0.04656 / 60 # $/vCPU based on AWS nfragate memory price per hour (frankfurt)

    
    
    def __init__(self, experiment_folder:str, config_file_path:str, load_data_from_file:False):
        #yaml_dict = parse_sut_yaml(config_file_path)
        #self.general_allowance = {entry["service_name"]: entry["limit"] for entry in yaml_dict["resource_limits"]}
        #self.pod_configuration = {entry["service_name"]: entry["limit"] for entry in yaml_dict["resource_limits"]}
        self.service_pods = [] #TODO
        #self.sut = yaml_dict['sut']
        #self.namespace = yaml_dict['namespace']
        self.sut="teastore"
        self.general_allowanc = {
                "teastore-recommender": {"cpu": 2600, "memory": 1332},
                "teastore-webui": {"cpu": 1300, "memory": 1950},
                "teastore-image": {"cpu": 1300, "memory": 1950},
                "teastore-auth": {"cpu": 585, "memory": 1332},
                'teastore-registry':{"cpu": 1300, "memory": 1332}, 
                'teastore-persistence':{"cpu": 1300, "memory": 1332}, 
                'teastore-db':{"cpu": 1300, "memory": 1332},
                "teastore-all": {"cpu":1950, "memory":2663},
                "auth": {"cpu": 500, "memory": 500},
            }
        self.namespace = "tea-bench"
        self.pod_configuration = {
                "teastore-recommender": {"cpu": 2600, "memory": 1332},
                "teastore-webui": {"cpu": 1300, "memory": 1950},
                "teastore-image": {"cpu": 1300, "memory": 1950},
                "teastore-auth": {"cpu": 585, "memory": 1332},
                'teastore-registry':{"cpu": 1000, "memory": 1024}, # not set by default ....
                'teastore-persistence':{"cpu": 1000, "memory": 1024}, # not set by default ....
                'teastore-db':{"cpu": 1000, "memory": 1024}, # not set by default ....
                "teastore-all": {"cpu":1950, "memory":2663},
                "auth": {"cpu": 500, "memory": 500},
            }
        self.node_model = {
            "sm-gpu": 32704316//1024,
            "ise-knode6": 32719632//1024,
            "ise-knode1": 32761604//1024,
        }
        self.resouce_scale = {
            "baseline_vanilla_full": {
                'teastore-recommender':3,
                'teastore-webui':3,
                'teastore-image':3,
                'teastore-auth':3,
                'teastore-registry':1,
                'teastore-persistence':1,
                'teastore-db':1,
                "teastore-all":0,
                "auth":0,
            },
            'jvm_jvm-impoove_full': {
                'teastore-recommender':3,
                'teastore-webui':3,
                'teastore-image':3,
                'teastore-auth':3,
                'teastore-registry':1,
                'teastore-persistence':1,
                'teastore-db':1,
                "teastore-all":0,
                "auth":0,
            },
            'monolith_feature_monolith_full': {
                'teastore-recommender':0,
                'teastore-webui':0,
                'teastore-image':0,
                'teastore-auth':0,
                'teastore-registry':1,
                'teastore-persistence':0,
                'teastore-db':1,
                "teastore-all":3,
                "auth":0,
            },
            'norec_feature_norecommendations_full' : {
                'teastore-recommender':0,
                'teastore-webui':3,
                'teastore-image':3,
                'teastore-auth':3,
                'teastore-registry':1,
                'teastore-persistence':1,
                'teastore-db':1,
                "teastore-all":0,
                "auth":0,
            },
            'obs_feature_object-storage_full' : {
                'teastore-recommender':3,
                'teastore-webui':3,
                'teastore-image':3,
                'teastore-auth':3,
                'teastore-registry':1,
                'teastore-persistence':1,
                'teastore-db':1,
                "teastore-all":0,
                "auth":0,
            },
            'serverless_feature_serverless_full' : {
                'teastore-recommender':3,
                'teastore-webui':3,
                'teastore-image':3,
                'teastore-auth':0,
                'teastore-registry':1,
                'teastore-persistence':1,
                'teastore-db':1,
                "teastore-all":0,
                "auth":40, # infinite theorethical, we use the maximum possible on the nodes we use (12+8 cores) -> 40 functions fit
            },
            'serverless_incl_knative' : {
                'teastore-recommender':3,
                'teastore-webui':3,
                'teastore-image':3,
                'teastore-auth':0,
                'teastore-registry':1,
                'teastore-persistence':1,
                'teastore-db':1,
                "teastore-all":0,
                "auth":40, # infinite theorethical, we use the maximum possible on the nodes we use (12+8 cores) -> 40 functions fit
            },
        }

        if load_data_from_file: #TODO: Make data_file dynamic
            #self.stats_history_aggregated_data = pd.read_hdf(f"{experiment_folder}/observation_original.hdf5", key="stats_history_aggregated")
            #self.pods_data = pd.read_hdf(f"{experiment_folder}/observation_original.hdf5", key="pods")
            #self.stats_data = pd.read_hdf(f"{experiment_folder}/observation_original.hdf5", key="stats")
            #self.nodes_data = pd.read_hdf(f"{experiment_folder}/observation_original.hdf5", key="nodes")
            #self.pods_energy_data = pd.read_hdf(f"{experiment_folder}/observation_original.hdf5", key="pods_energy")
            #self.run_stats_data = pd.read_hdf(f"{experiment_folder}/observation_original.hdf5", key="run_stats")
            self.stats_history_aggregated_data = pd.read_hdf(f"clue_deployer/src/results/observation_original.hdf5", key="stats_history_aggregated")
            self.pods_data = pd.read_hdf(f"clue_deployer/src/results/observation_original.hdf5", key="pods")
            self.stats_data = pd.read_hdf(f"clue_deployer/src/results/observation_original.hdf5", key="stats")
            self.nodes_data = pd.read_hdf(f"clue_deployer/src/results/observation_original.hdf5", key="nodes")
            self.pods_energy_data = pd.read_hdf(f"clue_deployer/src/results/observation_original.hdf5", key="pods_energy")
            self.run_stats_data = pd.read_hdf(f"clue_deployer/src/results/observation_original.hdf5", key="run_stats")
        else:
            exr = ExperimentResults(experiment_folder, load_stats_history=True, sut=self.sut, remove_outliers=True)
            self.stats_history_aggregated_data = exr.stats_history_aggregated_data
            self.pods_data = exr.pods
            self.stats_data = exr.stats
            self.nodes_data = exr.nodes
            self.pods_energy_data = exr.pods_energy
            self.run_stats_data = exr.run_stats

    def create_metrics(self):
        failures = self.get_failures()
        latency = self.get_latency()
        pod_usage = self.get_pod_usage()
        mean_costs = self.get_mean_costs(pod_usage)
        real_utilization = self.get_real_utilization(self.pods_data)
        run_time_overhead = self.get_run_time_overhead_costs(self.pods_data)
        json_data = self.groupby(["exp_branch", "exp_workload"]
            )["run_iteration"].nunique().reset_index(name="num_iterations")
        json_data = json_data.merge(latency).merge(failures).merge(DataAnalysis.runtime_overhead_cost).merge(DataAnalysis.real_total_utilization)

    def generate_basic_plots(self):
        pass

    def save_json(json_data, exp_branch, exp_workload, save_path):
        json_data[(json_data["exp_branch"] == exp_branch) & (json_data["exp_workload"] == exp_workload)].to_json(
            f"{save_path}/metrics.json", orient='records', lines=True)
        print(f"✅ JSON saved to {save_path}/metrics.json")

    def parse_sut_yaml(yaml_path):
        """
        Parses a SUT YAML file and extracts specific fields.

        Args:
            yaml_path (str): Path to the YAML file.

        Returns:
            dict: Extracted fields:
                - default_resource_limits
                - resource_limits
                - namespace
                - sut
                - workloads
        """
        with open(yaml_path, "r") as f:
            content = yaml.safe_load(f)

        return {
            "default_resource_limits": content.get("config").get("default_resource_limits"),
            "resource_limits": content.get("resource_limits"),
            "namespace": content.get("config").get("namespace"),
            "sut": content.get("config").get("sut"),
            #"workloads": content.get("workloads")
        }

    def split_by_branch_and_workload_named(**named_dfs):
        """
        Teilt benannte DataFrames nach eindeutigen Kombinationen von (exp_branch, exp_workload),
        überspringt DataFrames, die diese Spalten nicht enthalten.

        Args:
            **named_dfs: Beliebig viele benannte DataFrames, z. B. df1=df1, df2=df2

        Returns:
            dict: {(branch, workload): [df1_part, df2_part, ...]} – gleiche Reihenfolge wie Eingabe
        """
        result = {}
        valid_dfs = {}
        required_cols = {"exp_branch", "exp_workload"}
        for name, df in named_dfs.items():
            if required_cols.issubset(df.columns):
                df = df.copy()
                df["__source_name"] = name
                valid_dfs[name] = df
            else:
                print(f"⚠️ DataFrame '{name}' übersprungen – mindestens eine der Spalten fehlt: {required_cols}.")

        if not valid_dfs:
            print("❌ Kein gültiger DataFrame vorhanden.")
            return {}

        # Schlüssel aus erstem gültigen DataFrame
        first_df = next(iter(valid_dfs.values()))
        keys = first_df[["exp_branch", "exp_workload"]].drop_duplicates()

        for _, row in keys.iterrows():
            branch = row["exp_branch"]
            workload = row["exp_workload"]
            filtered_parts = [
                df[(df["exp_branch"] == branch) & (df["exp_workload"] == workload)]
                for df in valid_dfs.values()
            ]
            result[(branch, workload)] = filtered_parts

        return result

    def get_failures(self):
        left = "exp_scale_pausing"
        right = "exp_scale_rampup"
        failures = self.stats_history_aggregated_data.groupby(["exp_branch", "exp_workload"])[["rq", "frq"]].sum().reset_index()
        failures["Failure Rate"] = 100 * failures["frq"] / failures["rq"]
        return failures

    def get_latency(self):
        latency = (self.stats_history_aggregated_data.groupby(["exp_branch", "exp_workload"])[["p50", "p95"]].mean().reset_index())
        return latency

    def calc_request_based_billing(self, row):
        if row["type"] == "pod" and row["type"] in self.pod_configuration.keys():
            conf = self.pod_configuration[row["pod_name"]]
            return conf["memory"] * DataAnalysis.memory_second_price + np.ceil(conf["cpu"] / 1000) * DataAnalysis.vCPU_second_price
        elif row["type"] == "function":
            return 500 * DataAnalysis.serverless_price

    def calc_usage_based_billing(self, row):
        if row["type"] == "pod":
            return row["memory_usage"] * DataAnalysis.memory_second_price + np.ceil(row["cpu_usage"]) * DataAnalysis.vCPU_second_price
        elif row["type"] == "function":
            return row["memory_usage"] * DataAnalysis.serverless_price

    def get_pods_usage(self, namespace:str):
        pods = self.pods_data[self.pods_data["namespace"] == namespace]
        pods["pod_name"] = pods["name"].apply(lambda x: "-".join(x.split("-")[0:2]))

        #TODO: Find a way to generalize this
        #pods["type"] = pods["pod_name"].apply(
        #    lambda x: "pod" if x.startswith("teastore") else "function" if x.startswith("auth") else "infra")
        # ignore infra pods for now
        #pods = pods[pods["type"].isin(["pod", "function"])]
        pods_usage = pods.groupby(DataAnalysis.run_vars + ["run_time", "name", "pod_name", "type"])[
            ["memory_usage", "cpu_usage"]].sum().reset_index()

        pods_usage["requested_cost"] = pods_usage.apply(self.calc_request_based_billing, axis=1)
        pods_usage["used_cost"] = pods_usage.apply(self.calc_usage_based_billing, axis=1)

        return pods_usage



    def get_mean_costs(self, pods_usage):
        pods_mean_cost = pods_usage.groupby(DataAnalysis.run_vars)[["requested_cost", "used_cost"]].sum().reset_index().groupby(
            ["exp_branch", "exp_workload"])[["requested_cost", "used_cost"]].mean().reset_index()

        requests = self.stats_data.groupby(["exp_branch", "exp_workload"])[
            ["Request Count", "Failure Count"]].sum().reset_index()  # total request count
        requests["rq"] = requests["Request Count"] - requests["Failure Count"]

        pods_mean_cost_per_request = pods_mean_cost.merge(requests[["exp_branch", "exp_workload", "rq"]],
                                                          on=["exp_branch", "exp_workload"])
        pods_mean_cost_per_request["requested_cost_per_r"] = (pods_mean_cost_per_request["requested_cost"] /
                                                              pods_mean_cost_per_request[
                                                                  "rq"]) * 100 * 1000  # convert to mili cents
        pods_mean_cost_per_request["used_cost_per_r"] = (pods_mean_cost_per_request["used_cost"] /
                                                         pods_mean_cost_per_request[
                                                             "rq"]) * 100 * 1000  # convert to mili cents
        return pods_mean_cost_per_request

    def calculate_maximum_resource_allowance(self, exp_branch: str):
        scale = self.resouce_scale[exp_branch]
        max_allowance = {
            "cpu": 0,
            "memory": 0
        }
        for pod_name, pod_scale in scale.items():
            for resource, value in self.general_allowance[pod_name].items():
                max_allowance[resource] += value * pod_scale
        return max_allowance

    def calulate_resouce_allowence(self, row):
        if not row["type"] in self.general_allowance.keys() and not row["type"].startswith("auth"):
            return row
        else: #TODO: find way to generalize this
            if row["type"].startswith("auth"):
                cpu = self.general_allowance["auth"]["cpu"]
                memory = self.general_allowance["auth"]["memory"]
                max_count = self.resouce_scale[row["exp_branch"]]["auth"]
            else:
                cpu = self.general_allowance[row["type"]]["cpu"]
                memory = self.general_allowance[row["type"]]["memory"]
                max_count = self.resouce_scale[row["exp_branch"]][row["type"]]
            row["cpu_limit"] = cpu * row["count"]
            row["mem_limit"] = memory * row["count"]
            row["cpu_max"] = cpu * max_count
            row["mem_max"] = memory * max_count
        return row
    
    def get_real_utilization(self, pods):
        pods["type"] = pods["name"].apply(lambda x: "-".join(x.split("-")[0:2]))
        pod_scale_behavior = pods.groupby(DataAnalysis.run_vars + ["run_time", "type"])["type"].count().reset_index(name="count")

        pod_resouce_utilization = pod_scale_behavior.apply(self.calulate_resouce_allowence, axis=1)

        real_pod_utilization = pods.groupby(DataAnalysis.run_vars + ["run_time", "type"])[["cpu_usage", "memory_usage"]].sum()
        real_pod_utilization["r_cpu_usage"] = (real_pod_utilization["cpu_usage"] * 1000).astype(int)
        real_pod_utilization["r_memory_usage"] = real_pod_utilization["memory_usage"].astype(int)
        real_pod_utilization.reset_index()

        real_total_utilization = \
        pod_resouce_utilization.merge(real_pod_utilization, on=DataAnalysis.run_vars + ["run_time", "type"]).groupby(
            ["exp_branch", "exp_workload"])[
            ["r_cpu_usage", "r_memory_usage", "cpu_limit", "mem_limit", "cpu_max", "mem_max"]].sum()
        real_total_utilization["r_cpu_utilization"] = 100 * real_total_utilization["r_cpu_usage"] / \
                                                      real_total_utilization["cpu_max"]
        real_total_utilization["r_mem_utilization"] = 100 * real_total_utilization["r_memory_usage"] / \
                                                      real_total_utilization["mem_max"]
        real_total_utilization["t_cpu_utilization"] = 100 * real_total_utilization["cpu_limit"] / \
                                                      real_total_utilization["cpu_max"]
        real_total_utilization["t_mem_utilization"] = 100 * real_total_utilization["mem_limit"] / \
                                                      real_total_utilization["mem_max"]
        real_total_utilization["cpu_utilization"] = 100 * real_total_utilization["r_cpu_usage"] / \
                                                    real_total_utilization["cpu_limit"]
        real_total_utilization["mem_utilization"] = 100 * real_total_utilization["r_memory_usage"] / \
                                                    real_total_utilization["mem_limit"]
        real_total_utilization.reset_index(inplace=True)
        return real_total_utilization

    def calculate_cost(row):
        # meory * cpu_seconds * price_per_memory_second + wattage * kwh_price
        return row['memory_usage'] * DataAnalysis.memory_second_price + np.ceil(row["cpu_usage"]) * DataAnalysis.vCPU_second_price + (
                    row["wattage_kepler"] * DataAnalysis.ws_price)

    def calculate_memory_usage(self, row):
        return row['memory_usage'] * self.node_model[row['instance']]

    def get_runtime_overhead_costs(self, nodes):
        nodes = self.nodes_data[(self.nodes_data['instance'].isin(self.pods_data['instance'].unique()))].copy()
    
        nodes["memory_usage"] = nodes.apply(self.calculate_memory_usage, axis=1)
    
        # We calculate the cpu_seconds memory (MB) and wattage used per second for each node ... 
    
        nodes = nodes.groupby(DataAnalysis.run_vars + ['run_time', 'instance'])[
            ["cpu_usage", "memory_usage", "wattage_kepler", "wattage_scaph"]].sum()
        nodes['cost'] = nodes.apply(self.calculate_cost, axis=1)
    
        pods = self.pods_data.copy()
    
        pods = pods.groupby(DataAnalysis.run_vars + ['run_time', 'instance'])[
            ["cpu_usage", "memory_usage", "wattage_kepler", "wattage_scaph"]].sum()
    
        # ... and calculate the runtime overhead by removing the total pod usage from the node usage
        # we assume that the worklaod generator run on a separate node outside of the pod nodes
        runtime_overhead_data = (nodes - pods)
        runtime_overhead_data['cost'] = runtime_overhead_data.apply(self.calculate_cost, axis=1)
    
        runtime_overhead_cost = 100 * runtime_overhead_data.groupby(["exp_workload", "exp_branch"])[["cost"]].sum() / \
                                nodes.groupby(["exp_workload", "exp_branch"])[["cost"]].sum()
        runtime_overhead_cost.reset_index(inplace=True)
        return runtime_overhead_cost

    def calulate_resouce_allowence_for_cost(self, row):
        if row["service"] in self.pod_configuration.keys():
            row["cpu_limit"] = self.pod_configuration[row["service"]]["cpu"]
            row["mem_limit"] = self.pod_configuration[row["service"]]["memory"]
            return row
        else:
            row["cpu_limit"] = self.general_allowance['cpu']
            row["mem_limit"] = self.general_allowance['memory']
            return row
    
    def get_pod_scale(self):
        pods = self.pods_data.copy()
        pods["type"] = pods["pod_name"].apply(
            lambda x: "pod" if x in self.service_pods else "infra")
        pods = pods[pods["type"] != "infra"]
        pods["service"] = pods["pod_name"].apply(lambda x: "-".join(x.split("-")[0:2]))
        pods["service"].unique()
        pods.set_index("run_time")

        pods_scale = pods.groupby(["exp_branch", "exp_workload", "run_iteration", "run_time", "service"])[
            "name"].count().reset_index()
        
        pods = pods.apply(self.calulate_resouce_allowence_for_cost, axis=1, result_type="expand")

        pods["mem_utilization"] = 100 * pods["memory_usage"] / pods["mem_limit"]
        pods["cpu_utilization"] = 100 * (1000 * pods["cpu_usage"]) / pods["cpu_limit"]

        pods["under_utilized"] = 1
        pods.loc[(pods["mem_utilization"] < 49) & (pods["cpu_utilization"] < 49), "under_utilized"] = 0

        pods["over_utilized"] = 1
        pods.loc[(pods["mem_utilization"] > 90) | (pods["cpu_utilization"] > 90), "over_utilized"] = 0

        pod_scaling_behavior = pods.groupby(["exp_branch", "exp_workload", "run_iteration"] + ["service", "run_time"])[
            ["under_utilized", "over_utilized", "wattage_kepler"]].agg(["sum", "count"])
        service_utilization = pod_scaling_behavior
        service_utilization["under"] = service_utilization[("under_utilized", "count")] - service_utilization[
            ("under_utilized", "sum")]
        service_utilization["over"] = service_utilization[("over_utilized", "count")] - service_utilization[
            ("over_utilized", "sum")]
        service_utilization["count"] = service_utilization[("over_utilized", "count")]
        service_utilization.loc[(service_utilization["count"] == 1) & (service_utilization["under"] == 1), "under"] = 0
        service_utilization.loc[(service_utilization["count"] == 3) & (service_utilization["over"] == 3), "over"] = 0
        service_utilization.loc[(service_utilization["under"] > 0), "waste"] = service_utilization[
            ("wattage_kepler", "sum")]

        service_utilization.columns = service_utilization.columns.droplevel(1)
        service_utilization = service_utilization.reset_index()[
            ["exp_branch", "exp_workload", "run_iteration", "service", "run_time", "under", "over", "count", "waste"]]

        melt_service_utilization = service_utilization.melt(
            id_vars=["exp_branch", "exp_workload", "run_iteration"] + ["service", "run_time"],
            value_vars=["under", "over"])

        service_utilization_error = melt_service_utilization[melt_service_utilization["value"] > 0].groupby(
            ["exp_branch", "exp_workload", "run_time"])["value"].sum().reset_index()

        scaling_error = melt_service_utilization.groupby(["exp_branch", "exp_workload"])["value"].sum().reset_index()

        scaling_waste = service_utilization.groupby(["exp_branch", "exp_workload"])["waste"].sum().reset_index()
        scaling_error

    def create_server(self):
        
        # Load and copy data
        df = self.pods_data.copy()

        plot_columns = ["cpu_usage", "wattage_kepler", "network_usage", "memory_usage", "pod_name", "observation_time"]
        group_columns = ["None", "run_iteration", "instance", "pod_name", "exp_branch", "exp_workload"]
        agg_options = ["mean", "median", "min", "max", "sum"]

        app = dash.Dash(__name__)
        app.title = "Pods Data Explorer"

        app.layout = html.Div([
            html.H2("Pods Data Analysis"),

            html.Div([
                html.Label("Filter by exp_branch:"),
                dcc.Dropdown(
                    options=[{"label": b, "value": b} for b in sorted(df["exp_branch"].dropna().unique())],
                    id="branch-dropdown",
                    value=None,
                    clearable=True,
                )
            ], style={"width": "30%", "display": "inline-block", "margin-right": "2%"}),

            html.Div([
                html.Label("Filter by exp_workload:"),
                dcc.Dropdown(
                    options=[{"label": w, "value": w} for w in sorted(df["exp_workload"].dropna().unique())],
                    id="workload-dropdown",
                    value=None,
                    clearable=True
                )
            ], style={"width": "30%", "display": "inline-block"}),

            html.Hr(),

            html.Div([
                html.Label("Filter Column:"),
                dcc.Dropdown(
                    options=[{"label": col, "value": col} for col in df.columns],
                    id="value-filter-column",
                    placeholder="Select column to filter"
                )
            ], style={"width": "30%", "display": "inline-block", "margin-right": "2%"}),

            html.Div([
                html.Label("Filter Values:"),
                dcc.Dropdown(
                    options=[],
                    id="value-filter-values",
                    multi=True,
                    placeholder="Select values"
                )
            ], style={"width": "40%", "display": "inline-block"}),

            html.Hr(),

            html.Div([
                html.Label("Main Plot Type:"),
                dcc.Dropdown(
                    options=[{"label": t.title(), "value": t} for t in ["scatter", "line", "box", "histogram", "bar"]],
                    id="plot-type",
                    value="scatter"
                )
            ], style={"width": "30%", "display": "inline-block"}),

            html.Div([
                html.Label("Group Plot By:"),
                dcc.Dropdown(
                    options=[{"label": col, "value": col} for col in group_columns],
                    id="group-by",
                    value="instance",
                    clearable=False
                )
            ], style={"width": "30%", "display": "inline-block", "margin-left": "2%"}),

            html.Div([
                html.Label("X-axis:"),
                dcc.Dropdown(
                    options=[{"label": col, "value": col} for col in plot_columns],
                    id="x-axis",
                    value=plot_columns[0]
                )
            ], style={"width": "30%", "display": "inline-block", "margin-right": "2%"}),

            html.Div([
                html.Label("Y-axis:"),
                dcc.Dropdown(
                    options=[{"label": col, "value": col} for col in plot_columns],
                    id="y-axis",
                    value=plot_columns[1]
                )
            ], style={"width": "30%", "display": "inline-block"}),

            dcc.Graph(id="main-plot"),
            html.Div(id="summary-table"),

            html.Hr(),
            html.H3("Compare Multiple exp_branch"),

            html.Div([
                html.Label("Select exp_branch(es):"),
                dcc.Dropdown(
                    options=[{"label": b, "value": b} for b in sorted(df["exp_branch"].dropna().unique())],
                    id="multi-exp-branch",
                    value=[],
                    multi=True
                )
            ], style={"width": "50%"}),

            html.Div([
                html.Label("Comparison Plot Type:"),
                dcc.Dropdown(
                    options=[{"label": t.title(), "value": t} for t in ["line", "scatter", "bar"]],
                    id="compare-plot-type",
                    value="line"
                )
            ], style={"width": "30%", "margin-top": "10px"}),

            html.Div([
                html.Label("Aggregation Function:"),
                dcc.Dropdown(
                    options=[{"label": f.title(), "value": f} for f in agg_options],
                    id="compare-agg-func",
                    value="mean"
                )
            ], style={"width": "30%", "margin-top": "10px"}),

            html.Div([
                html.Label("Y-axis:"),
                dcc.Dropdown(
                    options=[{"label": col, "value": col} for col in plot_columns],
                    id="compare-y",
                    value=plot_columns[1]
                )
            ], style={"width": "30%", "display": "inline-block"}),

            dcc.Graph(id="compare-plot")
        ])

        @app.callback(
            Output("value-filter-values", "options"),
            Input("value-filter-column", "value")
        )
        def update_value_filter_options(selected_col):
            if selected_col and selected_col in df.columns:
                unique_vals = df[selected_col].dropna().unique()
                return [{"label": str(v), "value": v} for v in sorted(unique_vals)]
            return []

        @app.callback(
            dash.Output("main-plot", "figure"),
            dash.Output("summary-table", "children"),
            dash.Input("branch-dropdown", "value"),
            dash.Input("workload-dropdown", "value"),
            dash.Input("plot-type", "value"),
            dash.Input("group-by", "value"),
            dash.Input("x-axis", "value"),
            dash.Input("y-axis", "value"),
            dash.Input("value-filter-column", "value"),
            dash.Input("value-filter-values", "value")
        )
        def update_main_plot(branch, workload, plot_type, group_by, x_col, y_col, filter_col, filter_vals):
            dff = df.copy()
            if branch:
                dff = dff[dff["exp_branch"] == branch]
            if workload:
                dff = dff[dff["exp_workload"] == workload]
            if filter_col and filter_vals:
                dff = dff[dff[filter_col].isin(filter_vals)]
            if x_col == "pod_name": dff[x_col] = dff[x_col].astype(str)
            if y_col == "pod_name": dff[y_col] = dff[y_col].astype(str)
            group = None if group_by == "None" else group_by
            summary = None

            if plot_type == "box":
                fig = px.box(dff, x=x_col, y=y_col, color=group, points="all")
                means = dff.groupby(x_col)[y_col].mean().reset_index()
                fig.add_scatter(x=means[x_col], y=means[y_col], mode="markers", marker=dict(symbol="diamond", size=8, color="black"), name="Mean")
                summary_df = dff.groupby(x_col)[y_col].describe().reset_index()
                summary = html.Div([
                    html.H4("Boxplot Summary Statistics"),
                    dash_table.DataTable(
                        data=summary_df.round(2).to_dict("records"),
                        columns=[{"name": col, "id": col} for col in summary_df.columns],
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left", "padding": "5px"},
                        style_header={"fontWeight": "bold"},
                    )
                ])
            elif plot_type == "scatter":
                fig = px.scatter(dff, x=x_col, y=y_col, color=group)
                #summary = html.Div([
                #    html.H4("data"),
                #    dash_table.DataTable(
                #        data=dff.round(2).to_dict("records"),
                #        columns=[{"name": col, "id": col} for col in dff.columns],
                #        style_table={"overflowX": "auto"},
                #        style_cell={"textAlign": "left", "padding": "5px"},
                #        style_header={"fontWeight": "bold"},
                #   )
                #])
            elif plot_type == "line":
                fig = px.line(dff, x=x_col, y=y_col, color=group, markers=True)
            elif plot_type == "histogram":
                fig = px.histogram(dff, x=x_col, color=group, barmode="overlay")
            elif plot_type == "bar":
                fig = px.bar(dff, x=x_col, y=y_col, color=group)
            else:
                fig = px.scatter(dff, x=x_col, y=y_col)

            fig.update_layout(title=f"{plot_type.title()} Plot: {y_col} vs {x_col}")
            return fig, summary

        @app.callback(
            dash.Output("compare-plot", "figure"),
            dash.Input("multi-exp-branch", "value"),
            dash.Input("compare-plot-type", "value"),
            #Input("compare-x", "value"),
            dash.Input("compare-y", "value"),
            dash.Input("compare-agg-func", "value")
        )
        def update_compare_plot(branches, plot_type, y_col, agg_func):
            if not branches:
                return px.scatter(title="Select branches to compare.")
            dff = df[df["exp_branch"].isin(branches)].copy()
            if y_col == "pod_name":
                dff[y_col] = dff[y_col].astype(str)

            try:
                agg_df = dff.groupby("exp_branch")[y_col].agg(agg_func).reset_index()
            except Exception as e:
                return px.scatter(title=f"Aggregation error: {e}")

            if plot_type == "line":
                fig = px.line(agg_df, x="exp_branch", y=y_col, markers=True)
            elif plot_type == "bar":
                fig = px.bar(agg_df, x="exp_branch", y=y_col, barmode="group")
            else:
                fig = px.scatter(agg_df, x="exp_branch", y=y_col)

            fig.update_layout(title=f"{agg_func.title()} of {y_col} by exp_branch")
            return fig
        
        logger.info(f"Start Server datashape {df.shape}")
        app.run(host="0.0.0.0", port=8050, debug=False, use_reloader=False)

if __name__ == '__main__':
    da = DataAnalysis("/", "data/sut_config", load_data_from_fil=True)
    da.create_server()