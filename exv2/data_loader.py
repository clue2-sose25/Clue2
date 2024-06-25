import pandas as pd
import numpy as np
from glob import glob
import seaborn as sns
from scipy.stats import zscore


class DataLoader:

    DATA_ROOT_FOLDER = "data"

    def __init__(self, exp_dir=None):

        # per default, use last experiment performed
        if not exp_dir:
            experiment_dirs = sorted(glob(f"{self.DATA_ROOT_FOLDER}/*"))
            exp_dir = experiment_dirs[-1]

        self.exp_dir = exp_dir
        self.measurement_dirs = glob(self.exp_dir + "/*/*/*")

    def pods(self):
        return self.get_df_for_prefix("measurements_pod_")

    def _set_experiment_time(
        self, df, col="collection_time", target="experiment_time", where="run"
    ):
        missing_time = df[df[col] == "0"]
        print(f"{len(missing_time)} missing times")
        df.drop(missing_time.index, inplace=True)
        df[col] = pd.to_datetime(df[col])

        # the fancy way with different starting times:
        # df["run_starts"] = df.groupby(where)[col].transform("min")
        # df[target] = df[col] - df["run_starts"]

        # one experiment per df:
        df[target] = df[col] - df[col].min()

    def _drop_outliers(self, df, z_score_threshold=3):
        data_errors = 0

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

        print(f"dropped {data_errors} outliers")
        return data_errors

    def measurement_file_to_df(self, file: str, prefix: str, treat=True):
        # no risk, no fun
        (_, pr_time, pr_scale, pr_branch, pr_run, pr_name) = file.split("/")
        pod_df = pd.read_csv(file)
        pod_df["exp_workload"] = pr_scale
        pod_df["exp_branch"] = pr_branch
        pod_df["exp_run_i"] = pr_run
        pod_df["exp_id"] = pr_name.replace(prefix, "").replace(".csv", "")

        pod_df["run"] = "_".join([pr_branch, pr_scale, pr_run])

        if treat:
            self._drop_outliers(pod_df)
            self._set_experiment_time(pod_df)

        return pod_df

    def get_df_for_prefix(self, prefix, treat=True):
        pod_files = np.concatenate([glob(f"{d}/{prefix}*") for d in self.measurement_dirs])
        all_pods = pd.concat(
            [self.measurement_file_to_df(pf, prefix, treat) for pf in pod_files]
        )
        return all_pods
