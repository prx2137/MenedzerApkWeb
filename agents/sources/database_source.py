import sqlite3
import logging
from typing import List, Dict, Any


class DatabaseSource:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection = None

    def connect(self) -> bool:
        try:
            db_path = self.config.get('path', 'logs.db')
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def read_logs(self) -> List[Dict[str, Any]]:
        if not self.connection:
            if not self.connect():
                return []

        try:
            cursor = self.connection.cursor()
            limit = self.config.get('limit', 100)

            query = self.config.get('query', '''
                SELECT * FROM logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''')

            cursor.execute(query, (limit,))
            logs = []
            for row in cursor.fetchall():
                log_entry = {
                    "timestamp": row["timestamp"],
                    "level": row["level"],
                    "message": row["message"],
                    "source": self.name,
                    "service": row.get("service", self.config.get('service', 'database')),
                    "original_data": dict(row)
                }
                logs.append(log_entry)

            return logs
        except Exception as e:
            self.logger.error(f"Error reading database logs: {e}")
            return []