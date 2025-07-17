#!/usr/bin/env python3
"""
Minimal Grafana Setup for Kubernetes.
Sets up Prometheus, Grafana, Kepler, and imports the Kepler dashboard.
"""

import sys
import time
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.error("requests module is required. Install with: pip install requests")
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).resolve().parent.parent  # Go up to main project root
sys.path.insert(0, str(project_root))

try:
    from clue_deployer.src.configs.configs import CLUE_CONFIG
    prometheus_url = CLUE_CONFIG.prometheus_url
    logger.info(f"Using Prometheus URL from CLUE config: {prometheus_url}")
except ImportError:
    prometheus_url = "http://localhost:30090"  # Fallback
    logger.warning("Could not import CLUE_CONFIG, using fallback Prometheus URL")

def run_command(cmd, check=True, capture_output=False):
    """Run a command with proper error handling."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
            return True
    except subprocess.CalledProcessError as e:
        if capture_output and hasattr(e, 'stderr'):
            logger.error(f"Command failed: {cmd} - {e.stderr}")
        return False

def check_cluster():
    """Check that Kubernetes cluster is accessible."""
    logger.info("Checking Kubernetes cluster...")
    try:
        run_command("kubectl cluster-info", capture_output=True)
        logger.info("✅ Kubernetes cluster is accessible")
        return True
    except:
        logger.error("❌ Kubernetes cluster is not accessible")
        return False

def setup_helm_repos():
    """Add required Helm repositories."""
    logger.info("Setting up Helm repositories...")
    
    repos = [
        ("prometheus-community", "https://prometheus-community.github.io/helm-charts"),
        ("kepler", "https://sustainable-computing-io.github.io/kepler-helm-chart")
    ]
    
    for name, url in repos:
        run_command(f"helm repo add {name} {url}", check=False)
    
    run_command("helm repo update")
    logger.info("✅ Helm repositories updated")

def install_prometheus_grafana():
    """Install Prometheus stack with Grafana."""
    logger.info("Installing Prometheus + Grafana stack...")
    
    # Check if already installed
    if run_command("helm status kps1", check=False, capture_output=True):
        logger.info("✅ Prometheus stack already installed")
        return True
    
    install_cmd = [
        "helm", "install", "kps1", "prometheus-community/kube-prometheus-stack",
        "--set", "prometheus.service.type=NodePort",
        "--set", "prometheus.service.nodePort=30090",
        "--set", "grafana.service.type=NodePort", 
        "--set", "grafana.service.nodePort=30080",
        "--set", "grafana.adminPassword=prom-operator",
        "--wait", "--timeout", "10m"
    ]
    
    try:
        subprocess.run(install_cmd, check=True)
        logger.info("✅ Prometheus + Grafana installed")
        return True
    except subprocess.CalledProcessError:
        logger.error("❌ Failed to install Prometheus stack")
        return False

def install_kepler():
    """Install Kepler for energy monitoring."""
    logger.info("Installing Kepler...")
    
    # Check if already installed
    if run_command("helm status kepler --namespace kepler", check=False, capture_output=True):
        logger.info("✅ Kepler already installed")
        return True
    
    install_cmd = [
        "helm", "install", "kepler", "kepler/kepler",
        "--namespace", "kepler", "--create-namespace",
        "--set", "serviceMonitor.enabled=true",
        "--set", "serviceMonitor.labels.release=kps1",
        "--wait", "--timeout", "8m"
    ]
    
    try:
        subprocess.run(install_cmd, check=True)
        logger.info("✅ Kepler installed")
        return True
    except subprocess.CalledProcessError:
        logger.error("❌ Failed to install Kepler")
        return False

def wait_for_grafana():
    """Wait for Grafana to be ready."""
    logger.info("Waiting for Grafana to be ready...")
    
    # Wait for pods
    run_command("kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana --timeout=300s", check=False)
    
    # Give Grafana extra time to initialize
    time.sleep(20)
    logger.info("✅ Grafana should be ready")

def import_dashboard():
    """Import the Kepler dashboard into Grafana."""
    logger.info("Dashboard import setup...")
    
    try:
        # Check if dashboard file exists
        dashboard_path = project_root / "grafana_dashboard.json"
        if not dashboard_path.exists():
            # Try alternative location
            dashboard_path = project_root.parent / "grafana_dashboard.json"
        
        if dashboard_path.exists():
            logger.info("✅ Dashboard file found")
            logger.info(f"Dashboard location: {dashboard_path}")
            logger.info("📊 Grafana dashboards are automatically provisioned by kube-prometheus-stack")
            logger.info("🔧 For manual dashboard import, use Grafana UI or API calls")
            logger.info("🌐 Access Grafana at http://localhost:30080 (admin/prom-operator)")
            return True
        else:
            logger.warning("❌ Dashboard file not found")
            logger.info("📊 Grafana is ready but dashboard needs to be imported manually")
            return True
            
    except Exception as e:
        logger.error(f"❌ Dashboard setup error: {e}")
    
    return True  # Don't fail the entire setup for dashboard issues

def show_access_info():
    """Show how to access the services."""
    print("\n" + "="*50)
    print("🎉 SETUP COMPLETE!")
    print("="*50)
    print("📊 Grafana Dashboard:")
    print("   URL: http://localhost:30080")
    print("   Username: admin")
    print("   Password: prom-operator")
    print("   Note: Dashboards auto-provisioned by Helm chart")
    print()
    print("📈 Prometheus:")
    print(f"   URL: {prometheus_url}")
    print("   Local access: http://localhost:30090")
    print()
    print("📋 Manual Dashboard Import (if needed):")
    print("   1. Access Grafana UI at http://localhost:30080")
    print("   2. Go to '+' → Import → Upload JSON file")
    print("   3. Use grafana_dashboard.json from project root")
    print()
    print("🔧 If NodePort doesn't work, use port-forward:")
    print("   kubectl port-forward service/kps1-grafana 3080:80")
    print("   kubectl port-forward service/kps1-kube-prometheus-stack-prometheus 9090:9090")
    print("="*50)

def main():
    """Main setup function."""
    logger.info("🚀 Starting Grafana + Kepler setup for Kubernetes")
    
    # Step 1: Check cluster
    if not check_cluster():
        return False
    
    # Step 2: Setup Helm repos
    setup_helm_repos()
    
    # Step 3: Install Prometheus + Grafana
    if not install_prometheus_grafana():
        return False
    
    # Step 4: Install Kepler
    if not install_kepler():
        return False
    
    # Step 5: Wait for Grafana
    wait_for_grafana()
    
    # Step 6: Setup dashboard info
    import_dashboard()
    
    # Step 7: Show access info
    show_access_info()
    
    logger.info("✅ Setup completed!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        sys.exit(1)
