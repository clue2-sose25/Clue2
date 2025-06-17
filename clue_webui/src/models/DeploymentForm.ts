export type Workload = "shaped" | "rampup" | "pausing" | "fixed";

export const workloadOptions: Workload[] = [
  "shaped",
  "rampup",
  "pausing",
  "fixed",
];

export interface DeploymentForm {
  SutName: string | null;
  experimentName: string | null;
  workload: Workload;
  iterations: number;
  deploy_only: boolean;
}
