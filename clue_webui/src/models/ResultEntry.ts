export interface ResultEntry {
  uuid: string;
  status: string;
  sut: string;
  workloads: string;
  variants: string;
  timestamp: string;
  n_iterations: number;
  deploy_only: boolean;
}
