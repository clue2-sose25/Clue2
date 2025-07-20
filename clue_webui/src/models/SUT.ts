export interface Variant {
  name: string;
  description?: string;
}

export interface Workload {
  name: string;
  description?: string;
}

export interface SUT {
  name: string;
  variants: Variant[];
  workloads: Workload[];
}

export interface WorkloadConfig {
  name: string;
  description: string;
  timeout_duration: number;
  workload_runtime: number;
}

export interface SutConfig {
  wait_before_workloads: number;
  wait_after_workloads: number;
  workloads: WorkloadConfig[];
}