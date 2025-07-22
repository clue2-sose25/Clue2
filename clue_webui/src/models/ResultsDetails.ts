export interface WorkloadSettings {
    [key: string]: any;
}

export interface Workload {
    name: string;
    description: string;
    timeout_duration: number;
    workload_settings: WorkloadSettings;
}

export interface Variant {
    name: string;
    target_branch: string;
    critical_services: string[];
    colocated_workload: boolean;
    autoscaling: string;
    max_autoscale: number;
    description: string;
}

export interface EnvConfig {
    SUT_CONFIGS_PATH: string;
    CLUE_CONFIG_PATH: string;
    RESULTS_PATH: string;
    LOG_LEVEL: string;
    SUT: string;
    VARIANTS: string;
    WORKLOADS: string;
    N_ITERATIONS: number;
    DEPLOY_ONLY: boolean;
    SUT_CONFIG_PATH: string;
}

export interface ClueConfig {
    prometheus_url: string;
    local_public_ip: string;
    local_port: number;
    remote_platform_arch: string;
    local_platform_arch: string;
    docker_registry_address: string;
    target_utilization: number;
}

export interface ResourceLimit {
    cpu: number;
    memory: number;
}

export interface ResourceLimitConfig {
    service_name: string;
    limit: ResourceLimit;
}

export interface HelmReplacementConditions {
    autoscaling?: boolean;
    autoscaling_type?: string;
}

export interface HelmReplacement {
    value: string;
    replacement: string;
    conditions: HelmReplacementConditions | null;
}

export interface SutConfig {
    sut: string;
    sut_path: string;
    sut_git_repo: string;
    helm_chart_path: string;
    helm_chart_repo: string;
    helm_dependencies_from_chart: boolean;
    values_yaml_name: string;
    namespace: string;
    infrastructure_namespaces: string[];
    workload_target: string;
    application_endpoint_path: string;
    default_resource_limits: ResourceLimit;
    wait_before_workloads: number;
    wait_after_workloads: number;
    timeout_for_services_ready: number;
    helm_replacements: HelmReplacement[];
    variants: Variant[];
    workloads: Workload[];
    resource_limits: ResourceLimitConfig[];
    target_host: string;
}

export interface Configs {
    env_config: EnvConfig;
    clue_config: ClueConfig;
    sut_config: SutConfig;
}

export interface ResultDetails {
    id: string;
    sut: string;
    workloads: Workload[];
    variants: Variant[];
    timestamp: string;
    n_iterations: number;
    deploy_only: boolean;
    configs: Configs;
    status: string;
}