import os
import time
import yaml
import argparse
import sqlite3
from datetime import datetime
from elasticsearch import Elasticsearch
import logging
from typing import List, Dict, Any
import requests

# Import źródeł
try:
    from sources.file_source import FileSource
    from sources.database_source import DatabaseSource
    from sources.api_source import APISource
except ImportError:
    # Dla kompatybilności wstecznej
    FileSource = None
    DatabaseSource = None
    APISource = None


class LogAgent:
    def __init__(self, config_path: str = "config.yaml", elasticsearch_host: str = "http://localhost:9200"):
        self.es = Elasticsearch([elasticsearch_host])
        self.sources = []
        self.config_path = config_path
        self.setup_logging()
        self.load_config()
        self.config = {}

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        """Ładuje konfigurację z pliku YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            self.logger.info(f"Loaded configuration from {self.config_path}")

            # Tworzenie źródeł na podstawie konfiguracji
            for source_config in self.config.get('sources', []):
                source_type = source_config.get('type')
                source_name = source_config.get('name', f"source_{len(self.sources)}")

                source = None

                if source_type == 'file' and FileSource:
                    source = FileSource(source_name, source_config)
                elif source_type == 'database' and DatabaseSource:
                    source = DatabaseSource(source_name, source_config)
                elif source_type == 'api' and APISource:
                    source = APISource(source_name, source_config)
                elif source_type == 'elasticsearch':
                    source = ElasticsearchSource(source_name, source_config)
                else:
                    self.logger.error(f"Unknown or unsupported source type: {source_type}")
                    continue

                if source:
                    self.sources.append(source)
                    self.logger.info(f"Added source: {source_name} ({source_type})")

        except FileNotFoundError:
            self.logger.error(f"Configuration file {self.config_path} not found")
            # Utwórz domyślną konfigurację
            self.create_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")

    def create_default_config(self):
        """Tworzy domyślną konfigurację"""
        default_config = {
            'sources': [
                {
                    'name': 'frontend-logs',
                    'type': 'file',
                    'path': '../Examples/frontend_app.log',
                    'service': 'frontend-ui',
                    'format': 'text'
                },
                {
                    'name': 'backend-logs',
                    'type': 'file',
                    'path': '../Examples/backend_api.log',
                    'service': 'backend-api',
                    'format': 'text'
                },
                {
                    'name': 'database-logs',
                    'type': 'file',
                    'path': '../Examples/database.log',
                    'service': 'database',
                    'format': 'text'
                }
            ]
        }

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        self.logger.info(f"Created default configuration at {self.config_path}")
        self.load_config()

    def connect_sources(self):
        """Łączy się ze wszystkimi źródłami"""
        for source in self.sources:
            try:
                if source.connect():
                    self.logger.info(f"Connected to source: {source.name}")
                else:
                    self.logger.error(f"Failed to connect to source: {source.name}")
            except Exception as e:
                self.logger.error(f"Error connecting to source {source.name}: {e}")

    def disconnect_sources(self):
        """Rozłącza wszystkie źródła"""
        for source in self.sources:
            try:
                source.disconnect()
                self.logger.info(f"Disconnected from source: {source.name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from source {source.name}: {e}")

    def send_to_elasticsearch(self, log_entry: Dict[str, Any]):
        """Wysyła pojedynczy wpis logu do Elasticsearch"""
        try:
            # Przygotuj dokument
            timestamp = log_entry.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()

            doc = {
                "timestamp": timestamp,
                "level": log_entry.get("level", "INFO"),
                "message": log_entry.get("message", ""),
                "source": log_entry.get("source", "unknown"),
                "service": log_entry.get("service", "unknown"),
                "original_data": log_entry
            }

            # Wyślij do Elasticsearch
            result = self.es.index(
                index="application-logs",
                document=doc
            )

            self.logger.debug(f"Log sent: {doc['level']} - {doc['message'][:60]}...")
            return True

        except Exception as e:
            self.logger.error(f"Error sending to Elasticsearch: {e}")
            return False

    def monitor_sources(self):
        """Monitoruje wszystkie źródła logów"""
        self.logger.info(f"Monitoring {len(self.sources)} sources...")

        try:
            while True:
                total_logs = 0

                for source in self.sources:
                    try:
                        logs = source.read_logs()
                        for log in logs:
                            if self.send_to_elasticsearch(log):
                                total_logs += 1
                    except Exception as e:
                        self.logger.error(f"Error reading from source {source.name}: {e}")

                if total_logs > 0:
                    self.logger.info(f"Processed {total_logs} logs from all sources")

                time.sleep(1)  # Krótka przerwa między cyklami

        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")

    def read_from_database(self, db_path: str = "logs.db", limit: int = 100):
        """Czytaj logi bezpośrednio z bazy SQLite"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(f'''
                SELECT * FROM logs 
                ORDER BY timestamp DESC 
                LIMIT {limit}
            ''')

            logs = []
            for row in cursor.fetchall():
                log_entry = {
                    "timestamp": row["timestamp"],
                    "level": row["level"],
                    "message": row["message"],
                    "source": row.get("source", "database"),
                    "service": row["service"],
                    "original_data": dict(row)
                }
                logs.append(log_entry)

            conn.close()
            return logs
        except Exception as e:
            self.logger.error(f"Error reading from database: {e}")
            return []

    def read_from_file(self, file_path: str, service_name: str, limit: int = 100):
        """Czytaj logi z pliku tekstowego"""
        logs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-limit:]  # Ostatnie `limit` linii
                for line in lines:
                    if line.strip():
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "level": self._parse_log_level(line),
                            "message": line.strip(),
                            "source": "file",
                            "service": service_name,
                            "original_data": {"line": line.strip()}
                        }
                        logs.append(log_entry)
            return logs
        except Exception as e:
            self.logger.error(f"Error reading from file {file_path}: {e}")
            return []

    def _parse_log_level(self, line: str) -> str:
        """Automatyczne wykrywanie poziomu logu"""
        line_lower = line.lower()
        if "error" in line_lower:
            return "ERROR"
        elif "warning" in line_lower or "warn" in line_lower:
            return "WARNING"
        elif "debug" in line_lower:
            return "DEBUG"
        else:
            return "INFO"

    def get_direct_logs(self, source_type: str, **kwargs):
        """Pobierz logi bezpośrednio ze źródła"""
        if source_type == "database":
            return self.read_from_database(kwargs.get("db_path", "logs.db"), kwargs.get("limit", 100))
        elif source_type == "file":
            return self.read_from_file(
                kwargs.get("file_path"),
                kwargs.get("service_name", "unknown"),
                kwargs.get("limit", 100)
            )
        elif source_type == "elasticsearch":
            return self.read_from_elasticsearch(
                kwargs.get("query", {}),
                kwargs.get("limit", 100)
            )
        else:
            return []

    def read_from_elasticsearch(self, query: dict = None, limit: int = 100):
        """Czytaj logi bezpośrednio z Elasticsearch"""
        try:
            if not query:
                query = {"match_all": {}}

            result = self.es.search(
                index="application-logs",
                query=query,
                size=limit,
                sort=[{"timestamp": {"order": "desc"}}]
            )

            logs = []
            for hit in result["hits"]["hits"]:
                log_data = hit["_source"]
                log_data["_id"] = hit["_id"]
                logs.append(log_data)

            return logs
        except Exception as e:
            self.logger.error(f"Error reading from Elasticsearch: {e}")
            return []

    def get_all_sources_direct(self, limit_per_source: int = 50):
        """Pobierz logi ze wszystkich źródeł jednocześnie"""
        all_logs = []

        # 1. Z Elasticsearch (główne repozytorium)
        es_logs = self.read_from_elasticsearch(limit=limit_per_source)
        for log in es_logs:
            log["source_type"] = "elasticsearch"
            all_logs.append(log)

        # 2. Z bazy danych SQLite (jeśli istnieje)
        try:
            db_logs = self.read_from_database("logs.db", limit_per_source)
            for log in db_logs:
                log["source_type"] = "database"
                all_logs.append(log)
        except Exception as e:
            self.logger.error(f"Database read error: {e}")

        # 3. Z plików logów (z konfiguracji)
        for source in self.config.get('sources', []):
            if source['type'] == 'file':
                try:
                    file_logs = self.read_from_file(
                        source['path'],
                        source.get('service', 'unknown'),
                        limit_per_source
                    )
                    for log in file_logs:
                        log["source_type"] = "file"
                        all_logs.append(log)
                except Exception as e:
                    self.logger.error(f"File read error for {source['path']}: {e}")

        # 4. Z API (jeśli skonfigurowane)
        for source in self.config.get('sources', []):
            if source['type'] == 'api':
                try:
                    api_logs = self.read_from_api(source)
                    for log in api_logs:
                        log["source_type"] = "api"
                        all_logs.append(log)
                except Exception as e:
                    self.logger.error(f"API read error for {source['url']}: {e}")

        # Sortuj po timestamp (malejąco)
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return all_logs

    def read_from_api(self, api_config: dict):
        """Czytaj logi z API"""
        try:
            url = api_config.get('url')
            method = api_config.get('method', 'GET')
            params = api_config.get('params', {})

            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=10)
            else:
                response = requests.post(url, json=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                logs = []

                # Przetwarzanie odpowiedzi API
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
                            "source": api_config.get('name', 'api'),
                            "service": log_entry.get("service", api_config.get('service', 'api')),
                            "original_data": log_entry
                        }
                        logs.append(log)

                return logs
            else:
                self.logger.error(f"API returned status {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"Error reading API logs: {e}")
            return []

    def run(self):
        """Główna pętla agenta"""
        print("=" * 50)
        print("🤖 Multi-Source Log Agent")
        print("=" * 50)
        print(f"Config file: {self.config_path}")
        print(f"Sources configured: {len(self.sources)}")
        for source in self.sources:
            print(f"  - {source.name} ({source.__class__.__name__})")
        print("=" * 50)
        print("Press Ctrl+C to stop")
        print("=" * 50)

        try:
            self.connect_sources()
            self.monitor_sources()
        except KeyboardInterrupt:
            self.logger.info("Stopping agent...")
        finally:
            self.disconnect_sources()
            self.logger.info("Agent stopped")


class ElasticsearchSource:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.es = Elasticsearch([config.get('host', 'http://localhost:9200')])
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            return self.es.ping()
        except Exception as e:
            self.logger.error(f"Elasticsearch connection error: {e}")
            return False

    def disconnect(self):
        pass

    def read_logs(self):
        try:
            index = self.config.get('index', 'application-logs')
            query = self.config.get('query', {"match_all": {}})
            size = self.config.get('size', 100)

            response = self.es.search(
                index=index,
                query=query,
                size=size,
                sort=[{"timestamp": {"order": "desc"}}]
            )

            logs = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                logs.append({
                    **source,
                    "_id": hit["_id"],
                    "_index": hit["_index"],
                    "source": self.name
                })

            return logs
        except Exception as e:
            self.logger.error(f"Error reading Elasticsearch logs: {e}")
            return []


def main():
    parser = argparse.ArgumentParser(description='Multi-source Log Agent')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--elasticsearch', type=str, default='http://localhost:9200',
                        help='Elasticsearch URL')

    args = parser.parse_args()

    agent = LogAgent(config_path=args.config, elasticsearch_host=args.elasticsearch)
    agent.run()


if __name__ == "__main__":
    main()