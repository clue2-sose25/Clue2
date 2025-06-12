import type {Iteration} from "./Iteration";

export interface ResultEntry {
  id: string;
  timestamp: string;
  iterations: Iteration[];
}
