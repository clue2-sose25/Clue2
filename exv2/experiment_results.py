import pandas as pd
import numpy as np
from glob import glob
import seaborn as sns
import logging
from scipy.stats import zscore


class ExperimentResults:

    DATA_ROOT_FOLDER = "data"
    RUN_VARS = ["exp_start", "exp_branch", "exp_workload", "run_iteration"]
    SCAPH_FACTOR = 100
    ENERGY_WORKLOADS = ["exp_scale_fixed", "exp_scale_shaped"]

    def __init__(self, exp_dir=None, load_stats_history=True):

        # per default, use last experiment performed
        if not exp_dir:
            experiment_dirs = sorted(glob(f"{self.DATA_ROOT_FOLDER}/*"))
            exp_dir = experiment_dirs[-1]

        self.exp_dir = exp_dir
        self.measurement_dirs = glob(self.exp_dir + "/*/*/*")

        self.total_outliers = 0
        self.total_datapoints = 0

        #TODO: to speed this up we could try and add some sort of caching mechanism, based on measurment_dir+version_name write out the four files as csv after processing so we can load them instead of processing them every time.

        self.nodes = self.load_nodes()
        self.pods = self.load_pods() 
        self.pod_scaling = self.load_pod_scaling()
        self.stats = self.load_stats()
        self.stats_aggregated = self.load_stats_aggregated()

        if load_stats_history:
            self.stats_history = self.load_stat_history()
            self.stats_history_aggregated = self.load_stat_history(aggregated=True)
        else:
            self.stats_history = pd.DataFrame([],columns=['timestamp', 'user_count', 'type', 'url', 'rq_s', 'frq_s','rq', 'frq', 'mean_rsp_time', 'mean_resp_size', 'exp_workload','exp_branch', 'exp_start', 'run_start', 'run_iteration', 'run','run_time','urun'])

        logging.warn(f"loaded {self.total_datapoints} datapoints with {self.total_outliers} problems")

    def load_pods(self, filter=True):
        pods =  self.get_df_for_prefix("measurements_pod_")
        if filter:
            pods = pods[~pods.name.isin(['loadgenerator'])]
            pods = pods[~pods.instance.isin(['unknown'])]
            pods['name_prefix'] = pods['name'].apply(lambda n: n.split("-")[:-1])
        return pods 
    
    def load_pod_scaling(self):
        p = self.pods
        p['pod_name'] = p['name'].apply(lambda x: x[:-2])
        pod_scaling = p \
            .groupby(['exp_branch', 'exp_workload', 'pod_name', 'run_iteration', 'run_time']) \
            .agg({"wattage_scaph": "mean", "wattage_kepler": "mean", "cpu_usage": "sum", 'name': 'nunique'})

        return pod_scaling

    def load_nodes(self):
        nodes = self.get_df_for_prefix("measurements_node_")
        NodeEnergyModel.apply(nodes)
        assert "wattage_estimation" in nodes.columns
        return nodes

    def load_stats(self):
        stats = self.get_df_for_prefix("teastore_stats.csv", treat=False)
        return stats[stats["Name"] != "Aggregated"]
    
    def load_stats_aggregated(self):
        stats = self.get_df_for_prefix("teastore_stats.csv", treat=False)
        return stats[stats["Name"] == "Aggregated"]

    def load_stat_history(self, aggregated=False):

        history_cols = {
            "Timestamp":"timestamp",
            "User Count":"user_count",
            "Type":"type",
            "Name":"url",
            "Requests/s":"rq_s",
            "Failures/s":"frq_s",
            "Total Request Count":"rq",
            "Total Failure Count":"frq",
            "Total Average Response Time":"mean_rsp_time",
            "Total Average Content Size":"mean_resp_size",
            "50%":"p50",
            "90%":"p90",
            "95%":"p95",
            "99%":"p99",
            "99.9%":"p999",
        }

        hraw = self.get_df_for_prefix("teastore_stats_history.csv", treat=False)
        hraw['is_agg'] = hraw["Name"] == "Aggregated"
        history = hraw[hraw['is_agg'] == aggregated][[*history_cols.keys(), *self.RUN_VARS, "run_start", "run", "urun"]]
        history = history.rename(columns=history_cols)

        history["timestamp"] = history["timestamp"].astype(int)
        
        # fixing history
        # Step 1: Calculate the minimum timestamp for each 'urun'
        min_timestamps = history.groupby("urun")["timestamp"].transform("min")

        # Step 2: Subtract the minimum timestamp from each timestamp
        history["run_time"] = history["timestamp"] - min_timestamps
        history["run_time"] += 30 # XXX, TODO: this is not quite stable, this is the time delay between workload start and measurment start, we should fix this in the future, really!
        return history 

    def _set_experiment_time(
        self, df, col="collection_time", target="run_time", where="run"
    ):
        missing_time = df[df[col] == "0"]
        if len(missing_time):
            logging.warning(f"{len(missing_time)} missing times")
        df.drop(missing_time.index, inplace=True)
        df[col] = pd.to_datetime(df[col])

        # the fancy way with different starting times:
        # df["run_starts"] = df.groupby(where)[col].transform("min")
        # df[target] = df[col] - df["run_starts"]

        # one experiment per df:
        df[target] = df[col] - df[col].min()

    def _drop_outliers(self, df, z_score_threshold=3):
        data_errors = 0
        data_points = len(df)

        common_keys = [
            "wattage_kepler",
            "wattage_scaph",
            # "wattage"
            "cpu_usage",
            "memory_usage",
            "network_usage",
        ]

        for key in common_keys:
            if key in df:
                df[f"{key}_zscore"] = zscore(df[key])

        for key in common_keys:
            outliers = df[df[f"{key}_zscore"].abs() > z_score_threshold].index
            data_errors += len(outliers)
            df = df.drop(outliers)

        # if data_errors:
        #     logging.warning(
        #         f"dropped {data_errors} outliers ({100*data_errors/data_points:.0f}%)"
        #     )

        self.total_datapoints += data_points
        self.total_outliers += data_errors

        # print(f"dropped {data_errors} outliers")
        return data_errors

    def measurement_file_to_df(self, file: str, prefix: str, treat=True):
        # no risk, no fun
        (_, pr_time, pr_scale, pr_branch, pr_run, pr_name) = file.split("/")
        pod_df = pd.read_csv(file)
        pod_df["exp_workload"] = pr_scale
        pod_df["exp_branch"] = pr_branch
        pod_df["exp_start"] = pr_time
        pod_df["run_start"] = pr_name.replace(prefix, "").replace(".csv", "")
        pod_df["run_iteration"] = pr_run

        pod_df["run"] = "_".join([pr_branch, pr_scale, pr_run])
        pod_df["urun"] = "_".join([pr_time,pr_branch, pr_scale, pr_run])
        if treat:
            self.total_outliers += self._drop_outliers(pod_df)
            self._set_experiment_time(pod_df)

        return pod_df

    def get_df_for_prefix(self, prefix, treat=True):
        pod_files = np.concatenate(
            [glob(f"{d}/{prefix}*") for d in self.measurement_dirs]
        )
        all_pods = pd.concat(
            [self.measurement_file_to_df(pf, prefix, treat) for pf in pod_files]
        )
        return all_pods

    def absolute_requests_per_branch(self) -> pd.DataFrame:
        return self.stats.melt(
            id_vars="exp_branch", value_vars=["Request Count", "Failure Count"]
        )

    def run_stats(self):

        # exp_runtime = self.pods.groupby(["exp_time","exp_branch","exp_workload","exp_run_i"])["run_time"].max().reset_index()
        # requests = self.stats.groupby(["exp_time","exp_branch","exp_workload","exp_run_i"])[["request_count","failure_count"]].sum().reset_index()
        # requests = pd.merge(requests,exp_runtime, on=["exp_time","exp_branch","exp_workload","exp_run_i"], how="inner")
        # requests["real_requests"]=requests["request_count"]-requests["failure_count"]
        # requests["request_per_s"] = requests["real_requests"]/requests["run_time"]
        # requests.groupby(["exp_branch","exp_workload"])[["real_requests","request_per_s"]].sum()

        runs = (
            self.stats.groupby(ExperimentResults.RUN_VARS)[
                ["Request Count", "Failure Count"]
            ]
            .sum()
            .reset_index()
        )

        runs["Success Count"] = runs["Request Count"] - runs["Failure Count"]

        runs["reliability"] = 1 - runs["Failure Count"] / runs["Request Count"]

        # return reliability

        exp_runtime = (
            self.pods.groupby(ExperimentResults.RUN_VARS)["run_time"]
            .max()
            .reset_index()
        )

        runs_merged = pd.merge(
            runs,
            exp_runtime,
            on=ExperimentResults.RUN_VARS,
            how="inner",
        )
        runs_merged["total_rps"] = (
            runs_merged["Request Count"] / runs_merged["run_time"].dt.total_seconds()
        )

        runs_merged["success_rps"] = (
            runs_merged["Success Count"] / runs_merged["run_time"].dt.total_seconds()
        )

        return runs_merged

    def _calc_energy(self, input, wattages, energy_workloads=True):
        """
        Aggregate Wattages in different ways. Only use Workloads that make sense for that.

        kepler in: irate(kepler_node_core_joules_total[1m]
        """

        raw = input.copy()
        
        # not all workloads makes sense for energy consumption
        if energy_workloads:
            raw = raw[raw['exp_workload'].isin(self.ENERGY_WORKLOADS)]


        raw["wattage_scaph"] *= self.SCAPH_FACTOR

        wsum = raw.groupby(self.RUN_VARS).agg(
            {"run_time": "max"} | {w: "sum" for w in wattages}
        )

        wavg = raw.groupby(self.RUN_VARS).agg(
            {"run_time": "max"} | {w: "mean" for w in wattages}
        )

        for w in wattages:
            wsum[f"{w}_avg"] = wavg[w] * wavg["run_time"].dt.total_seconds()

        # todo: node wattages (also estimate + tap)o

        return wsum

    def pods_energy(self, energy_workloads=True):
        wattages = ["wattage_kepler", "wattage_scaph", "cpu_usage", "memory_usage"]
        return self._calc_energy(self.pods, wattages, energy_workloads)

    def nodes_energy(self):
        wattages = ["wattage_kepler", "wattage_scaph", "wattage", "cpu_usage", "memory_usage"]
        return self._calc_energy(self.nodes, wattages)

    def rps_per_branch(self) -> pd.DataFrame:
        stats = self.run_stats()
        run_meta_columns = ExperimentResults.RUN_VARS
        m = stats.melt(
            id_vars=run_meta_columns, value_vars=["success_rps", "total_rps"]
        )
        return m


class NodeEnergyModel:
    physical_nodes = ["sm-gpu", "ise-knode6"]
    cpu_specs = {
        # idle, peak, memory
        "sm-gpu": [
            20,
            90,
            2.5,
        ],  # based on https://www.tomshardware.com/reviews/amd-ryzen-5-3600-review,6287-3.html
        "ise-knode6": [
            11,
            73,
            2.5,
        ],  # based on https://www.tomshardware.com/reviews/skylake-intel-core-i7-6700k-core-i5-6600k,4252-11.html
    }

    node_models = {
        "sm-gpu": [45.92820512, 56.31438933, -7.39335927],
        "ise-knode6": [41.25204258, 42.25050137, 22.34559982],
    }

    def energy_func(X, idle, c_peak, mem_peak):
        return idle + ((c_peak - idle) * X[:, 0]) + ((mem_peak) * X[:, 1])

    def apply(df: pd.DataFrame):
        for instance in NodeEnergyModel.node_models:
            df.loc[df["instance"] == instance, "wattage_estimation"] = (
                NodeEnergyModel.energy_func(
                    df[df["instance"] == instance][
                        ["cpu_usage", "memory_usage"]
                    ].values,
                    *NodeEnergyModel.node_models[instance],
                )
            )
        return df
