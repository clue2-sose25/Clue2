import os
import pathlib
import warnings
import json

import glasbey
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from clue_deployer.src.logger import logger

warnings.filterwarnings('ignore')

# --- Pricing Constants (AWS Frankfurt, fallback values) ---
MEMORY_SECOND_PRICE = 0.00511 / 1024 / 60  # $/MBs per minute
VCPU_SECOND_PRICE = 0.04656 / 60           # $/vCPU per minute
SERVERLESS_PRICE = 0.0000166667            # $/GB-s (Lambda)

# --- Dynamic Experiment Discovery and Configuration ---
def discover_experiments(base_dir):
    """
    Recursively discover all experiment runs and their configurations.
    Returns a list of dicts with experiment metadata and paths.
    """
    experiments = []
    for root, dirs, files in os.walk(base_dir):
        if 'experiment.json' in files:
            exp_path = os.path.join(root, 'experiment.json')
            try:
                with open(exp_path, 'r') as f:
                    config = json.load(f)
                # Add useful metadata from the path structure
                parts = pathlib.Path(root).parts
                # Expect: .../<date>/<label>/<branch>/<iteration>
                if len(parts) >= 4:
                    experiments.append({
                        'config': config,
                        'path': root,
                        'date': parts[-4],
                        'label': parts[-3],
                        'branch': parts[-2],
                        'iteration': parts[-1],
                    })
                else:
                    experiments.append({'config': config, 'path': root})
            except Exception as e:
                logger.info(f"Failed to load {exp_path}: {e}")
    return experiments

# --- Helper Functions (Dynamic) ---
def _calc_request_based_billing(row, config):
    # Use resource_limits from experiment.json
    pod_name = row["pod_name"]
    resource_limits = config.get("resource_limits", {})
    if pod_name in resource_limits:
        conf = resource_limits[pod_name]
        return conf["memory"] * MEMORY_SECOND_PRICE + np.ceil(conf["cpu"] / 1000) * VCPU_SECOND_PRICE
    elif pod_name.startswith("auth"):  # fallback for serverless
        return 500 * SERVERLESS_PRICE
    return 0

def _calc_usage_based_billing(row, config):
    if row["type"] == "pod":
        return row["memory_usage"] * MEMORY_SECOND_PRICE + np.ceil(row["cpu_usage"]) * VCPU_SECOND_PRICE
    elif row["type"] == "function":
        return row["memory_usage"] * SERVERLESS_PRICE
    return 0

def _calculate_maximum_resource_allowance(config):
    # Use resource_limits and scaling from experiment.json
    scale = config.get("resource_limits", {})
    max_allowance = {"cpu": 0, "memory": 0}
    for pod_name, pod_conf in scale.items():
        for resource, value in pod_conf.items():
            max_allowance[resource] += value
    return max_allowance

def _calulate_resource_allowence(row, config):
    # Use resource_limits from experiment.json
    resource_limits = config.get("resource_limits", {})
    pod_type = row["type"]
    if pod_type in resource_limits:
        cpu = resource_limits[pod_type]["cpu"]
        memory = resource_limits[pod_type]["memory"]
        row["cpu_limit"] = cpu * row["count"]
        row["mem_limit"] = memory * row["count"]
        row["cpu_max"] = cpu
        row["mem_max"] = memory
    return row

def _calculate_cost(row, config):
    ws_price = 0.5 / 3_600_000
    return (row['memory_usage'] * MEMORY_SECOND_PRICE +
            np.ceil(row["cpu_usage"]) * VCPU_SECOND_PRICE +
            (row.get("wattage_kepler", 0) * ws_price))

def _calculate_memory_usage(row, config):
    return row['memory_usage']


# --- Main Plotting Function ---

def generate_plots(data_path: str, output_path: str):
    """
    Generates and saves plots from the experiment data.

    Args:
        data_path: Path to the directory containing the experiment CSV files.
        output_path: Path to the directory where images will be saved.
    """
    logger.info("--- Starting Plot Generation ---")
    
    palette = _setup_style()
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)

    # 1. Load Data
    logger.info("Loading data...")
    # Load experiment.json to get SUT name
    experiment_json_path = os.path.join(data_path, "experiment.json")
    with open(experiment_json_path, "r") as f:
        experiment_config = json.load(f)
    sut_path = experiment_config.get("sut_path", "teastore")

    # Use SUT name to find the correct stats and pod files
    stats_history_file = os.path.join(data_path, f"{sut_path}_stats_history.csv")
    stats_file = os.path.join(data_path, f"{sut_path}_stats.csv")
    pods_file = [f for f in os.listdir(data_path) if f.startswith(f"measurements_pod") and f.endswith('.csv')]
    nodes_file = [f for f in os.listdir(data_path) if f.startswith('measurements_node') and f.endswith('.csv')]

    try:
        stats_history = pd.read_csv(stats_history_file)
        pods_data = pd.read_csv(os.path.join(data_path, pods_file[0])) if pods_file else None
        stats_data = pd.read_csv(stats_file)
        nodes_data = pd.read_csv(os.path.join(data_path, nodes_file[0])) if nodes_file else None
        pods_energy_data = pd.read_csv(os.path.join(data_path, "pods_energy.csv"))
        run_stats_data = pd.read_csv(os.path.join(data_path, "run_stats.csv"))
    except Exception as e:
        logger.info(f"Error loading data: {e}")
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
        
        table_path = os.path.join(output_path, "service_quality_table.json")
        main_table.to_json(table_path, orient="records", indent=2)
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

    # --- Node-level Plots ---
    if nodes_data_df is not None:
        try:
            # 1. Node CPU Usage Over Time
            fig, ax = plt.subplots(figsize=(10, 6))
            for instance, group in nodes_data_df.groupby('instance'):
                ax.plot(pd.to_datetime(group['observation_time']), group['cpu_usage'], label=f'Node {instance}')
            ax.set_title('Node CPU Usage Over Time')
            ax.set_xlabel('Time')
            ax.set_ylabel('CPU Usage (cores)')
            ax.legend()
            plot_path = os.path.join(output_path, "node_cpu_usage_over_time.png")
            fig.tight_layout()
            fig.savefig(plot_path)
            plt.close(fig)
            logger.info(f"Node CPU usage plot saved to {plot_path}")

            # 2. Node Memory Usage Over Time
            fig, ax = plt.subplots(figsize=(10, 6))
            for instance, group in nodes_data_df.groupby('instance'):
                ax.plot(pd.to_datetime(group['observation_time']), group['memory_usage'], label=f'Node {instance}')
            ax.set_title('Node Memory Usage Over Time')
            ax.set_xlabel('Time')
            ax.set_ylabel('Memory Usage (GB)')
            ax.legend()
            plot_path = os.path.join(output_path, "node_memory_usage_over_time.png")
            fig.tight_layout()
            fig.savefig(plot_path)
            plt.close(fig)
            logger.info(f"Node memory usage plot saved to {plot_path}")

            # 3. Node Power Consumption (Wattage Kepler) Over Time
            if 'wattage_kepler' in nodes_data_df.columns:
                fig, ax = plt.subplots(figsize=(10, 6))
                for instance, group in nodes_data_df.groupby('instance'):
                    ax.plot(pd.to_datetime(group['observation_time']), group['wattage_kepler'], label=f'Node {instance}')
                ax.set_title('Node Power Consumption (Kepler) Over Time')
                ax.set_xlabel('Time')
                ax.set_ylabel('Wattage (Kepler)')
                ax.legend()
                plot_path = os.path.join(output_path, "node_wattage_kepler_over_time.png")
                fig.tight_layout()
                fig.savefig(plot_path)
                plt.close(fig)
                logger.info(f"Node wattage kepler plot saved to {plot_path}")
        except Exception as e:
            logger.info(f"Failed to generate node-level plots: {e}")
    logger.info("--- Plot Generation Complete ---")

def _setup_style():
    pd.set_option('display.max_columns', None)
    sns.set_theme(rc={'figure.figsize': (12, 6)})
    sns.set_context("paper")
    sns.set_style("whitegrid")
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    return sns.color_palette("tab10")

def generate_plots_dynamic(data_base_path: str, output_path: str):
    """
    Dynamically generates and saves plots from all discovered experiment data.
    Args:
        data_base_path: Path to the base data directory (e.g., 'data').
        output_path: Path to the directory where images will be saved.
    """
    logger.info("--- Starting Dynamic Plot Generation ---")
    experiments = discover_experiments(data_base_path)
    if not experiments:
        logger.info("No experiments found.")
        return

    palette = _setup_style()
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)

    # Build dynamic label/grouping info
    label_names = {}
    short_labels = {}
    all_branches = set()
    all_workloads = set()
    for exp in experiments:
        config = exp['config']
        branch = exp.get('branch', config.get('target_branch', 'unknown'))
        label = config.get('name', branch)
        label_names[branch] = label
        short_labels[branch] = label[:2].upper()
        all_branches.add(branch)
        if 'workload_settings' in config:
            for k, v in config['workload_settings'].items():
                all_workloads.add(str(v))

    # --- Aggregate Data Across Experiments from CSVs ---
    all_stats_history = []
    all_pods_data = []
    all_stats_data = []
    all_nodes_data = []
    all_failures_data = []
    for exp in experiments:
        config = exp['config']
        exp_path = exp['path']
        branch = exp.get('branch', config.get('target_branch', 'unknown'))
        label = label_names[branch]
        def try_load_csv(filename):
            fpath = os.path.join(exp_path, filename)
            if os.path.exists(fpath):
                try:
                    df = pd.read_csv(fpath)
                    df['exp_branch'] = branch
                    df['exp_label'] = label
                    df['exp_path'] = exp_path
                    return df
                except Exception as e:
                    logger.info(f"Failed to load {fpath}: {e}")
            return None
        # Load all relevant CSVs using the SUT name from experiment.json
        sut_path = config.get("sut_path")
        stats_history = try_load_csv(f'{sut_path}_stats_history.csv')
        pods_file = [f for f in os.listdir(exp_path) if f.startswith('measurements_pod') and f.endswith('.csv')]
        pods_data = try_load_csv(pods_file[0]) if pods_file else None
        stats_data = try_load_csv(f'{sut_path}_stats.csv')
        nodes_file = [f for f in os.listdir(exp_path) if f.startswith('measurements_node') and f.endswith('.csv')]
        nodes_data = try_load_csv(nodes_file[0]) if nodes_file else None
        failures_data = try_load_csv(f'{sut_path}_failures.csv')
        if stats_history is not None:
            all_stats_history.append(stats_history)
        if pods_data is not None:
            all_pods_data.append(pods_data)
        if stats_data is not None:
            all_stats_data.append(stats_data)
        if nodes_data is not None:
            all_nodes_data.append(nodes_data)
        if failures_data is not None:
            all_failures_data.append(failures_data)

    # Combine data
    stats_history_df = pd.concat(all_stats_history, ignore_index=True) if all_stats_history else None
    pods_data_df = pd.concat(all_pods_data, ignore_index=True) if all_pods_data else None
    stats_data_df = pd.concat(all_stats_data, ignore_index=True) if all_stats_data else None
    nodes_data_df = pd.concat(all_nodes_data, ignore_index=True) if all_nodes_data else None
    failures_data_df = pd.concat(all_failures_data, ignore_index=True) if all_failures_data else None

    # --- Service Quality Table and Plot ---
    if stats_history_df is not None and stats_data_df is not None:
        try:
            left, right = "exp_scale_pausing", "exp_scale_rampup"
            failures = stats_history_df[stats_history_df["exp_workload"].isin([left, right])].groupby(["exp_branch", "exp_workload"])[["rq", "frq"]].sum()
            failures["Failure Rate"] = 100 * failures["frq"] / failures["rq"]
            failures = failures.unstack()
            failures["fr"] = failures["Failure Rate"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
            failures = failures.droplevel(1, axis=1).reset_index()[["exp_branch", "fr"]]

            latency = stats_history_df[stats_history_df["exp_workload"].isin([left, right])].groupby(["exp_branch", "exp_workload"])[["p50", "p95"]].mean().unstack() / 1000
            latency["p50_diff"] = latency["p50"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
            latency["p95_diff"] = latency["p95"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
            latency = latency.droplevel(1, axis=1).reset_index()[["exp_branch", "p50_diff", "p95_diff"]]

            requests = stats_data_df.groupby(["exp_branch", "exp_workload"])[["Request Count", "Failure Count"]].sum().reset_index()
            requests["rq"] = requests["Request Count"] - requests["Failure Count"]

            main_table = latency.merge(failures, on="exp_branch")
            main_table.columns = ["exp_branch", "Latency p50 [s]", "Latency p95 [s]", "Failure Rate [%]", "Failure Rate"]
            table_path = os.path.join(output_path, "service_quality_table.json")
            main_table.to_json(table_path, orient="records", indent=2)
            logger.info(f"Service Quality table saved to {table_path}")

            # Plot
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=main_table, x='exp_branch', y='Failure Rate [%]', ax=ax, palette=palette)
            ax.set_title('Failure Rate by Experiment')
            plot_path = os.path.join(output_path, "failure_rate_by_experiment.png")
            fig.tight_layout()
            fig.savefig(plot_path)
            plt.close(fig)
            logger.info(f"Failure rate plot saved to {plot_path}")
        except Exception as e:
            logger.info(f"Failed to generate service quality plot: {e}")

    # --- Concatenate Iterations for Experiment-level Analysis ---
    try:
        # Group by experiment (date/label/experiment) and concatenate all iterations
        experiment_key = (exp.get('date'), exp.get('label'), exp.get('branch'))
        if 'experiment_groups' not in locals():
            experiment_groups = {}
        if experiment_key not in experiment_groups:
            experiment_groups[experiment_key] = {
                'stats_history': [],
                'pods_data': [],
                'stats_data': [],
                'nodes_data': [],
                'failures_data': []
            }
        if stats_history is not None:
            experiment_groups[experiment_key]['stats_history'].append(stats_history)
        if pods_data is not None:
            experiment_groups[experiment_key]['pods_data'].append(pods_data)
        if stats_data is not None:
            experiment_groups[experiment_key]['stats_data'].append(stats_data)
        if nodes_data is not None:
            experiment_groups[experiment_key]['nodes_data'].append(nodes_data)
        if failures_data is not None:
            experiment_groups[experiment_key]['failures_data'].append(failures_data)

    # After the experiment loop, concatenate all iterations for each experiment
    all_stats_history = []
    all_pods_data = []
    all_stats_data = []
    all_nodes_data = []
    all_failures_data = []
    for group in experiment_groups.values():
        if group['stats_history']:
            all_stats_history.append(pd.concat(group['stats_history'], ignore_index=True))
        if group['pods_data']:
            all_pods_data.append(pd.concat(group['pods_data'], ignore_index=True))
        if group['stats_data']:
            all_stats_data.append(pd.concat(group['stats_data'], ignore_index=True))
        if group['nodes_data']:
            all_nodes_data.append(pd.concat(group['nodes_data'], ignore_index=True))
        if group['failures_data']:
            all_failures_data.append(pd.concat(group['failures_data'], ignore_index=True))

    # Combine concatenated data
    stats_history_df = pd.concat(all_stats_history, ignore_index=True) if all_stats_history else None
    pods_data_df = pd.concat(all_pods_data, ignore_index=True) if all_pods_data else None
    stats_data_df = pd.concat(all_stats_data, ignore_index=True) if all_stats_data else None
    nodes_data_df = pd.concat(all_nodes_data, ignore_index=True) if all_nodes_data else None
    failures_data_df = pd.concat(all_failures_data, ignore_index=True) if all_failures_data else None

    # --- Service Quality Table and Plot (Experiment-level) ---
    if stats_history_df is not None and stats_data_df is not None:
        try:
            left, right = "exp_scale_pausing", "exp_scale_rampup"
            failures = stats_history_df[stats_history_df["exp_workload"].isin([left, right])].groupby(["exp_branch", "exp_workload"])[["rq", "frq"]].sum()
            failures["Failure Rate"] = 100 * failures["frq"] / failures["rq"]
            failures = failures.unstack()
            failures["fr"] = failures["Failure Rate"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
            failures = failures.droplevel(1, axis=1).reset_index()[["exp_branch", "fr"]]

            latency = stats_history_df[stats_history_df["exp_workload"].isin([left, right])].groupby(["exp_branch", "exp_workload"])[["p50", "p95"]].mean().unstack() / 1000
            latency["p50_diff"] = latency["p50"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
            latency["p95_diff"] = latency["p95"].apply(lambda x: f'{x[left]:>2.2f} - {x[right]:>2.2f}', axis=1)
            latency = latency.droplevel(1, axis=1).reset_index()[["exp_branch", "p50_diff", "p95_diff"]]

            requests = stats_data_df.groupby(["exp_branch", "exp_workload"])[["Request Count", "Failure Count"]].sum().reset_index()
            requests["rq"] = requests["Request Count"] - requests["Failure Count"]

            main_table = latency.merge(failures, on="exp_branch")
            main_table.columns = ["exp_branch", "Latency p50 [s]", "Latency p95 [s]", "Failure Rate [%]", "Failure Rate"]
            table_path = os.path.join(output_path, "service_quality_table_experiment_level.json")
            main_table.to_json(table_path, orient="records", indent=2)
            logger.info(f"Service Quality table (experiment-level) saved to {table_path}")

            # Plot
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=main_table, x='exp_branch', y='Failure Rate [%]', ax=ax, palette=palette)
            ax.set_title('Failure Rate by Experiment (Experiment-level)')
            plot_path = os.path.join(output_path, "failure_rate_by_experiment_level.png")
            fig.tight_layout()
            fig.savefig(plot_path)
            plt.close(fig)
            logger.info(f"Failure rate plot (experiment-level) saved to {plot_path}")
        except Exception as e:
            logger.info(f"Failed to generate service quality plot (experiment-level): {e}")