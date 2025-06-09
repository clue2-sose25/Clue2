import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glasbey
import seaborn as sns
import matplotlib.gridspec as gridspec
from clue_deployer.src.logger import logger

palette = glasbey.create_block_palette(
    [4, 3, 3, 2, 2],
    colorblind_safe=True,
    cvd_severity=90
)
sns.set_palette(palette)

# ─── Pricing & Pod Configuration ─────────────────────────────────────────────

# cost in $ per second of wall-clock energy (Germany avg kWh price)
WS_PRICE = 0.5 / 3_600_000  

# AWS cost-model
SERVERLESS_PRICE = 0.0000166667     # $ per GB-s (AWS Lambda, Frankfurt)
MEMORY_SECOND_PRICE = 0.00511 / 1024 / 60   # $ per MB-s (AWS Fargate mem)
VCPU_SECOND_PRICE   = 0.04656 / 60          # $ per vCPU-s (AWS Fargate vCPU)

NODE_MODEL = {
    "sm-gpu": 32704316//1024,
    "ise-knode6": 32719632//1024,
    "ise-knode1": 32761604//1024,
}

# pod resource request configurations (cpu in millicores, memory in MiB)
POD_CONFIGURATION = {
    "teastore-recommender": {"cpu": 2600, "memory": 1332},
    "teastore-webui":       {"cpu": 1300, "memory": 1950},
    "teastore-image":       {"cpu": 1300, "memory": 1950},
    "teastore-auth":        {"cpu":  585, "memory": 1332},
    "teastore-registry":    {"cpu": 1000, "memory": 1024},
    "teastore-persistence": {"cpu": 1000, "memory": 1024},
    "teastore-db":          {"cpu": 1000, "memory": 1024},
    "teastore-all":         {"cpu": 1950, "memory": 2663},
    "auth":                 {"cpu":  500, "memory":  500},
}

GENERAL_ALLOWANCE = {
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

RESOURCE_SCALE = {
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

# runs are indexed by these columns in the HDF5
RUN_VARS = ['exp_start', 'exp_branch', 'exp_workload', 'run_iteration']

# for comparing two workloads side-by-side
LEFT_WORKLOAD  = "exp_scale_pausing"
RIGHT_WORKLOAD = "exp_scale_rampup"

# labels for branches & workloads
LABEL_NAMES = {
    "baseline_vanilla_full":           "Microservices",
    "monolith_feature_monolith_full":  "Monolith",
    "serverless_feature_serverless_full": "Serverless",
    "jvm_jvm-impoove_full":            "Runtime Improvement",
    "norec_feature_norecommendations_full": "Service Reduction",
    "exp_scale_pausing":                "Pausing",
    "exp_scale_rampup":                 "Stress",
    "exp_scale_fixed":                  "Fixed",
    "exp_scale_shaped":                 "Regular",
}

SHORT_LABELS = {
    "baseline_vanilla_full": "MS",
    'monolith_feature_monolith_full': "ML",
    'serverless_feature_serverless_full' : "SL",
    'jvm_jvm-impoove_full': "RT",
    'norec_feature_norecommendations_full' : "SR",
}

# only show these branches in the final table
FULL_STACK_FOCUS = [
    "baseline_vanilla_full",
    "monolith_feature_monolith_full",
    "serverless_feature_serverless_full",
    "norec_feature_norecommendations_full",
    "jvm_jvm-impoove_full",
]

# ─── Helpers ───────────────────────────────────────────────────────────────────

def calc_request_billing(row):
    """Billing cost based on requested resources."""
    if row["type"] == "pod":
        conf = POD_CONFIGURATION[row["pod_name"]]
        mem_cost = conf["memory"] * MEMORY_SECOND_PRICE
        cpu_cost = np.ceil(conf["cpu"] / 1000) * VCPU_SECOND_PRICE
        return mem_cost + cpu_cost
    else: 
        return 500 * SERVERLESS_PRICE

def calc_usage_billing(row):
    """Billing cost based on actual usage."""
    if row["type"] == "pod":
        mem_cost = row["memory_usage"] * MEMORY_SECOND_PRICE
        cpu_cost = np.ceil(row["cpu_usage"]) * VCPU_SECOND_PRICE
        return mem_cost + cpu_cost
    else:
        return row["memory_usage"] * SERVERLESS_PRICE

# ─── Data Loading ─────────────────────────────────────────────────────────────

def load_all_data(hdf5_path: str = "01 Data/observation.hdf5"):
    """
    Reads all DataFrame keys from the HDF5 file and returns them.
    """
    stats_hist   = pd.read_hdf(hdf5_path, key="stats_history_aggregated")
    pods         = pd.read_hdf(hdf5_path, key="pods")
    stats        = pd.read_hdf(hdf5_path, key="stats")
    nodes        = pd.read_hdf(hdf5_path, key="nodes")
    pods_energy  = pd.read_hdf(hdf5_path, key="pods_energy")
    run_stats    = pd.read_hdf(hdf5_path, key="run_stats")
    return stats_hist, pods, stats, nodes, pods_energy, run_stats

# ─── Service Quality Table ───────────────────────────────────────────────────

def compute_service_quality_table(stats_hist, pods, stats):
    """
    Builds the main performance & quality comparison table
    between LEFT_WORKLOAD and RIGHT_WORKLOAD.
    Returns a styled DataFrame (pandas Styler).
    """
    # 1) Failure rates
    sel = stats_hist["exp_workload"].isin([LEFT_WORKLOAD, RIGHT_WORKLOAD])
    failures = (
        stats_hist[sel]
        .groupby(["exp_branch", "exp_workload"])[["rq", "frq"]]
        .sum()
    )
    failures["Failure Rate"] = 100 * failures["frq"] / failures["rq"]
    failures = failures["Failure Rate"].unstack().reset_index()
    failures["Failure Rate Δ"] = failures.apply(
        lambda r: f"{r[LEFT_WORKLOAD]:>2.2f} - {r[RIGHT_WORKLOAD]:>2.2f}", axis=1
    )
    failures = failures[["exp_branch", "Failure Rate Δ"]]

    # 2) Latency differences (p50 & p95 in seconds)
    lat = (
        stats_hist[sel]
        .groupby(["exp_branch", "exp_workload"])[["p50", "p95"]]
        .mean()
        / 1000
    ).unstack()
    lat = lat.reset_index()
    lat["p50 Δ"] = lat.apply(
        lambda r: f"{r[('p50', LEFT_WORKLOAD)]:>2.2f} - {r[('p50', RIGHT_WORKLOAD)]:>2.2f}",
        axis=1
    )
    lat["p95 Δ"] = lat.apply(
        lambda r: f"{r[('p95', LEFT_WORKLOAD)]:>2.2f} - {r[('p95', RIGHT_WORKLOAD)]:>2.2f}",
        axis=1
    )
    latency = lat[["exp_branch", "p50 Δ", "p95 Δ"]]

    # 3) Pod costs per request
    # annotate pod type
    pods = pods.copy()
    pods["pod_name"] = pods["name"].apply(lambda x: "-".join(x.split("-")[:2]))
    pods["type"] = pods["pod_name"].apply(
        lambda n: "pod" if n.startswith("teastore") else "function" if n.startswith("auth") else "infra"
    )
    pods = pods[pods["type"].isin(["pod","function"])]
    usage = (
        pods
        .groupby(RUN_VARS + ["run_time", "name", "pod_name", "type"])
        [["memory_usage", "cpu_usage"]]
        .sum()
        .reset_index()
    )
    usage["requested_cost"] = usage.apply(calc_request_billing, axis=1)
    usage["used_cost"]      = usage.apply(calc_usage_billing, axis=1)

    # average cost per branch/workload
    mean_cost = (
        usage
        .groupby(RUN_VARS)[["requested_cost","used_cost"]]
        .sum()
        .reset_index()
        .groupby(["exp_branch","exp_workload"])
        .mean()
        .reset_index()
    )

    # requests count
    reqs = (
        stats
        .groupby(["exp_branch","exp_workload"])[["Request Count","Failure Count"]]
        .sum()
        .reset_index()
    )
    reqs["rq"] = reqs["Request Count"] - reqs["Failure Count"]

    cost_req = mean_cost.merge(reqs[["exp_branch","exp_workload","rq"]], on=["exp_branch","exp_workload"])
    cost_req["requested_per_req"] = (cost_req["requested_cost"] / cost_req["rq"]) * 100 * 1000
    cost_req["used_per_req"]      = (cost_req["used_cost"]      / cost_req["rq"]) * 100 * 1000

    # compare left vs right workloads
    left_df  = cost_req[cost_req["exp_workload"] == LEFT_WORKLOAD]
    right_df = cost_req[cost_req["exp_workload"] == RIGHT_WORKLOAD]
    comp = left_df.merge(right_df, on="exp_branch", suffixes=("_L","_R"))
    comp["Cost Δ (requested)"] = comp.apply(
        lambda r: f"{r['requested_cost_L']:>2.2f} - {r['requested_cost_R']:>2.2f}", axis=1
    )
    comp["Cost Δ (used)"] = comp.apply(
        lambda r: f"{r['used_cost_L']:>2.2f} - {r['used_cost_R']:>2.2f}", axis=1
    )
    comp["Cost Δ (/req)"] = comp.apply(
        lambda r: f"{r['used_per_req_L']:>2.2f} - {r['used_per_req_R']:>2.2f}", axis=1
    )
    pods_cost = comp[["exp_branch","Cost Δ (requested)","Cost Δ (used)","Cost Δ (/req)"]]

    # 4) Merge into final table
    main = (
        latency
        .merge(failures, on="exp_branch")
        .merge(pods_cost, on="exp_branch")
    )
    main = main[main["exp_branch"].isin(FULL_STACK_FOCUS)]
    main["Feature"] = main["exp_branch"].map(LABEL_NAMES)
    main = main.set_index("Feature")[[
        "p50 Δ","p95 Δ","Failure Rate Δ","Cost Δ (requested)","Cost Δ (used)","Cost Δ (/req)"
    ]]

    # wrap in Styler for HTML / LaTeX formatting downstream
    return main.style.set_caption(
        f"Performance & Quality Δ between {LABEL_NAMES[LEFT_WORKLOAD]} and {LABEL_NAMES[RIGHT_WORKLOAD]}"
    )

# ─── Resource Utilization ────────────────────────────────────────────────────

def calculate_maximum_resource_allowance(exp_branch: str):
    scale = RESOURCE_SCALE[exp_branch]
    max_allowance = {"cpu": 0, "memory": 0}
    for pod_name, pod_scale in scale.items():
        for resource, value in GENERAL_ALLOWANCE[pod_name].items():
            max_allowance[resource] += value * pod_scale
    return max_allowance

def calculate_resource_allowance(row):
    if row["type"] not in GENERAL_ALLOWANCE and not row["type"].startswith("auth"):
        return row
    if row["type"].startswith("auth"):
        cpu, memory = GENERAL_ALLOWANCE["auth"].values()
        max_count = RESOURCE_SCALE[row["exp_branch"]]["auth"]
    else:
        cpu  = GENERAL_ALLOWANCE[row["type"]]["cpu"]
        memory = GENERAL_ALLOWANCE[row["type"]]["memory"]
        max_count = RESOURCE_SCALE[row["exp_branch"]][row["type"]]
    row["cpu_limit"] = cpu * row["count"]
    row["mem_limit"] = memory * row["count"]
    row["cpu_max"]   = cpu * max_count
    row["mem_max"]   = memory * max_count
    return row

def compute_resource_utilization(pods_df):
    # build pod scale behavior
    pods_df = pods_df.copy()
    pods_df["type"] = pods_df["name"].apply(lambda x: "-".join(x.split("-")[:2]))
    pod_scale = (
        pods_df
        .groupby(RUN_VARS + ["run_time","type"])
        .size()
        .reset_index(name="count")
        .apply(calculate_resource_allowance, axis=1)
    )

    real_usage = (
        pods_df
        .groupby(RUN_VARS + ["run_time","type"])[["cpu_usage","memory_usage"]]
        .sum()
        .assign(
            r_cpu_usage=lambda df: (df.cpu_usage * 1000).astype(int),
            r_memory_usage=lambda df: df.memory_usage.astype(int)
        )
        .reset_index()
    )

    merged = pod_scale.merge(real_usage, on=RUN_VARS + ["run_time","type"])
    totals = (
        merged
        .groupby(["exp_branch","exp_workload"])
        [["r_cpu_usage","r_memory_usage","cpu_limit","mem_limit","cpu_max","mem_max"]]
        .sum()
    )
    totals["r_cpu_utilization"] = 100 * totals["r_cpu_usage"] / totals["cpu_max"]
    totals["r_mem_utilization"] = 100 * totals["r_memory_usage"] / totals["mem_max"]
    totals["t_cpu_utilization"] = 100 * totals["cpu_limit"]   / totals["cpu_max"]
    totals["t_mem_utilization"] = 100 * totals["mem_limit"]   / totals["mem_max"]
    totals["cpu_utilization"]   = 100 * totals["r_cpu_usage"] / totals["cpu_limit"]
    totals["mem_utilization"]   = 100 * totals["r_memory_usage"] / totals["mem_limit"]
    return totals.reset_index()

# ─── Platform Overhead Cost ──────────────────────────────────────────────────

def calculate_node_cost(row):
    return (
        row["memory_usage"] * MEMORY_SECOND_PRICE
        + np.ceil(row["cpu_usage"]) * VCPU_SECOND_PRICE
        + row["wattage_kepler"] * WS_PRICE
    )

def compute_platform_overhead(nodes_df, pods_df):
    # node-level cost
    nodes = (
        nodes_df[nodes_df.instance.isin(pods_df.instance.unique())]
        .copy()
        .assign(
            memory_usage=lambda df: df.apply(
                lambda r: r["memory_usage"] * NODE_MODEL[r["instance"]], axis=1
            )
        )
        .groupby(RUN_VARS + ["run_time","instance"])
        [["cpu_usage","memory_usage","wattage_kepler"]]
        .sum()
    )
    nodes["cost"] = nodes.apply(calculate_node_cost, axis=1)

    # pod-level sum
    pods_cost = (
        pods_df
        .groupby(RUN_VARS + ["run_time","instance"])
        [["cpu_usage","memory_usage","wattage_kepler"]]
        .sum()
    )
    runtime_overhead = nodes.subtract(pods_cost, fill_value=0)
    runtime_overhead["cost"] = runtime_overhead.apply(calculate_node_cost, axis=1)

    overhead_pct = (
        100
        * runtime_overhead
            .groupby(["exp_workload","exp_branch"])["cost"]
            .sum()
        / nodes
            .groupby(["exp_workload","exp_branch"])["cost"]
            .sum()
    ).reset_index()
    return overhead_pct

# ─── Plot Resource Utilization & Overhead ────────────────────────────────────

def plot_utilization_and_overhead(util_df, overhead_df):
    warnings.filterwarnings("ignore")
    focus = FULL_STACK_FOCUS
    workloads = [RIGHT_WORKLOAD, "exp_scale_shaped", LEFT_WORKLOAD]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    sns.set_context(rc={"font.size":13, "axes.titlesize":13})

    # Memory Utilization boxplot
    sns.boxplot(
        data=util_df.query("exp_branch in @focus and exp_workload in @workloads"),
        y="exp_branch", x="mem_utilization",
        ax=axes[0], color="C3"
    )
    axes[0].set(xlabel="Mem Utilization (%)", ylabel="")
    axes[0].set_yticklabels([LABEL_NAMES[b] for b in axes[0].get_yticklabels()])
    axes[0].set_xlim(0, 100)

    # CPU Utilization
    sns.boxplot(
        data=util_df.query("exp_branch in @focus and exp_workload in @workloads"),
        y="exp_branch", x="cpu_utilization",
        ax=axes[1], color="C3"
    )
    axes[1].set(xlabel="CPU Utilization (%)", ylabel="")
    axes[1].set_yticks([]); axes[1].set_xlim(0, 100)

    # Add shared title
    left_pos  = axes[0].get_position()
    right_pos = axes[1].get_position()
    mid_x = (left_pos.x0 + right_pos.x1) / 2 + 0.05
    top_y = left_pos.y1 + 0.05
    fig.text(mid_x, top_y, "Resource Utilization (RU)", ha="center")

    # Platform Overhead
    sns.boxplot(
        data=overhead_df.query("exp_branch in @focus and exp_workload in @workloads"),
        y="exp_branch", x="cost",
        ax=axes[2], color="C9"
    )
    axes[2].set(xlabel="Overhead (%)", ylabel="", title="Platform Overhead (RO)")
    axes[2].set_yticks([]); axes[2].set_xlim(0, 100)

    plt.tight_layout()
    plt.show()

# ─── Scaling and Energy Consumption ──────────────────────────────────────────

def compute_scaling_and_energy(pods_data, pods_energy_data, run_stats_data):
    # prepare pods
    pods = pods_data.copy()
    pods["type"] = pods["pod_name"].apply(
        lambda x: "pod" if x.startswith("teastore")
        else "function" if x.startswith("auth")
        else "infra"
    )
    pods = pods[pods["type"] != "infra"]
    pods["service"] = pods["pod_name"].apply(lambda x: "-".join(x.split("-")[:2]))

    # count per service/time
    pods_scale = pods.groupby(
        ["exp_branch","exp_workload","run_iteration","run_time","service"]
    )["name"].count().reset_index()

    # resource allowance per service
    def _allowance(row):
        svc = row["service"]
        if svc not in GENERAL_ALLOWANCE and not svc.startswith("auth"):
            return row
        if svc.startswith("auth"):
            cpu = GENERAL_ALLOWANCE["auth"]["cpu"]
            mem = GENERAL_ALLOWANCE["auth"]["memory"]
        else:
            cpu = GENERAL_ALLOWANCE[svc]["cpu"]
            mem = GENERAL_ALLOWANCE[svc]["memory"]
        row["cpu_limit"] = cpu
        row["mem_limit"] = mem
        return row

    pods = pods.apply(_allowance, axis=1, result_type="expand")
    pods["mem_utilization"] = 100 * pods["memory_usage"] / pods["mem_limit"]
    pods["cpu_utilization"] = 100 * (1000 * pods["cpu_usage"]) / pods["cpu_limit"]

    # under/over‐utilization flags
    pods["under_utilized"] = 1
    pods.loc[
        (pods["mem_utilization"] < 49) &
        (pods["cpu_utilization"] < 49),
        "under_utilized"
    ] = 0

    pods["over_utilized"] = 1
    pods.loc[
        (pods["mem_utilization"] > 90) |
        (pods["cpu_utilization"] > 90),
        "over_utilized"
    ] = 0

    # aggregate per branch/workload
    agg = pods.groupby(
        ["exp_branch","exp_workload","run_iteration","service","run_time"]
    )[
        ["under_utilized","over_utilized","wattage_kepler"]
    ].agg(["sum","count"])
    agg["under"] = agg[("under_utilized","count")] - agg[("under_utilized","sum")]
    agg["over"]  = agg[("over_utilized","count")] - agg[("over_utilized","sum")]
    agg["count"] = agg[("over_utilized","count")]
    agg.loc[(agg["count"]==1)&(agg["under"]==1),"under"] = 0
    agg.loc[(agg["count"]==3)&(agg["over"]==3),"over"] = 0
    agg.loc[agg["under"] > 0,"waste"] = agg[("wattage_kepler","sum")]

    df = (
        agg
        .droplevel(1, axis=1)
        .reset_index()[[
            "exp_branch","exp_workload","run_iteration",
            "service","run_time","under","over","count","waste"
        ]]
    )
    # total waste per branch/workload
    scaling_waste = df.groupby(["exp_branch","exp_workload"])["waste"].sum().reset_index()

    # energy per request
    wdf = pods_energy_data.merge(
        run_stats_data,
        on=RUN_VARS,
        how="left",
        validate="one_to_one"
    )
    wdf["ws_per_rq"]  = wdf["wattage_kepler"]  / wdf["Success Count"]
    wdf["mems_per_rq"] = wdf["memory_usage"]   / wdf["Success Count"]
    wdf["cpus_per_rq"] = wdf["cpu_usage"]      / wdf["Success Count"]

    return scaling_waste, wdf

def plot_scaling_and_energy(scaling_waste, wdf):
    warnings.filterwarnings("ignore")
    focus = FULL_STACK_FOCUS
    workloads = [RIGHT_WORKLOAD, "exp_scale_shaped", LEFT_WORKLOAD]

    # set up figure
    fig = plt.figure(figsize=(13, 4))
    gs  = gridspec.GridSpec(1, 3, width_ratios=[1,1,1.1])
    sns.set_style("whitegrid")
    sns.set_context(rc={
        "font.size":13,
        "axes.titlesize":13,
        "axes.labelsize":13,
        "xtick.labelsize":13,
        "ytick.labelsize":15
    })

    # energy per request (left two panels)
    ax0 = fig.add_subplot(gs[0:2])
    sns.boxplot(
        data=wdf[wdf.exp_branch.isin(focus)],
        hue="exp_branch",
        hue_order=LABEL_NAMES.keys(),
        y="ws_per_rq",
        x="exp_workload",
        palette=palette,
        ax=ax0
    )
    ax0.set(
        xlabel="Workloads",
        ylabel="Energy per Request [Ws]",
        title="Request Consumption per Workload (WR)"
    )
    ax0.set_xticklabels([LABEL_NAMES[x.get_text()] for x in ax0.get_xticklabels()])
    handles, labels = ax0.get_legend_handles_labels()
    ax0.legend(handles, [LABEL_NAMES[l] for l in labels], title="")
    
    # scaling waste (right panel)
    ax1 = fig.add_subplot(gs[2])
    sns.boxplot(
        data=scaling_waste[scaling_waste.exp_branch.isin(focus)],
        x="exp_branch",
        y="waste",
        palette=palette,
        ax=ax1
    )
    ax1.set(
        xlabel="",
        ylabel="Scaling Waste [Ws]",
        title="Resource Efficiency (RE)"
    )
    ax1.set_xticklabels([SHORT_LABELS[x.get_text()] for x in ax1.get_xticklabels()])

    plt.tight_layout()
    # save figure
    out = "01 Data/plots/scaling_energy.png"
    fig.savefig(out)
    logger.info(f"Saved scaling & energy plot to {out}")
    plt.close(fig)

# ─── Generate Plots ──────────────────────────────────────────────────

def generate_plots():
    plots_dir = "01 Data/plots"
    os.makedirs(plots_dir, exist_ok=True)
    logger.info(f"Ensured plots directory exists: {plots_dir}")

    # 1) Load all data
    stats_hist, pods_data, stats_data, nodes_data, pods_energy_data, run_stats_data = \
        load_all_data("01 Data/observation.hdf5")
    logger.info("Loaded all experiment data from HDF5.")

    # 2) Service-quality table
    svc_table = compute_service_quality_table(stats_hist, pods_data, stats_data)
    svc_csv = f"{plots_dir}/service_quality_table.csv"
    # .data unwraps the Styler to a plain DataFrame
    svc_table.data.to_csv(svc_csv, index=True)
    logger.info(f"Wrote service-quality table CSV to {svc_csv}")

    # 3) Resource utilization & overhead
    util  = compute_resource_utilization(pods_data)
    overh = compute_platform_overhead(nodes_data, pods_data)
    plot_utilization_and_overhead(util, overh)
    logger.info("Resource utilization & platform overhead plots generated.")

    # 4) Scaling & energy consumption
    scaling_waste, wdf = compute_scaling_and_energy(pods_data, pods_energy_data, run_stats_data)
    plot_scaling_and_energy(scaling_waste, wdf)
    logger.info("Scaling & energy consumption plot generated.")

    logger.info("All plots successfully generated and saved under 01 Data/plots.")



