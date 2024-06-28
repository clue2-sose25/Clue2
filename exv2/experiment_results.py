import pandas as pd
import numpy as np
from glob import glob
import seaborn as sns
import logging
from scipy.stats import zscore


class ExperimentResults:

    DATA_ROOT_FOLDER = "data"

    def __init__(self, exp_dir=None):

        # per default, use last experiment performed
        if not exp_dir:
            experiment_dirs = sorted(glob(f"{self.DATA_ROOT_FOLDER}/*"))
            exp_dir = experiment_dirs[-1]

        self.exp_dir = exp_dir
        self.measurement_dirs = glob(self.exp_dir + "/*/*/*")

        self.nodes = self.load_nodes()
        self.pods = self.load_pods()
        self.stats = self.load_stats()

    def load_pods(self):
        return self.get_df_for_prefix("measurements_pod_")

    def load_nodes(self):
        nodes = self.get_df_for_prefix("measurements_node_")
        NodeEnergyModel.apply(nodes)
        assert "wattage_estimation" in nodes.columns
        return nodes

    def load_stats(self):
        stats = self.get_df_for_prefix("teastore_stats.csv", treat=False)
        return stats[stats["Name"] != "Aggregated"]

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

        if data_errors:
            logging.warning(
                f"dropped {data_errors} outliers ({100*data_errors/data_points:.0f}%)"
            )

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

        if treat:
            num_outliers = self._drop_outliers(pod_df)
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
            self.stats.groupby(["exp_start", "exp_branch", "exp_workload", "run_iteration"])[
                ["Request Count", "Failure Count"]
            ]
            .sum()
            .reset_index()
        )

        runs["Success Count"] = runs["Request Count"] - runs["Failure Count"]

        runs["reliability"] = (
            1 - runs["Failure Count"] / runs["Request Count"]
        )

        # return reliability

        exp_runtime = (
            self.pods.groupby(["exp_start", "exp_branch", "exp_workload", "run_iteration"])[
                "run_time"
            ]
            .max()
            .reset_index()
        )

        runs_merged = pd.merge(
            runs,
            exp_runtime,
            on=["exp_start", "exp_branch", "exp_workload", "run_iteration"],
            how="inner",
        )
        runs_merged["total_rps"] = (
            runs_merged["Request Count"] / runs_merged["run_time"].dt.total_seconds()
        )

        runs_merged["success_rps"] = (
            runs_merged["Success Count"] / runs_merged["run_time"].dt.total_seconds()
        )

        return runs_merged
    
    def rps_per_branch(self) -> pd.DataFrame:
        stats = self.run_stats()
        run_meta_columns = ["exp_start", "exp_branch", "exp_workload", "run_iteration"]
        m = stats.melt(id_vars=run_meta_columns, value_vars=["success_rps", "total_rps"])
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
