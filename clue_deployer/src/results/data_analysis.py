import seaborn as sns # type: ignore
import pandas as pd# type: ignore
import matplotlib.pyplot as plt # type: ignore
import glasbey # type: ignore
import numpy as np # type: ignore
import warnings
import yaml # type: ignore
from clue_deployer.src.results.experiment_results import ExperimentResults
from datetime import time
from clue_deployer.src.logger import logger
import dash
import dash_table
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import statsmodels.api as sm
import numpy as np
from scipy.stats import mannwhitneyu, pearsonr



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
        df.rename(columns = {'exp_branch': 'variant', 'exp_workload': 'workload'}, inplace = True)

        ####---------------------Standard plots setup---------------------####

        plot_columns = ["cpu_usage", "wattage_kepler", "network_usage", "memory_usage", "pod_name", "observation_time", "collection_time"]
        group_columns = ["None", "run_iteration", "instance", "pod_name", "variant", "workload"]
        agg_options = ["mean", "median", "min", "max", "sum"]

        ####---------------------Regression setup---------------------####

        variant_options = [{"label": v, "value": v} for v in sorted(df["variant"].dropna().unique())]
        workload_options = [{"label": w, "value": w} for w in sorted(df["workload"].dropna().unique())]
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        feature_options = [{"label": col, "value": col} for col in numeric_cols]

        default_features = ["memory_usage", "network_usage", "cpu_usage"]
        default_target = "wattage_kepler"

        ####---------------------Correlation setup---------------------####
        def cliffs_delta(a, b):
            a, b = np.array(a), np.array(b)
            n, m = len(a), len(b)
            greater = np.sum(a[:, None] > b)
            less = np.sum(a[:, None] < b)
            return (greater - less) / (n * m)

        variant_options = [{"label": v, "value": v} for v in sorted(df["variant"].dropna().unique())]
        workload_options = [{"label": w, "value": w} for w in sorted(df["workload"].dropna().unique())]

        app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        app.title = "Data Explorer"

        def card_toggle_header(title, icon_id, toggle_id):
            return html.Div([
                html.Span(title, style={"fontWeight": "bold", "fontSize": "1.2rem"}),
                html.Span(id=icon_id, children="⯆", style={"float": "right", "cursor": "pointer", "fontSize": "1.5rem"})
            ], id=toggle_id, n_clicks=0, style={"cursor": "pointer", "display": "flex", "justifyContent": "space-between", "alignItems": "center"})

        app.layout = dbc.Container([

            # Observation Analysis Card
            dbc.Card([
                dbc.CardHeader(card_toggle_header("Observation Analysis", "obs-icon", "obs-toggle")),
                dbc.Collapse(dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Filter by Variant"),
                            dcc.Dropdown(
                                id="branch-dropdown",
                                options=[{"label": b, "value": b} for b in sorted(df["variant"].dropna().unique())],
                                value=None, clearable=True
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Filter by Workload"),
                            dcc.Dropdown(
                                id="workload-dropdown",
                                options=[{"label": w, "value": w} for w in sorted(df["workload"].dropna().unique())],
                                value=None, clearable=True
                            )
                        ], width=6),
                    ], className="p-2 mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Filter Column"),
                            dcc.Dropdown(
                                id="value-filter-column",
                                options=[{"label": col, "value": col} for col in df.columns],
                                placeholder="Select column to filter"
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Filter Values"),
                            dcc.Dropdown(
                                id="value-filter-values",
                                options=[], multi=True,
                                placeholder="Select values"
                            )
                        ], width=6),
                    ], className="p-2 mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Main Plot Type"),
                            dcc.Dropdown(
                                id="plot-type",
                                options=[{"label": t.title(), "value": t} for t in ["scatter", "line", "box", "histogram", "bar"]],
                                value="scatter"
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Group Plot By"),
                            dcc.Dropdown(
                                id="group-by",
                                options=[{"label": col, "value": col} for col in group_columns],
                                value="instance", clearable=False
                            )
                        ], width=6),
                    ], className="p-2 mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("X-Axis"),
                            dcc.Dropdown(
                                id="x-axis",
                                options=[{"label": col, "value": col} for col in plot_columns],
                                value=plot_columns[0]
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Y-Axis"),
                            dcc.Dropdown(
                                id="y-axis",
                                options=[{"label": col, "value": col} for col in plot_columns],
                                value=plot_columns[1]
                            )
                        ], width=6),
                    ], className="p-2 mb-3"),

                    dcc.Graph(id="main-plot"),
                    html.Div(id="summary-table")
                ]), id="obs-collapse", is_open=True)
            ], className="mb-4"),

            # Variant Comparison Card
            dbc.Card([
                dbc.CardHeader(card_toggle_header("Variant Comparison", "cmp-icon", "cmp-toggle")),
                dbc.Collapse(dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Select variant(s)"),
                            dcc.Dropdown(
                                id="multi-exp-branch",
                                options=[{"label": b, "value": b} for b in sorted(df["variant"].dropna().unique())],
                                value=[], multi=True
                            )
                        ], width=6),
                    ], className="p-2 mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Comparison Plot Type"),
                            dcc.Dropdown(
                                id="compare-plot-type",
                                options=[{"label": t.title(), "value": t} for t in ["line", "scatter", "bar"]],
                                value="line"
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Aggregation Function"),
                            dcc.Dropdown(
                                id="compare-agg-func",
                                options=[{"label": f.title(), "value": f} for f in agg_options],
                                value="mean"
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Y-Axis"),
                            dcc.Dropdown(
                                id="compare-y",
                                options=[{"label": col, "value": col} for col in plot_columns],
                                value=plot_columns[1]
                            )
                        ], width=4),
                    ], className="p-2 mb-3"),

                    dcc.Graph(id="compare-plot")
                ]), id="cmp-collapse", is_open=True)
            ]),
            
            #Regression Card
            dbc.Card([
                html.Div([
                    dbc.CardHeader(
                        dbc.Row([
                            dbc.Col(html.H5("Regression Model Explorer"), align="center"),
                            dbc.Col(html.Div(id="collapse-icon", style={"textAlign": "right", "cursor": "pointer"}), width="auto", align="center")
                        ], justify="between", className="w-100"),
                        className="p-2"
                    )
                ], id="toggle-area", n_clicks=0, style={"cursor": "pointer"}),

                dbc.Collapse(
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Select Variant"),
                                dcc.Dropdown(id="variant-dropdown", options=variant_options)
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Select Workload"),
                                dcc.Dropdown(id="workload-dropdown", options=workload_options)
                            ], md=6),
                        ], className="mb-3"),

                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Select Features"),
                                dcc.Dropdown(
                                    id="feature-dropdown",
                                    options=feature_options,
                                    multi=True,
                                    value=default_features
                                )
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Select Target"),
                                dcc.Dropdown(
                                    id="target-dropdown",
                                    options=feature_options,
                                    value=default_target
                                )
                            ], md=6),
                        ], className="mb-3"),

                        html.Div(id="plot-output")
                    ]),
                    id="collapse-body",
                    is_open=True
                )
            ], className="my-4 p-2"),
            
            #Correlation Card
            dbc.Card([
                dbc.CardHeader(
                    html.Div([
                        html.Span("Statistical Influence Analysis", style={"fontWeight": "bold", "fontSize": "1.2rem"}),
                        html.Span(id="collapse-icon", children="⯆", style={"float": "right", "cursor": "pointer", "fontSize": "1.5rem"})
                    ], id="collapse-toggle", n_clicks=0, style={"cursor": "pointer", "display": "flex", "justifyContent": "space-between", "alignItems": "center"})
                ),
                dbc.Collapse(
                    dbc.CardBody([

                        # Selection Controls
                        dbc.Card([
                            dbc.CardHeader("Selection Controls"),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Select Workload"),
                                        dcc.Dropdown(id="workload-select", options=workload_options, value=workload_options[0]["value"]),
                                    ], md=6),
                                    dbc.Col([
                                        dbc.Label("Select Variants"),
                                        dcc.Dropdown(id="variant-select", options=variant_options, value=[v["value"] for v in variant_options], multi=True),
                                    ], md=6)
                                ])
                            ])
                        ], className="mb-4"),

                        # Heatmaps
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Cliff's Delta"),
                                    dbc.CardBody([
                                        html.Div([
                                            html.H5("Interpretation"),
                                            html.Ul([
                                                html.Li("Δ ≈ 0: no effect"),
                                                html.Li("Δ ≈ ±0.1: small effect"),
                                                html.Li("Δ ≈ ±0.33: medium effect"),
                                                html.Li("Δ ≈ ±0.47 or more: large effect"),
                                            ]),
                                            html.P("Significance tested with Mann–Whitney U test (p < 0.05)."),
                                        ], style={"minHeight": "180px"}),
                                        html.Div(dcc.Graph(id="cliffs-heatmap"), style={"flex": "1 1 auto"})
                                    ], style={"display": "flex", "flexDirection": "column", "height": "100%"})
                                ], style={"height": "100%"})
                            ], md=6),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("Pearson Correlation"),
                                    dbc.CardBody([
                                        html.Div([
                                            html.H5("Interpretation"),
                                            html.Ul([
                                                html.Li("r = 1: perfect positive linear relationship"),
                                                html.Li("r = 0: no linear relationship"),
                                                html.Li("r = -1: perfect negative linear relationship"),
                                            ]),
                                            html.P("Significance based on Pearson p-value (p < 0.05)."),
                                        ], style={"minHeight": "180px"}),
                                        html.Div(dcc.Graph(id="pearson-heatmap"), style={"flex": "1 1 auto"})
                                    ], style={"display": "flex", "flexDirection": "column", "height": "100%"})
                                ], style={"height": "100%"})
                            ], md=6)
                        ])
                    ]),
                    id="main-collapse",
                    is_open=True
                )
            ], className="my-4 p-3 shadow")
            
        ], fluid=True)

        # Toggle callbacks
        @app.callback(
            Output("obs-collapse", "is_open"),
            Output("obs-icon", "children"),
            Input("obs-toggle", "n_clicks"),
            State("obs-collapse", "is_open")
        )
        def toggle_obs(n, is_open):
            if n == 0:
                raise dash.exceptions.PreventUpdate
            new_state = not is_open
            return new_state, "⯆" if new_state else "⯇"

        @app.callback(
            Output("cmp-collapse", "is_open"),
            Output("cmp-icon", "children"),
            Input("cmp-toggle", "n_clicks"),
            State("cmp-collapse", "is_open")
        )
        def toggle_cmp(n, is_open):
            if n == 0:
                raise dash.exceptions.PreventUpdate
            new_state = not is_open
            return new_state, "⯆" if new_state else "⯇"

        # Value filter update
        @app.callback(
            Output("value-filter-values", "options"),
            Input("value-filter-column", "value")
        )
        def update_value_filter_options(selected_col):
            if selected_col and selected_col in df.columns:
                unique_vals = df[selected_col].dropna().unique()
                return [{"label": str(v), "value": v} for v in sorted(unique_vals)]
            return []

        # Main plot
        @app.callback(
            Output("main-plot", "figure"),
            Output("summary-table", "children"),
            Input("branch-dropdown", "value"),
            Input("workload-dropdown", "value"),
            Input("plot-type", "value"),
            Input("group-by", "value"),
            Input("x-axis", "value"),
            Input("y-axis", "value"),
            Input("value-filter-column", "value"),
            Input("value-filter-values", "value")
        )
        def update_main_plot(branch, workload, plot_type, group_by, x_col, y_col, filter_col, filter_vals):
            dff = df.copy()
            if branch:
                dff = dff[dff["variant"] == branch]
            if workload:
                dff = dff[dff["workload"] == workload]
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
                summary = dbc.Card([
                    dbc.CardHeader("Boxplot Summary Statistics"),
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

        # Compare plot
        @app.callback(
            Output("compare-plot", "figure"),
            Input("multi-exp-branch", "value"),
            Input("compare-plot-type", "value"),
            Input("compare-y", "value"),
            Input("compare-agg-func", "value")
        )
        def update_compare_plot(branches, plot_type, y_col, agg_func):
            if not branches:
                return px.scatter(title="Select branches to compare.")
            dff = df[df["variant"].isin(branches)].copy()
            if y_col == "pod_name":
                dff[y_col] = dff[y_col].astype(str)

            try:
                agg_df = dff.groupby("variant")[y_col].agg(agg_func).reset_index()
            except Exception as e:
                return px.scatter(title=f"Aggregation error: {e}")

            if plot_type == "line":
                fig = px.line(agg_df, x="variant", y=y_col, markers=True)
            elif plot_type == "bar":
                fig = px.bar(agg_df, x="variant", y=y_col, barmode="group")
            else:
                fig = px.scatter(agg_df, x="variant", y=y_col)

            fig.update_layout(title=f"{agg_func.title()} of {y_col} by variant")
            return fig

        ####---------------------Regression Functions---------------------####
        # Toggle collapse
        @app.callback(
            Output("collapse-body", "is_open"),
            Input("toggle-area", "n_clicks"),
            State("collapse-body", "is_open"),
            prevent_initial_call=True
        )
        def toggle_collapse(n, is_open):
            return not is_open

        # Update arrow icon
        @app.callback(
            Output("collapse-icon", "children"),
            Input("collapse-body", "is_open")
        )
        def update_icon(is_open):
            return "⯆" if is_open else "⯇"

        # Main output
        @app.callback(
            Output("plot-output", "children"),
            Input("variant-dropdown", "value"),
            Input("workload-dropdown", "value"),
            Input("feature-dropdown", "value"),
            Input("target-dropdown", "value")
        )
        def update_plot(variant, workload, features, target):
            if not (variant and workload and features and target):
                return dbc.Alert("Please select all inputs.", color="warning")

            dff = df[(df["variant"] == variant) & (df["workload"] == workload)].dropna(subset=features + [target])
            if dff.empty:
                return dbc.Alert("No data available after filtering.", color="danger")

            X = dff[features]
            y = dff[target]
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            try:
                X_sm = sm.add_constant(X_train_scaled)
                sm_model = sm.OLS(y_train, X_sm).fit()
                ols_summary_text = sm_model.summary().as_text()
            except Exception as e:
                ols_summary_text = f"OLS failed: {e}"

            lr = LinearRegression().fit(X_train_scaled, y_train)
            ridge = Ridge(alpha=1.0).fit(X_train_scaled, y_train)
            lasso = Lasso(alpha=0.01).fit(X_train_scaled, y_train)
            rf = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_train, y_train)

            models = {
                "Linear": (lr, lr.predict(X_test_scaled)),
                "Ridge": (ridge, ridge.predict(X_test_scaled)),
                "Lasso": (lasso, lasso.predict(X_test_scaled)),
                "Random Forest": (rf, rf.predict(X_test))
            }

            results = []
            for name, (model, y_pred) in models.items():
                results.append({
                    "Model": name,
                    "R²": round(r2_score(y_test, y_pred), 3),
                    "MSE": round(mean_squared_error(y_test, y_pred), 6),
                    "Pred": y_pred
                })

            scatter_fig = go.Figure()
            colors = {"Linear": "blue", "Ridge": "green", "Lasso": "purple", "Random Forest": "orange"}
            for res in results:
                scatter_fig.add_trace(go.Scatter(
                    x=y_test,
                    y=res["Pred"],
                    mode="markers",
                    name=res["Model"],
                    marker=dict(size=6, opacity=0.7, color=colors[res["Model"]])
                ))

            scatter_fig.add_trace(go.Scatter(
                x=[y_test.min(), y_test.max()],
                y=[y_test.min(), y_test.max()],
                mode="lines",
                name="Ideal",
                line=dict(color="red", dash="dash")
            ))

            scatter_fig.update_layout(
                title="Actual vs. Predicted",
                xaxis_title=f"Actual {target}",
                yaxis_title=f"Predicted {target}",
                height=500
            )

            importance_fig = make_subplots(
                rows=1, cols=4,
                shared_yaxes=True,
                horizontal_spacing=0.05,
                subplot_titles=("Linear", "Ridge", "Lasso", "Random Forest")
            )

            for i, (name, model) in enumerate([("Linear", lr), ("Ridge", ridge), ("Lasso", lasso)], start=1):
                importance_fig.add_trace(go.Bar(
                    x=model.coef_, y=features, orientation="h", showlegend=False
                ), row=1, col=i)

            importance_fig.add_trace(go.Bar(
                x=rf.feature_importances_, y=features, orientation="h", showlegend=False
            ), row=1, col=4)

            importance_fig.update_layout(
                height=400,
                title_text="Feature Importances by Model",
                margin=dict(t=50)
            )

            summary_table = dbc.Card([
                dbc.CardHeader("Model Performance Summary"),
                dash_table.DataTable(
                    data=[{"Model": r["Model"], "R²": r["R²"], "MSE": r["MSE"]} for r in results],
                    columns=[{"name": i, "id": i} for i in ["Model", "R²", "MSE"]],
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "center"},
                    style_header={"fontWeight": "bold"}
                )
            ], className="my-4")

            def model_card(title, intercept, r2, mse, coefs):
                lines = [f"Intercept: {intercept:.4f}", f"R²: {r2:.4f}", f"MSE: {mse:.6f}", "", "Coefficients:"]
                lines += [f"{f}: {round(c, 4)}" for f, c in zip(features, coefs)]
                return dbc.Card([
                    dbc.CardHeader(title),
                    dbc.CardBody(html.Pre("\n".join(lines), style={"whiteSpace": "pre-wrap", "fontSize": "13px"}))
                ])

            def rf_card(title, r2, mse, importances):
                lines = [f"R²: {r2:.4f}", f"MSE: {mse:.6f}", "", "Feature Importances:"]
                lines += [f"{f}: {round(i, 4)}" for f, i in zip(features, importances)]
                return dbc.Card([
                    dbc.CardHeader(title),
                    dbc.CardBody(html.Pre("\n".join(lines), style={"whiteSpace": "pre-wrap", "fontSize": "13px"}))
                ])

            summaries_row = dbc.Row([
                dbc.Col(model_card("Linear Regression", lr.intercept_, r2_score(y_test, lr.predict(X_test_scaled)), mean_squared_error(y_test, lr.predict(X_test_scaled)), lr.coef_), md=6, lg=4),
                dbc.Col(model_card("Ridge Regression", ridge.intercept_, r2_score(y_test, ridge.predict(X_test_scaled)), mean_squared_error(y_test, ridge.predict(X_test_scaled)), ridge.coef_), md=6, lg=4),
                dbc.Col(model_card("Lasso Regression", lasso.intercept_, r2_score(y_test, lasso.predict(X_test_scaled)), mean_squared_error(y_test, lasso.predict(X_test_scaled)), lasso.coef_), md=6, lg=4),
                dbc.Col(rf_card("Random Forest", r2_score(y_test, rf.predict(X_test)), mean_squared_error(y_test, rf.predict(X_test)), rf.feature_importances_), md=6, lg=4),
            ], className="gy-4 my-4")

            ols_summary = dbc.Card([
                dbc.CardHeader("OLS Regression Summary (statsmodels)"),
                dbc.CardBody(html.Pre(ols_summary_text, style={"whiteSpace": "pre-wrap", "fontSize": "13px"}))
            ])

            return dbc.Card([
                dbc.CardHeader("Regression Results"),
                dbc.CardBody([
                    dcc.Graph(figure=scatter_fig),
                    dcc.Graph(figure=importance_fig),
                    summary_table,
                    summaries_row,
                    ols_summary
                ])
            ], className="mb-4 p-2")

        ####---------------------Correlation Functions---------------------####
        def toggle_main(n, is_open):
            if n == 0:
                raise dash.exceptions.PreventUpdate
            new_state = not is_open
            return new_state, "⯆" if new_state else "⯇"

        # Heatmap callback
        @app.callback(
            Output("cliffs-heatmap", "figure"),
            Output("pearson-heatmap", "figure"),
            Input("variant-select", "value"),
            Input("workload-select", "value")
        )
        def update_heatmaps(selected_variants, selected_workload):
            if not selected_variants or len(selected_variants) < 2 or not selected_workload:
                empty_fig = px.imshow([[0]], x=["Select ≥2"], y=["Select ≥2"],
                                    labels=dict(x="Variant", y="Variant", color="Value"),
                                    title="Please select at least 2 variants and a workload.")
                return empty_fig, empty_fig

            data = df[(df["variant"].isin(selected_variants)) & (df["workload"] == selected_workload)]
            cliffs_matrix = pd.DataFrame(index=selected_variants, columns=selected_variants, dtype=float)
            pearson_matrix = pd.DataFrame(index=selected_variants, columns=selected_variants, dtype=float)
            hover_cliff, hover_pearson = [], []

            grouped = {v: data[data["variant"] == v]["wattage_kepler"].dropna() for v in selected_variants}

            for v1 in selected_variants:
                row_cliff = []
                row_pearson = []
                for v2 in selected_variants:
                    x, y = grouped.get(v1), grouped.get(v2)
                    if v1 == v2:
                        cliffs_matrix.loc[v1, v2] = 0.0
                        pearson_matrix.loc[v1, v2] = 1.0
                        row_cliff.append("Δ = 0.000")
                        row_pearson.append("r = 1.000<br>p = 0.000")
                    elif x.empty or y.empty:
                        cliffs_matrix.loc[v1, v2] = np.nan
                        pearson_matrix.loc[v1, v2] = np.nan
                        row_cliff.append("N/A")
                        row_pearson.append("N/A")
                    else:
                        try:
                            delta = cliffs_delta(x, y)
                            p_cliff = mannwhitneyu(x, y, alternative='two-sided').pvalue
                            cliffs_matrix.loc[v1, v2] = round(delta, 3)
                            row_cliff.append(f"Δ = {delta:.3f}<br>p = {p_cliff:.3f}")
                        except:
                            cliffs_matrix.loc[v1, v2] = np.nan
                            row_cliff.append("Error")
                        try:
                            n = min(len(x), len(y))
                            r_val, p_val = pearsonr(x[:n], y[:n])
                            pearson_matrix.loc[v1, v2] = round(r_val, 3)
                            row_pearson.append(f"r = {r_val:.3f}<br>p = {p_val:.3f}")
                        except:
                            pearson_matrix.loc[v1, v2] = np.nan
                            row_pearson.append("Error")
                hover_cliff.append(row_cliff)
                hover_pearson.append(row_pearson)

            zmin, zmax = -1, 1

            fig_cliffs = px.imshow(
                cliffs_matrix.astype(float),
                text_auto=True,
                color_continuous_scale="RdBu",
                zmin=zmin, zmax=zmax,
                labels=dict(x="Variant", y="Variant", color="Cliff's Δ"),
                title=f"Cliff's Delta — {selected_workload}",
                x=selected_variants,
                y=selected_variants
            )
            fig_cliffs.update_traces(customdata=np.array(hover_cliff), hovertemplate="%{customdata}<extra></extra>")

            fig_pearson = px.imshow(
                pearson_matrix.astype(float),
                text_auto=True,
                color_continuous_scale="RdBu",
                zmin=zmin, zmax=zmax,
                labels=dict(x="Variant", y="Variant", color="Pearson r"),
                title=f"Pearson Correlation — {selected_workload}",
                x=selected_variants,
                y=selected_variants
            )
            fig_pearson.update_traces(customdata=np.array(hover_pearson), hovertemplate="%{customdata}<extra></extra>")

            return fig_cliffs, fig_pearson

        
        app.run(host="0.0.0.0", port=8050, debug=False, use_reloader=False)

if __name__ == '__main__':
    da = DataAnalysis("/", "data/sut_config", load_data_from_fil=True)
    da.create_server()