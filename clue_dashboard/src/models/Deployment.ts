export interface Deployment {
  SUT: string | null;
  experiment: string | null;
  workload: string | null;
  iterations: number;
}
