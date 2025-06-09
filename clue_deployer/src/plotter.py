import os
import pathlib
import warnings

import glasbey
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from clue_deployer.src.logger import logger

warnings.filterwarnings('ignore')

# --- Constants and Configurations from Notebook ---

WS_PRICE = 0.5 / 3_600_000  # based on germany mean kWh price

# AWS cost-model
SERVERLESS_PRICE = 0.0000166667  # based on aws lambda price per GB-s (frankfurt)
MEMORY_SECOND_PRICE = 0.00511 / 1024 / 60  # $/MBs based on AWS fargate memory price per hour (frankfurt)
VCPU_SECOND_PRICE = 0.04656 / 60  # $/vCPU based on AWS fargate memory price per hour (frankfurt)

NODE_MODEL = {
    "sm-gpu": 32704316 // 1024,
    "ise-knode6": 32719632 // 1024,
    "ise-knode1": 32761604 // 1024,
}

POD_CONFIGURATION = {
    "teastore-recommender": {"cpu": 2600, "memory": 1332},
    "teastore-webui": {"cpu": 1300, "memory": 1950},
    "teastore-image": {"cpu": 1300, "memory": 1950},
    "teastore-auth": {"cpu": 585, "memory": 1332},
    'teastore-registry': {"cpu": 1000, "memory": 1024},
    'teastore-persistence': {"cpu": 1000, "memory": 1024},
    'teastore-db': {"cpu": 1000, "memory": 1024},
    "teastore-all": {"cpu": 1950, "memory": 2663},
    "auth": {"cpu": 500, "memory": 500},
}

GENERAL_ALLOWANCE = {
    "teastore-recommender": {"cpu": 2600, "memory": 1332},
    "teastore-webui": {"cpu": 1300, "memory": 1950},
    "teastore-image": {"cpu": 1300, "memory": 1950},
    "teastore-auth": {"cpu": 585, "memory": 1332},
    'teastore-registry': {"cpu": 1300, "memory": 1332},
    'teastore-persistence': {"cpu": 1300, "memory": 1332},
    'teastore-db': {"cpu": 1300, "memory": 1332},
    "teastore-all": {"cpu": 1950, "memory": 2663},
    "auth": {"cpu": 500, "memory": 500},
}

RESOURCE_SCALE = {
    "baseline_vanilla_full": {
        'teastore-recommender': 3, 'teastore-webui': 3, 'teastore-image': 3,
        'teastore-auth': 3, 'teastore-registry': 1, 'teastore-persistence': 1,
        'teastore-db': 1, "teastore-all": 0, "auth": 0,
    },
    'jvm_jvm-impoove_full': {
        'teastore-recommender': 3, 'teastore-webui': 3, 'teastore-image': 3,
        'teastore-auth': 3, 'teastore-registry': 1, 'teastore-persistence': 1,
        'teastore-db': 1, "teastore-all": 0, "auth": 0,
    },
    'monolith_feature_monolith_full': {
        'teastore-recommender': 0, 'teastore-webui': 0, 'teastore-image': 0,
        'teastore-auth': 0, 'teastore-registry': 1, 'teastore-persistence': 0,
        'teastore-db': 1, "teastore-all": 3, "auth": 0,
    },
    'norec_feature_norecommendations_full': {
        'teastore-recommender': 0, 'teastore-webui': 3, 'teastore-image': 3,
        'teastore-auth': 3, 'teastore-registry': 1, 'teastore-persistence': 1,
        'teastore-db': 1, "teastore-all": 0, "auth": 0,
    },
    'serverless_feature_serverless_full': {
        'teastore-recommender': 3, 'teastore-webui': 3, 'teastore-image': 3,
        'teastore-auth': 0, 'teastore-registry': 1, 'teastore-persistence': 1,
        'teastore-db': 1, "teastore-all": 0, "auth": 40,
    },
}

FULL_STACK_FOCUS = [
    "baseline_vanilla_full", "monolith_feature_monolith_full",
    "serverless_feature_serverless_full", "norec_feature_norecommendations_full",
    "jvm_jvm-impoove_full"
]

LABLE_NAMES = {
    "baseline_vanilla_full": "Microservices",
    'monolith_feature_monolith_full': "Monolith",
    'serverless_feature_serverless_full': "Serverless",
    'jvm_jvm-impoove_full': "Runtime Improvement",
    'norec_feature_norecommendations_full': "Service Reduction",
    'exp_scale_pausing': "Pausing",
    "exp_scale_rampup": "Stress",
    "exp_scale_fixed": "Fixed",
    "exp_scale_shaped": "Regular",
}

SHORT_LABELS = {
    "baseline_vanilla_full": "MS",
    'monolith_feature_monolith_full': "ML",
    'serverless_feature_serverless_full': "SL",
    'jvm_jvm-impoove_full': "RT",
    'norec_feature_norecommendations_full': "SR",
}

RUN_VARS = ['exp_start', 'exp_branch', 'exp_workload', 'run_iteration']

# --- Helper Functions from Notebook ---

def _setup_style():
    """Sets up the plotting style."""
    pd.set_option('display.max_columns', None)
    sns.set_theme(rc={'figure.figsize': (12, 6)})
    sns.set_context("paper")
    sns.set_style("whitegrid")
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    palette = glasbey.create_block_palette(
        [4, 3, 3, 2, 2], colorblind_safe=True, cvd_severity=90
    )
    sns.set_palette(palette)
    return palette

def _calc_request_based_billing(row):
    if row["type"] == "pod":
        conf = POD_CONFIGURATION[row["pod_name"]]
        return conf["memory"] * MEMORY_SECOND_PRICE + np.ceil(conf["cpu"] / 1000) * VCPU_SECOND_PRICE
    elif row["type"] == "function":
        return 500 * SERVERLESS_PRICE
    return 0

def _calc_usage_based_billing(row):
    if row["type"] == "pod":
        return row["memory_usage"] * MEMORY_SECOND_PRICE + np.ceil(row["cpu_usage"]) * VCPU_SECOND_PRICE
    elif row["type"] == "function":
        return row["memory_usage"] * SERVERLESS_PRICE
    return 0

def _calculate_maximum_resource_allowance(exp_branch: str):
    scale = RESOURCE_SCALE[exp_branch]
    max_allowance = {"cpu": 0, "memory": 0}
    for pod_name, pod_scale in scale.items():
        if pod_name in GENERAL_ALLOWANCE:
            for resource, value in GENERAL_ALLOWANCE[pod_name].items():
                max_allowance[resource] += value * pod_scale
    return max_allowance

def _calulate_resource_allowence(row):
    branch = row["exp_branch"]
    pod_type = row["type"]
    if branch not in RESOURCE_SCALE or pod_type not in RESOURCE_SCALE[branch]:
        return row

    if pod_type.startswith("auth"):
        cpu = GENERAL_ALLOWANCE["auth"]["cpu"]
        memory = GENERAL_ALLOWANCE["auth"]["memory"]
        max_count = RESOURCE_SCALE[branch]["auth"]
    elif pod_type in GENERAL_ALLOWANCE:
        cpu = GENERAL_ALLOWANCE[pod_type]["cpu"]
        memory = GENERAL_ALLOWANCE[pod_type]["memory"]
        max_count = RESOURCE_SCALE[branch][pod_type]
    else:
        return row

    row["cpu_limit"] = cpu * row["count"]
    row["mem_limit"] = memory * row["count"]
    row["cpu_max"] = cpu * max_count
    row["mem_max"] = memory * max_count
    return row

def _calculate_cost(row):
    return (row['memory_usage'] * MEMORY_SECOND_PRICE +
            np.ceil(row["cpu_usage"]) * VCPU_SECOND_PRICE +
            (row["wattage_kepler"] * WS_PRICE))

def _calculate_memory_usage(row):
    instance = row.get('instance')
    if instance in NODE_MODEL:
        return row['memory_usage'] * NODE_MODEL[instance]
    return row['memory_usage']


# --- Main Plotting Function ---

def generate_plots(data_path: str, output_path: str):
    """
    Generates and saves plots from the experiment data.

    Args:
        data_path: Path to the directory containing 'observation.hdf5'.
        output_path: Path to the directory where images will be saved.
    """
    logger.info("--- Starting Plot Generation ---")
    
    palette = _setup_style()
    hdf_file = os.path.join(data_path, "observation.hdf5")
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(hdf_file):
        logger.info(f"Error: Data file not found at {hdf_file}")
        return

    # 1. Load Data
    logger.info("Loading data...")
    try:
        stats_history = pd.read_hdf(hdf_file, key="stats_history_aggregated")
        pods_data = pd.read_hdf(hdf_file, key="pods")
        stats_data = pd.read_hdf(hdf_file, key="stats")
        nodes_data = pd.read_hdf(hdf_file, key="nodes")
        pods_energy_data = pd.read_hdf(hdf_file, key="pods_energy")
        run_stats_data = pd.read_hdf(hdf_file, key="run_stats")
    except Exception as e:
        logger.info(f"Error loading data from HDF5 file: {e}")
        return

    # 2. Generate and Save Service Quality Table
    logger.info("Generating Service Quality table...")
    try:
        left, right = "exp_scale_pausing", "exp_scale_rampup"
        failures = stats_history[stats_history["exp_workload"].isin([left, right])].groupby(["exp_branch", "exp_workload"])[["rq", "frq"]].sum()
        failures["Failure Rate"] = 100 * failures["frq"] / failures["rq"]
        failures = failures.unstack()
        failures["fr"] = failures["Failure Rate"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
        failures = failures.droplevel(1, axis=1).reset_index()[["exp_branch", "fr"]]

        latency = stats_history[stats_history["exp_workload"].isin([left, right])].groupby(["exp_branch", "exp_workload"])[["p50", "p95"]].mean().unstack() / 1000
        latency["p50_diff"] = latency["p50"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
        latency["p95_diff"] = latency["p95"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
        latency = latency.droplevel(1, axis=1).reset_index()[["exp_branch", "p50_diff", "p95_diff"]]

        pods = pods_data[pods_data["namespace"] == "tea-bench"].copy()
        pods["pod_name"] = pods["name"].apply(lambda x: "-".join(x.split("-")[0:2]))
        pods["type"] = pods["pod_name"].apply(lambda x: "pod" if x.startswith("teastore") else "function" if x.startswith("auth") else "infra")
        pods = pods[pods["type"].isin(["pod", "function"])]
        
        pods_usage = pods.groupby(RUN_VARS + ["run_time", "name", "pod_name", "type"])[["memory_usage", "cpu_usage"]].sum().reset_index()
        pods_usage["requested_cost"] = pods_usage.apply(_calc_request_based_billing, axis=1)
        pods_usage["used_cost"] = pods_usage.apply(_calc_usage_based_billing, axis=1)
        
        pods_mean_cost = pods_usage.groupby(RUN_VARS)[["requested_cost", "used_cost"]].sum().reset_index().groupby(["exp_branch", "exp_workload"])[["requested_cost", "used_cost"]].mean().reset_index()
        requests = stats_data.groupby(["exp_branch", "exp_workload"])[["Request Count", "Failure Count"]].sum().reset_index()
        requests["rq"] = requests["Request Count"] - requests["Failure Count"]
        
        pods_mean_cost_per_request = pods_mean_cost.merge(requests[["exp_branch", "exp_workload", "rq"]], on=["exp_branch", "exp_workload"])
        pods_mean_cost_per_request["requested_cost_per_r"] = (pods_mean_cost_per_request["requested_cost"] / pods_mean_cost_per_request["rq"]) * 100 * 1000
        pods_mean_cost_per_request["used_cost_per_r"] = (pods_mean_cost_per_request["used_cost"] / pods_mean_cost_per_request["rq"]) * 100 * 1000
        
        pods_cost_comp = pods_mean_cost_per_request[pods_mean_cost_per_request["exp_workload"] == left].merge(pods_mean_cost_per_request[pods_mean_cost_per_request["exp_workload"] == right], on="exp_branch", suffixes=("_left", "_right"))
        pods_cost_comp["requested_cost"] = pods_cost_comp.apply(lambda x: f'{x["requested_cost_left"]:.2f} - {x["requested_cost_right"]:.2f}', axis=1)
        pods_cost_comp["used_cost"] = pods_cost_comp.apply(lambda x: f'{x["used_cost_left"]:.2f} - {x["used_cost_right"]:.2f}', axis=1)
        pods_cost_comp["used_cost_per_r"] = pods_cost_comp.apply(lambda x: f'{x["used_cost_per_r_left"]:.2f} - {x["used_cost_per_r_right"]:.2f}', axis=1)
        
        main_table = latency.merge(failures, on="exp_branch").merge(pods_cost_comp[["exp_branch", "requested_cost", "used_cost", "used_cost_per_r"]], on="exp_branch")
        main_table = main_table[main_table["exp_branch"].isin(FULL_STACK_FOCUS)]
        main_table["exp_branch"] = main_table["exp_branch"].map(LABLE_NAMES)
        main_table.columns = ["Feature", "Latency p50 [s]", "Latency p95 [s]", "Failure Rate [%]", "Total Cost [$]", "Consumed Cost [$]", "Cost Per Request [¢/1000]"]
        
        table_path = os.path.join(output_path, "service_quality_table.csv")
        main_table.to_csv(table_path, index=False)
        logger.info(f"Service Quality table saved to {table_path}")
    except Exception as e:
        logger.info(f"Failed to generate service quality table: {e}")


    # 3. Generate and Save Resource Utilization & Overhead Plot
    logger.info("Generating Resource Utilization plot...")
    try:
        pods = pods_data.copy()
        pods["type"] = pods["name"].apply(lambda x: "-".join(x.split("-")[0:2]))
        pod_scale_behavior = pods.groupby(RUN_VARS + ["run_time", "type"])["type"].count().reset_index(name="count")
        pod_resource_utilization = pod_scale_behavior.apply(_calulate_resource_allowence, axis=1)
        
        real_pod_utilization = pods.groupby(RUN_VARS + ["run_time", "type"])[["cpu_usage", "memory_usage"]].sum()
        real_pod_utilization["r_cpu_usage"] = (real_pod_utilization["cpu_usage"] * 1000).astype(int)
        real_pod_utilization["r_memory_usage"] = real_pod_utilization["memory_usage"].astype(int)
        
        real_total_utilization = pod_resource_utilization.merge(real_pod_utilization.reset_index(), on=RUN_VARS + ["run_time", "type"])
        real_total_utilization = real_total_utilization.groupby(["exp_branch", "exp_workload"])[["r_cpu_usage", "r_memory_usage", "cpu_limit", "mem_limit", "cpu_max", "mem_max"]].sum()
        real_total_utilization["cpu_utilization"] = 100 * real_total_utilization["r_cpu_usage"] / real_total_utilization["cpu_limit"]
        real_total_utilization["mem_utilization"] = 100 * real_total_utilization["r_memory_usage"] / real_total_utilization["mem_limit"]
        
        nodes = nodes_data[nodes_data['instance'].isin(pods_data['instance'].unique())].copy()
        nodes["memory_usage"] = nodes.apply(_calculate_memory_usage, axis=1)
        nodes_sum = nodes.groupby(RUN_VARS + ['run_time', 'instance'])[["cpu_usage", "memory_usage", "wattage_kepler", "wattage_scaph"]].sum()
        nodes_sum['cost'] = nodes_sum.apply(_calculate_cost, axis=1)
        
        pods_sum = pods_data.groupby(RUN_VARS + ['run_time', 'instance'])[["cpu_usage", "memory_usage", "wattage_kepler", "wattage_scaph"]].sum()
        runtime_overhead_data = (nodes_sum - pods_sum).dropna()
        runtime_overhead_data['cost'] = runtime_overhead_data.apply(_calculate_cost, axis=1)
        
        runtime_overhead_cost = (100 * runtime_overhead_data.groupby(["exp_workload", "exp_branch"])[["cost"]].sum() /
                                 nodes_sum.groupby(["exp_workload", "exp_branch"])[["cost"]].sum())
        runtime_overhead_cost.reset_index(inplace=True)

        fig, ax = plt.subplots(1, 3, figsize=(14, 4))
        sns.set_context(rc={"font.size": 13, "axes.titlesize": 13, "axes.labelsize": 13, "xtick.labelsize": 13, "ytick.labelsize": 15})
        
        wls = ["exp_scale_rampup", "exp_scale_shaped", "exp_scale_pausing"]
        focus_data = real_total_utilization.reset_index()
        focus_data = focus_data[focus_data["exp_branch"].isin(FULL_STACK_FOCUS) & focus_data["exp_workload"].isin(wls)]
        
        sns.boxplot(data=focus_data, y="exp_branch", x="mem_utilization", ax=ax[0], color="C3")
        ax[0].set_xlabel("Mem Utilization (%)")
        ax[0].set_ylabel("")
        ax[0].set_yticklabels([LABLE_NAMES.get(x.get_text(), x.get_text()) for x in ax[0].get_yticklabels()])
        ax[0].set_xlim(0, 100)
        
        sns.boxplot(data=focus_data, y="exp_branch", x="cpu_utilization", ax=ax[1], color="C3")
        ax[1].set_xlabel("CPU Utilization (%)")
        ax[1].set_yticklabels([])
        ax[1].set_yticks([])
        ax[1].set_xlim(0, 100)
        
        fig.text(0.5, 0.98, 'Resource Utilization ($RU$)', ha='center', va='top', fontsize=14)

        overhead_data = runtime_overhead_cost[runtime_overhead_cost["exp_branch"].isin(FULL_STACK_FOCUS) & runtime_overhead_cost["exp_workload"].isin(wls)]
        sns.boxplot(data=overhead_data, y="exp_branch", x="cost", color="C9", ax=ax[2])
        ax[2].set_ylabel("")
        ax[2].set_yticklabels([])
        ax[2].set_yticks([])
        ax[2].set_xlabel("Overhead (%)")
        ax[2].set_title("Platform Overhead ($RO$)")
        ax[2].set_xlim(0, 100)

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        plot_path = os.path.join(output_path, "resource_utilization_overhead.png")
        fig.savefig(plot_path)
        plt.close(fig)
        logger.info(f"Resource utilization plot saved to {plot_path}")
    except Exception as e:
        logger.info(f"Failed to generate resource utilization plot: {e}")

    # 4. Generate and Save Energy Consumption & Efficiency Plot
    logger.info("Generating Energy Consumption plot...")
    try:
        wdf = pods_energy_data.merge(how="left", right=run_stats_data, on=RUN_VARS, validate="one_to_one")
        wdf["ws_per_rq"] = wdf["wattage_kepler"] / wdf["Success Count"]
        wdff = wdf[wdf.exp_branch.isin(FULL_STACK_FOCUS)]
        
        pods = pods_data.copy()
        pods["pod_name"] = pods["name"].apply(lambda x: "-".join(x.split("-")[0:2]))
        pods["type"] = pods["pod_name"].apply(lambda x: "pod" if x.startswith("teastore") else "function" if x.startswith("auth") else "infra")
        pods = pods[pods["type"] != "infra"]
        pods["service"] = pods["pod_name"]

        def _allowance_for_cost(row):
            service = row["service"]
            if service in GENERAL_ALLOWANCE:
                row["cpu_limit"] = GENERAL_ALLOWANCE[service]["cpu"]
                row["mem_limit"] = GENERAL_ALLOWANCE[service]["memory"]
            return row

        pods = pods.apply(_allowance_for_cost, axis=1)
        pods["mem_utilization"] = 100 * pods["memory_usage"] / pods["mem_limit"]
        pods["cpu_utilization"] = 100 * (1000 * pods["cpu_usage"]) / pods["cpu_limit"]
        pods["under_utilized"] = ((pods["mem_utilization"] < 49) & (pods["cpu_utilization"] < 49)).astype(int)
        
        service_utilization = pods.groupby(RUN_VARS + ["service", "run_time"])['wattage_kepler', 'under_utilized'].sum().reset_index()
        service_utilization['waste'] = service_utilization['wattage_kepler'] * service_utilization['under_utilized']
        scaling_waste = service_utilization.groupby(["exp_branch", "exp_workload"])["waste"].sum().reset_index()

        fig = plt.figure(figsize=(13, 4))
        gs = gridspec.GridSpec(1, 3, width_ratios=[1, 1, 1.1])
        sns.set_context(rc={"font.size": 13, "axes.titlesize": 13, "axes.labelsize": 13, "xtick.labelsize": 13, "ytick.labelsize": 15})
        
        g = fig.add_subplot(gs[0:2])
        sns.boxplot(data=wdff, hue="exp_branch", hue_order=SHORT_LABELS.keys(), y="ws_per_rq", x="exp_workload", palette=palette, ax=g)
        g.set_ylabel("Energy per Request [Ws]")
        g.set_xlabel("Workloads")
        g.set_title("Request Consumption per Workload ($WR$)")
        g.set_xticklabels([LABLE_NAMES.get(x.get_text(), x.get_text()) for x in g.get_xticklabels()])
        handles, labels = g.get_legend_handles_labels()
        g.legend(handles, [LABLE_NAMES.get(label, label) for label in labels], title="")

        f = fig.add_subplot(gs[2])
        waste_data = scaling_waste[scaling_waste["exp_branch"].isin(FULL_STACK_FOCUS)]
        sns.boxplot(data=waste_data, x="exp_branch", order=SHORT_LABELS.keys(), y="waste", hue="exp_branch", ax=f, palette=palette, hue_order=SHORT_LABELS.keys())
        f.set_title("Resource Efficiency ($RE$)")
        f.set_xlabel("")
        f.set_ylabel("Scaling Waste [Ws]")
        f.set_xticklabels([SHORT_LABELS.get(x.get_text(), x.get_text()) for x in f.get_xticklabels()])

        plt.tight_layout()
        plot_path = os.path.join(output_path, "energy_and_efficiency.png")
        fig.savefig(plot_path)
        plt.close(fig)
        logger.info(f"Energy and efficiency plot saved to {plot_path}")
    except Exception as e:
        logger.info(f"Failed to generate energy consumption plot: {e}")

    logger.info("--- Plot Generation Complete ---")