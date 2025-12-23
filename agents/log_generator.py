import time
import random
from datetime import datetime


def generate_sample_logs(file_path, num_entries=20):
    """Generuje przykładowe logi do testowania"""

    log_levels = ['INFO', 'DEBUG', 'WARN', 'ERROR']
    services = ['web-app', 'api-service', 'auth-service', 'database-service']
    messages = [
        "User login successful",
        "Database query executed",
        "Cache miss occurred",
        "API response sent",
        "File uploaded successfully",
        "Configuration loaded",
        "Session created",
        "Password reset requested",
        "Email sent to user",
        "Payment processed",
        "Database connection pool exhausted",
        "Memory usage high",
        "Request timeout",
        "Authentication failed",
        "File not found",
        "Invalid input parameters",
        "Server starting up",
        "Server shutting down",
        "Backup completed",
        "Security alert detected"
    ]

    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(num_entries):
            # Generuj timestamp z losowym offsetem
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            level = random.choice(log_levels)
            service = random.choice(services)
            message = random.choice(messages)

            log_line = f"{timestamp} {level} [{service}] {message}\n"
            f.write(log_line)

            # Małe opóźnienie dla realistycznych timestampów
            time.sleep(0.01)

    print(f"Wygenerowano {num_entries} przykładowych logów w: {file_path}")


if __name__ == "__main__":
    generate_sample_logs('../Examples/example_app.log', 50)