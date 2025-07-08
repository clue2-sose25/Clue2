import requests
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from clue_deployer.src.logger import logger
from clue_deployer.src.configs.configs import CLUE_CONFIG


class GrafanaManager:
    """
    Manages Grafana configuration and dashboard operations for CLUE sustainability evaluation.
    """
    
    def __init__(self, grafana_url: str = "http://localhost:3000", 
                 username: str = "admin", password: str = "prom-operator"):
        """
        Initialize Grafana manager.
        
        Args:
            grafana_url: Grafana base URL
            username: Grafana admin username
            password: Grafana admin password
        """
        self.grafana_url = grafana_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def wait_for_grafana_ready(self, timeout: int = 300, check_interval: int = 5) -> bool:
        """
        Wait for Grafana to be ready and accessible.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            True if Grafana is ready, False if timeout reached
        """
        logger.info(f"Waiting for Grafana to be ready at {self.grafana_url}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.grafana_url}/api/health", timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get('database') == 'ok':
                        logger.info("Grafana is ready and healthy")
                        return True
                    else:
                        logger.debug(f"Grafana health check: {health_data}")
                        
            except requests.exceptions.RequestException as e:
                logger.debug(f"Grafana not ready yet: {e}")
                
            time.sleep(check_interval)
            
        logger.error(f"Grafana failed to become ready within {timeout} seconds")
        return False
    
    def setup_grafana_service_access(self, node_port: int = 30080) -> bool:
        """
        Set up access to Grafana service and ensure it's accessible.
        
        Args:
            node_port: NodePort for Grafana service
            
        Returns:
            True if service is accessible, False otherwise
        """
        try:
            # Check if Grafana service exists and is NodePort
            service_check = subprocess.run([
                "kubectl", "get", "svc", "kps1-grafana", 
                "-o", "jsonpath={.spec.type}"
            ], capture_output=True, text=True)
            
            if service_check.returncode != 0:
                logger.error("Grafana service not found")
                return False
                
            service_type = service_check.stdout.strip()
            
            if service_type != "NodePort":
                logger.info("Converting Grafana service to NodePort...")
                patch_result = subprocess.run([
                    "kubectl", "patch", "svc", "kps1-grafana",
                    "-p", f'{{"spec":{{"type":"NodePort","ports":[{{"port":80,"targetPort":3000,"nodePort":{node_port}}}]}}}}'
                ], capture_output=True, text=True)
                
                if patch_result.returncode != 0:
                    logger.error(f"Failed to patch Grafana service: {patch_result.stderr}")
                    return False
                    
                logger.info(f"Grafana service converted to NodePort on port {node_port}")
            else:
                logger.info("Grafana service is already NodePort")
                
            # Update the Grafana URL to use the NodePort
            self.grafana_url = f"http://localhost:{node_port}"
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up Grafana service access: {e}")
            return False
    
    def create_datasource(self, datasource_config: Dict) -> bool:
        """
        Create or update a Grafana datasource.
        
        Args:
            datasource_config: Datasource configuration dictionary
            
        Returns:
            True if datasource created/updated successfully
        """
        try:
            # Check if datasource already exists
            datasource_name = datasource_config.get('name', 'prometheus')
            response = self.session.get(f"{self.grafana_url}/api/datasources/name/{datasource_name}")
            
            if response.status_code == 200:
                logger.info(f"Datasource '{datasource_name}' already exists")
                return True
            elif response.status_code == 404:
                # Create new datasource
                response = self.session.post(f"{self.grafana_url}/api/datasources", 
                                           json=datasource_config)
                if response.status_code == 200:
                    logger.info(f"Successfully created datasource '{datasource_name}'")
                    return True
                else:
                    logger.error(f"Failed to create datasource: {response.text}")
                    return False
            else:
                logger.error(f"Error checking datasource: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating datasource: {e}")
            return False
    
    def import_dashboard(self, dashboard_path: Path, datasource_uid: str = "prometheus") -> bool:
        """
        Import a dashboard from JSON file.
        
        Args:
            dashboard_path: Path to dashboard JSON file (kepler_dashboard.json)
            datasource_uid: UID of the datasource to use
            
        Returns:
            True if dashboard imported successfully
        """
        try:
            if not dashboard_path.exists():
                logger.error(f"Dashboard file not found: {dashboard_path}")
                return False
                
            logger.info(f"Importing Kepler dashboard from: {dashboard_path}")
            
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                dashboard_json = json.load(f)
            
            # Store original values for rollback if needed
            original_id = dashboard_json.get('id')
            original_uid = dashboard_json.get('uid')
            
            # Prepare dashboard for import
            dashboard_json['id'] = None  # Let Grafana assign new ID
            dashboard_json['uid'] = None  # Let Grafana assign new UID
            
            # Update datasource references for Kepler dashboard
            dashboard_str = json.dumps(dashboard_json, indent=2)
            
            # Replace variable datasource references
            dashboard_str = dashboard_str.replace('"${datasource}"', f'"{datasource_uid}"')
            
            # Replace hardcoded prometheus datasource references
            dashboard_str = dashboard_str.replace('"datasource": "prometheus"', f'"datasource": "{datasource_uid}"')
            
            # Handle datasource object format
            dashboard_str = dashboard_str.replace(
                '"datasource": {\n        "type": "prometheus",\n        "uid": "${datasource}"\n      }',
                f'"datasource": {{\n        "type": "prometheus",\n        "uid": "{datasource_uid}"\n      }}'
            )
            
            dashboard_json = json.loads(dashboard_str)
            
            # Import dashboard with proper configuration for Kepler
            import_payload = {
                "dashboard": dashboard_json,
                "overwrite": True,
                "folderId": 0,  # Place in General folder
                "inputs": [
                    {
                        "name": "DS_PROMETHEUS",
                        "type": "datasource",
                        "pluginId": "prometheus", 
                        "value": datasource_uid
                    }
                ]
            }
            
            response = self.session.post(f"{self.grafana_url}/api/dashboards/import", 
                                       json=import_payload)
            
            if response.status_code == 200:
                result = response.json()
                dashboard_url = f"{self.grafana_url}/d/{result['uid']}/{result['slug']}"
                logger.info(f"✅ Successfully imported Kepler dashboard: {dashboard_path.name}")
                logger.info(f"📊 Dashboard URL: {dashboard_url}")
                logger.info(f"🔑 Dashboard UID: {result['uid']}")
                return True
            else:
                logger.error(f"❌ Failed to import dashboard: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in dashboard file: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error importing Kepler dashboard: {e}")
            return False
    
    def get_default_prometheus_datasource_config(self) -> Dict:
        """
        Get default Prometheus datasource configuration.
        
        Returns:
            Datasource configuration dictionary
        """
        return {
            "name": "prometheus",
            "type": "prometheus",
            "url": "http://kps1-kube-prometheus-stack-prometheus:9090",
            "access": "proxy",
            "isDefault": True,
            "basicAuth": False,
            "basicAuthUser": "",
            "basicAuthPassword": "",
            "withCredentials": False,
            "jsonData": {
                "httpMethod": "POST",
                "queryTimeout": "60s",
                "timeInterval": "30s"
            }
        }
    
    def validate_dashboard_metrics(self, dashboard_title: str = "Kepler Exporter") -> bool:
        """
        Validate that Kepler dashboard metrics are available and working.
        
        Args:
            dashboard_title: Title of dashboard to validate (default: "Kepler Exporter")
            
        Returns:
            True if Kepler metrics are available
        """
        try:
            logger.info("🔍 Validating Kepler dashboard metrics...")
            
            # Search for the Kepler dashboard
            response = self.session.get(f"{self.grafana_url}/api/search", 
                                      params={"query": dashboard_title})
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to search for dashboard: {response.text}")
                return False
                
            dashboards = response.json()
            if not dashboards:
                logger.warning(f"⚠️ Dashboard '{dashboard_title}' not found in search results")
                # Try searching for "Kepler" specifically
                response = self.session.get(f"{self.grafana_url}/api/search", 
                                          params={"query": "Kepler"})
                if response.status_code == 200:
                    dashboards = response.json()
                    if dashboards:
                        logger.info(f"✅ Found Kepler dashboard(s): {[d.get('title', 'Unknown') for d in dashboards]}")
                    else:
                        logger.error("❌ No Kepler dashboards found")
                        return False
                else:
                    return False
                
            # Test Kepler-specific metrics that should be available
            test_queries = [
                "up{job=\"kepler\"}",
                "kepler_container_energy_stat",
                "kepler_node_energy_stat", 
                "kepler_container_cpu_cycles_total",
                "kepler_node_cpu_cycles_total"
            ]
            
            # Try to use the datasource proxy API
            datasource_proxy_url = f"{self.grafana_url}/api/datasources/proxy/1/api/v1/query"
            
            metrics_found = 0
            for query in test_queries:
                try:
                    response = self.session.get(datasource_proxy_url, 
                                              params={"query": query},
                                              timeout=10)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if (result.get('status') == 'success' and 
                            result.get('data', {}).get('result') and 
                            len(result['data']['result']) > 0):
                            logger.info(f"✅ Kepler metric '{query}' is available with data")
                            metrics_found += 1
                        else:
                            logger.debug(f"⚠️ Metric '{query}' exists but has no data")
                    else:
                        logger.debug(f"❌ Query '{query}' failed: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.debug(f"❌ Network error for query '{query}': {e}")
                    
            if metrics_found > 0:
                logger.info(f"✅ Kepler metrics validation passed! Found {metrics_found}/{len(test_queries)} metrics with data")
                return True
            else:
                logger.warning("⚠️ No Kepler metrics found with data - dashboard may not display information correctly")
                logger.info("💡 This might be normal if Kepler has just been deployed and hasn't collected data yet")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error validating Kepler dashboard metrics: {e}")
            return False
    
    def setup_complete_grafana_environment(self, dashboard_path: Path, node_port: int = 30080) -> bool:
        """
        Complete setup of Grafana environment including service access, datasource, and dashboard import.
        
        Args:
            dashboard_path: Path to dashboard JSON file to import
            node_port: NodePort for Grafana service
            
        Returns:
            True if setup completed successfully
        """
        logger.info("Setting up complete Grafana environment...")
        
        # Step 1: Setup service access
        if not self.setup_grafana_service_access(node_port):
            logger.error("Failed to setup Grafana service access")
            return False
        
        # Step 2: Wait for Grafana to be ready
        if not self.wait_for_grafana_ready():
            logger.error("Grafana failed to become ready")
            return False
        
        # Step 3: Create Prometheus datasource
        datasource_config = self.get_default_prometheus_datasource_config()
        if not self.create_datasource(datasource_config):
            logger.error("Failed to create Prometheus datasource")
            return False
        
        # Step 4: Import dashboard
        if not self.import_dashboard(dashboard_path):
            logger.error("Failed to import dashboard")
            return False
        
        # Step 5: Validate metrics (non-blocking)
        self.validate_dashboard_metrics()
        
        logger.info("Grafana environment setup completed successfully!")
        logger.info(f"Access Grafana at: {self.grafana_url}")
        logger.info(f"Default credentials: {self.username}/{self.password}")
        
        return True
