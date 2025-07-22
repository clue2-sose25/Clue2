export interface DeploymentForm {
  sut: string | null;
  variants: string[];
  workloads: string[];
  n_iterations: number;
  deploy_only: boolean;
}