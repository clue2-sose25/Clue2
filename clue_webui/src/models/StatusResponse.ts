export interface StatusResponse {
  is_deploying: boolean;
  phase: string | null;
  message: string | null;
}
