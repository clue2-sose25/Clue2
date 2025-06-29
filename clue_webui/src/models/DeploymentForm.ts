export interface DeploymentForm {
  sut: string | null;
  variants: string[];
  workloads: string[];
  iterations: number;
  deploy_only: boolean;
}