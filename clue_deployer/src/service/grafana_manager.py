import json
import time
from pathlib import Path


import requests

from clue_deployer.src.logger import logger


class GrafanaManager:
    """Simple manager for interacting with Grafana's HTTP API."""

    def __init__(self, grafana_url: str = "http://localhost:30080", *, username: str = "admin", password: str = "admin") -> None:
        self.grafana_url = grafana_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Content-Type": "application/json"})

    def wait_for_grafana_ready(self, timeout: int = 30) -> bool:
        """Wait until Grafana's health endpoint responds successfully."""
        end_time = time.time() + timeout
        url = f"{self.grafana_url}/api/health"
        while time.time() < end_time:
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False

    def _import_dashboard(self, dashboard: dict, *, folder_id: int = 0) -> bool:
        url = f"{self.grafana_url}/api/dashboards/db"
        payload = {"dashboard": dashboard, "overwrite": True, "folderId": folder_id}
        try:
            response = self.session.post(url, json=payload)
            if response.status_code in (200, 202):
                return True
            logger.error(f"Failed to import dashboard: {response.text}")
        except Exception as exc:
            logger.error(f"Error importing dashboard: {exc}")
        return False

    def setup_complete_grafana_environment(self, dashboard_path: Path, node_port: int | None = None) -> bool:
        """Import the provided dashboard JSON into Grafana."""
        try:
            with open(dashboard_path, "r", encoding="utf-8") as f:
                dashboard = json.load(f)
        except Exception as exc:
            logger.error(f"Unable to load dashboard file {dashboard_path}: {exc}")
            return False
        return self._import_dashboard(dashboard)