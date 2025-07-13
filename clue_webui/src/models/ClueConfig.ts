export interface ClueConfig {
  experiment_timeout: number;
  prometheus_url: string;
  local_public_ip: string;
  local_port: number;
  remote_platform_arch: string;
  local_platform_arch: string;
  docker_registry_address: string;
  target_utilization: number;
}