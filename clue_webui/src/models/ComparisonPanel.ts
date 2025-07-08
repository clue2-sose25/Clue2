import type { Variant, Workload } from "./ResultsDetails";

export interface ComparisonPanel {
  id: string;
  workload: Workload;
  variant: Variant;
  iteration: number;
}