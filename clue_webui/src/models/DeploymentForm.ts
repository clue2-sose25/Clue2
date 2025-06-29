export type Workload = "shaped" | "rampup" | "pausing" | "fixed";

export interface WorkloadOption {
  name: Workload;
  description: string;
}

export const workloadOptions: WorkloadOption[] = [
  {
    name: "shaped",
    description: "Workload with custom load shape behavior.",
  },
  {
    name: "rampup",
    description: "Workload that ramps up users at a constant rate.",
  },
  {
    name: "pausing",
    description: "Workload that starts 20 pausing users with no ramp-up.",
  },
  {
    name: "fixed",
    description:
      "Workload that ramps to max users for a fixed number of requests.",
  },
];

export interface DeploymentForm {
  sut: string | null;
  variants: string[];
  workloads: Workload[];
  iterations: number;
  deploy_only: boolean;
}
