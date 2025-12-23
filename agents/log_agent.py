import os
import time
import json
import argparse
from datetime import datetime
from elasticsearch import Elasticsearch
import logging


class LogAgent:
    def __init__(self, elasticsearch_host="http://localhost:9200"):
        self.es = Elasticsearch([elasticsearch_host])
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def read_log_file(self, file_path, service_name):
        """Czyta plik logów i wysyła do Elasticsearch"""
        try:
            # Użyj absolutnej ścieżki
            absolute_path = os.path.abspath(file_path)
            self.logger.info(f"Sprawdzam plik: {absolute_path}")

            # Sprawdź czy plik istnieje
            if not os.path.exists(absolute_path):
                self.logger.error(f"Plik {absolute_path} nie istnieje")
                self.logger.info(f"Tworzę przykładowy plik logów: {absolute_path}")
                self.create_sample_logs(absolute_path)
                return

            self.logger.info(f"Rozpoczynam monitorowanie pliku: {absolute_path}")

            # Otwórz plik i przejdź na koniec
            with open(absolute_path, 'r', encoding='utf-8') as file:
                # Przejdź na koniec pliku
                file.seek(0, 2)

                while True:
                    current_position = file.tell()
                    line = file.readline()

                    if not line:
                        # Brak nowych linii - czekaj
                        file.seek(current_position)
                        time.sleep(1)
                    else:
                        # Nowa linia - przetwarzaj
                        log_entry = self.parse_log_line(line.strip(), service_name)
                        if log_entry:
                            self.send_to_elasticsearch(log_entry)

        except KeyboardInterrupt:
            self.logger.info("Zatrzymywanie agenta...")
        except Exception as e:
            self.logger.error(f"Błąd przy czytaniu pliku: {e}")

    def parse_log_line(self, log_line, service_name):
        """Parsuje linię logu i tworzy strukturalny wpis"""
        try:
            # Prosty parser dla formatu: TIMESTAMP LEVEL [SERVICE] MESSAGE
            parts = log_line.split(' ', 3)
            if len(parts) >= 4:
                timestamp_str = f"{parts[0]} {parts[1]}"
                level = parts[2]
                message = parts[3]

                # Konwersja timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                except ValueError:
                    timestamp = datetime.now()

                return {
                    "timestamp": timestamp,
                    "level": level,
                    "message": message,
                    "source": "file",
                    "service": service_name,
                    "raw_line": log_line
                }
            else:
                return {
                    "timestamp": datetime.now(),
                    "level": "UNKNOWN",
                    "message": log_line,
                    "source": "file",
                    "service": service_name,
                    "raw_line": log_line
                }

        except Exception as e:
            self.logger.error(f"Błąd przy parsowaniu linii: {e}")
            return None

    def create_sample_logs(self, file_path):
        """Tworzy przykładowe logi jeśli plik nie istnieje"""
        sample_logs = [
            "2024-01-15 10:00:01,123 INFO [web-app] Application started successfully",
            "2024-01-15 10:00:02,456 DEBUG [web-app] Database connection established",
            "2024-01-15 10:00:03,789 INFO [web-app] User logged in",
            "2024-01-15 10:00:05,234 WARN [web-app] Cache size approaching limit",
            "2024-01-15 10:00:07,891 ERROR [web-app] Database connection timeout",
            "2024-01-15 10:00:10,123 INFO [api-service] Processing API request",
            "2024-01-15 10:00:12,456 ERROR [api-service] Failed to process request"
        ]

        # Utwórz katalog jeśli nie istnieje
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            for log in sample_logs:
                f.write(log + '\n')

        self.logger.info(f"Utworzono przykładowy plik logów: {file_path}")

    def send_to_elasticsearch(self, log_entry):
        """Wysyła pojedynczy wpis logu do Elasticsearch"""
        try:
            doc = {
                "timestamp": log_entry["timestamp"],
                "level": log_entry["level"],
                "message": log_entry["message"],
                "source": log_entry["source"],
                "service": log_entry["service"],
                "raw_line": log_entry.get("raw_line", "")
            }

            result = self.es.index(
                index="application-logs",
                document=doc
            )

            self.logger.info(f"Log wysłany: {log_entry['level']} - {log_entry['message'][:60]}...")
            return True

        except Exception as e:
            self.logger.error(f"Błąd przy wysyłaniu do Elasticsearch: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Agent do zbierania logów')

    # Użyj absolutnej ścieżki do katalogu Examples
    examples_dir = os.path.join(os.path.dirname(__file__), '..', 'Examples')
    default_log_file = os.path.join(examples_dir, 'example_app.log')

    parser.add_argument('--file', type=str, default=default_log_file,
                        help=f'Ścieżka do pliku z logami (domyślnie: {default_log_file})')
    parser.add_argument('--service', type=str, default='web-application',
                        help='Nazwa serwisu (domyślnie: web-application)')
    parser.add_argument('--elasticsearch', type=str, default='http://localhost:9200',
                        help='URL Elasticsearch (domyślnie: http://localhost:9200)')

    args = parser.parse_args()

    # Utwórz i uruchom agenta
    agent = LogAgent(elasticsearch_host=args.elasticsearch)

    print(f"=== Intelligent Log Manager Agent ===")
    print(f"Plik: {os.path.abspath(args.file)}")
    print(f"Serwis: {args.service}")
    print(f"Elasticsearch: {args.elasticsearch}")
    print("Naciśnij Ctrl+C aby zatrzymać")
    print("=====================================")

    try:
        agent.read_log_file(args.file, args.service)
    except KeyboardInterrupt:
        agent.logger.info("Agent zatrzymany przez użytkownika")


if __name__ == "__main__":
    main()