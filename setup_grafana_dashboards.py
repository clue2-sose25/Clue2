#!/usr/bin/env python3
"""
Standalone utility script for setting up Grafana dashboards in CLUE.
This script can be used to manually import dashboards or troubleshoot Grafana setup.
"""

import argparse
import sys
from pathlib import Path
from clue_deployer.src.service.grafana_manager import GrafanaManager
from clue_deployer.src.configs.configs import CLUE_CONFIG
from clue_deployer.src.logger import logger

def main():
    parser = argparse.ArgumentParser(description='Setup Grafana dashboards for CLUE')
    parser.add_argument('--dashboard-path', type=Path, 
                       default=Path(__file__).parent.parent / CLUE_CONFIG.kepler_dashboard_path,
                       help='Path to dashboard JSON file')
    parser.add_argument('--grafana-url', type=str, 
                       default=f"http://localhost:{CLUE_CONFIG.grafana_node_port}",
                       help='Grafana URL')
    parser.add_argument('--username', type=str, 
                       default=CLUE_CONFIG.grafana_username,
                       help='Grafana username')
    parser.add_argument('--password', type=str, 
                       default=CLUE_CONFIG.grafana_password,
                       help='Grafana password')
    parser.add_argument('--node-port', type=int, 
                       default=CLUE_CONFIG.grafana_node_port,
                       help='Grafana NodePort')
    parser.add_argument('--skip-service-setup', action='store_true',
                       help='Skip Grafana service setup')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate metrics, do not import dashboard')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Initialize Grafana manager
    grafana_manager = GrafanaManager(
        grafana_url=args.grafana_url,
        username=args.username,
        password=args.password
    )
    
    try:
        if args.validate_only:
            logger.info("Validating dashboard metrics only...")
            success = grafana_manager.validate_dashboard_metrics()
            if success:
                logger.info("Dashboard metrics validation passed")
                return 0
            else:
                logger.error("Dashboard metrics validation failed")
                return 1
        
        if not args.skip_service_setup:
            logger.info("Setting up Grafana service access...")
            if not grafana_manager.setup_grafana_service_access(args.node_port):
                logger.error("Failed to setup Grafana service access")
                return 1
        
        logger.info("Waiting for Grafana to be ready...")
        if not grafana_manager.wait_for_grafana_ready():
            logger.error("Grafana is not ready")
            return 1
        
        logger.info("Setting up Prometheus datasource...")
        datasource_config = grafana_manager.get_default_prometheus_datasource_config()
        if not grafana_manager.create_datasource(datasource_config):
            logger.error("Failed to create Prometheus datasource")
            return 1
        
        if args.dashboard_path.exists():
            logger.info(f"Importing dashboard from {args.dashboard_path}")
            if not grafana_manager.import_dashboard(args.dashboard_path):
                logger.error("Failed to import dashboard")
                return 1
        else:
            logger.error(f"Dashboard file not found: {args.dashboard_path}")
            return 1
        
        logger.info("Validating dashboard metrics...")
        grafana_manager.validate_dashboard_metrics()
        
        logger.info("Grafana setup completed successfully!")
        logger.info(f"Access Grafana at: {args.grafana_url}")
        logger.info(f"Credentials: {args.username}/{args.password}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during Grafana setup: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
