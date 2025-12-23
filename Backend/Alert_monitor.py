import asyncio
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import smtplib
from email.mime.text import MIMEText


class AlertManager:
    def __init__(self):
        self.es = Elasticsearch(["http://localhost:9200"])
        self.alert_rules = [
            {
                "name": "High Error Rate",
                "condition": self.check_error_rate,
                "threshold": 10  # 10 błędów na minutę
            }
        ]

    async def start_monitoring(self):
        while True:
            for rule in self.alert_rules:
                if await rule["condition"](rule["threshold"]):
                    self.send_alert(rule["name"])
            await asyncio.sleep(60)  # Sprawdzaj co minutę

    async def check_error_rate(self, threshold):
        # Sprawdź liczbę błędów w ostatniej minucie
        one_minute_ago = datetime.now() - timedelta(minutes=1)

        query = {
            "bool": {
                "must": [
                    {"term": {"level": "ERROR"}},
                    {"range": {
                        "timestamp": {
                            "gte": one_minute_ago.isoformat()
                        }
                    }}
                ]
            }
        }

        result = self.es.count(
            index="application-logs",
            query=query
        )

        return result["count"] > threshold

    def send_alert(self, rule_name):
        # Implementacja wysyłania email/SMS
        print(f"ALERT: {rule_name} - Wysyłanie powiadomienia...")

        # Przykład wysyłania email
        try:
            msg = MIMEText(f"Wykryto alert: {rule_name}")
            msg['Subject'] = f'Log Alert: {rule_name}'
            msg['From'] = 'alerts@yourcompany.com'
            msg['To'] = 'admin@yourcompany.com'

            # Konfiguracja SMTP
            # s = smtplib.SMTP('localhost')
            # s.send_message(msg)
            # s.quit()

            print(f"Alert '{rule_name}' wysłany")
        except Exception as e:
            print(f"Błąd przy wysyłaniu alertu: {e}")



async def start_alert_system():
    manager = AlertManager()
    await manager.start_monitoring()