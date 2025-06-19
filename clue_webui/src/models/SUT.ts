export interface Experiment {
  name: string;
  description?: string;
}

export interface SUT {
  name: string;
  experiments: Experiment[];
}
