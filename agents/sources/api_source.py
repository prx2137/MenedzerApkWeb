import requests
import time
import logging
from typing import List, Dict, Any
from datetime import datetime


class APISource:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.url = config.get('url')
        self.method = config.get('method', 'GET')
        self.params = config.get('params', {})
        self.interval = config.get('interval', 10)
        self.last_check = 0

    def connect(self) -> bool:
        try:
            response = requests.get(self.url, params=self.params, timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"API connection error: {e}")
            return False

    def disconnect(self) -> None:
        # API nie wymaga rozłączenia
        pass

    def read_logs(self) -> List[Dict[str, Any]]:
        current_time = time.time()
        if current_time - self.last_check < self.interval:
            return []

        try:
            if self.method.upper() == 'GET':
                response = requests.get(self.url, params=self.params, timeout=10)
            else:
                response = requests.post(self.url, json=self.params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                logs = []

                # Przetwarzanie odpowiedzi API - dostosuj do struktury Twojego API
                if isinstance(data, dict) and 'logs' in data:
                    api_logs = data['logs']
                elif isinstance(data, list):
                    api_logs = data
                else:
                    api_logs = [data]

                for log_entry in api_logs:
                    if isinstance(log_entry, dict):
                        log = {
                            "timestamp": log_entry.get("timestamp", datetime.now().isoformat()),
                            "level": log_entry.get("level", "INFO"),
                            "message": log_entry.get("message", ""),
                            "source": self.name,
                            "service": log_entry.get("service", self.config.get('service', 'api')),
                            "original_data": log_entry
                        }
                        logs.append(log)

                self.last_check = current_time
                return logs
            else:
                self.logger.error(f"API returned status {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Error reading API logs: {e}")
            return []