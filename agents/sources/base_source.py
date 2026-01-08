from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging


class LogSource(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"source.{name}")
        self.service = config.get('service', 'unknown')

    @abstractmethod
    def connect(self) -> bool:
        """Nawiązanie połączenia ze źródłem"""
        pass

    @abstractmethod
    def disconnect(self):
        """Zamknięcie połączenia"""
        pass

    @abstractmethod
    def read_logs(self) -> list:
        """Odczyt logów ze źródła"""
        pass

    def parse_log_line(self, line: str, source_type: str = 'text') -> Optional[Dict[str, Any]]:
        """Parsuje linię logu w różnych formatach"""
        if source_type == 'json':
            import json
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse JSON line: {line[:50]}...")
                return None

        # Domyślny parser dla formatu tekstowego
        parts = line.strip().split(' ', 3)
        if len(parts) >= 4:
            timestamp_str = f"{parts[0]} {parts[1]}"
            level = parts[2]
            message = parts[3]

            # Spróbuj wyciągnąć service z message jeśli istnieje
            service = self.service
            if '[' in message and ']' in message:
                start = message.find('[') + 1
                end = message.find(']')
                if start < end:
                    service = message[start:end]
                    message = message[end + 2:]  # Usuń service z message

            return {
                "timestamp": timestamp_str,
                "level": level,
                "message": message,
                "service": service,
                "source": self.name
            }

        return None