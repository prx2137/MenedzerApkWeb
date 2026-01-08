import os
from datetime import datetime
import logging
from typing import List, Dict, Any


class FileSource:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.file_path = config.get('path')
        self.service = config.get('service', 'unknown')
        self.file = None
        self.last_position = 0

    def connect(self) -> bool:
        try:
            if os.path.exists(self.file_path):
                self.file = open(self.file_path, 'r', encoding='utf-8')
                # Przesuń się na koniec pliku
                self.file.seek(0, os.SEEK_END)
                self.last_position = self.file.tell()
                return True
            else:
                self.logger.error(f"File not found: {self.file_path}")
                return False
        except Exception as e:
            self.logger.error(f"File open error: {e}")
            return False

    def disconnect(self) -> None:
        if self.file:
            self.file.close()
            self.file = None

    def read_logs(self) -> List[Dict[str, Any]]:
        if not self.file:
            if not self.connect():
                return []

        try:
            self.file.seek(self.last_position)
            lines = self.file.readlines()
            self.last_position = self.file.tell()

            logs = []
            for line in lines:
                if line.strip():
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "level": self._detect_log_level(line),
                        "message": line.strip(),
                        "source": self.name,
                        "service": self.service,
                        "original_data": {"raw_line": line.strip()}
                    }
                    logs.append(log_entry)

            return logs
        except Exception as e:
            self.logger.error(f"Error reading file logs: {e}")
            return []

    def _detect_log_level(self, line: str) -> str:
        line_lower = line.lower()
        if any(word in line_lower for word in ['error', 'exception', 'failed']):
            return 'ERROR'
        elif any(word in line_lower for word in ['warning', 'warn']):
            return 'WARNING'
        elif 'debug' in line_lower:
            return 'DEBUG'
        else:
            return 'INFO'