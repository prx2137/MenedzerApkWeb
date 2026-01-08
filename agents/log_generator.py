import time
import random
from datetime import datetime


def generate_frontend_logs(file_path, num_entries=10):
    """Generuje przykładowe logi frontendowe"""
    log_levels = ['INFO', 'DEBUG', 'WARN', 'ERROR']
    user_actions = [
        "User clicked login button",
        "Page loaded successfully",
        "Form validation failed",
        "API call started",
        "API call completed",
        "User session expired",
        "Component rendered",
        "State updated",
        "Route changed to /dashboard",
        "Modal opened",
        "Notification displayed",
        "User logged out"
    ]

    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(num_entries):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            level = random.choice(log_levels)
            action = random.choice(user_actions)

            log_line = f"{timestamp} {level} [frontend-ui] {action}\n"
            f.write(log_line)

            time.sleep(0.01)

    print(f"Generated {num_entries} frontend logs in: {file_path}")


def generate_backend_logs(file_path, num_entries=10):
    """Generuje przykładowe logi backendowe"""
    log_levels = ['INFO', 'DEBUG', 'WARN', 'ERROR']
    operations = [
        "Processing GET request to /api/users",
        "Database query executed successfully",
        "Authentication token validated",
        "Cache miss for key: user_123",
        "Email sent successfully",
        "Payment processed",
        "File uploaded: size=2.5MB",
        "WebSocket connection established",
        "Job scheduled: cleanup_old_data",
        "Memory usage: 45%",
        "Response time: 120ms",
        "Database connection pool: 10/20 active"
    ]

    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(num_entries):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            level = random.choice(log_levels)
            operation = random.choice(operations)

            log_line = f"{timestamp} {level} [backend-api] {operation}\n"
            f.write(log_line)

            time.sleep(0.01)

    print(f"Generated {num_entries} backend logs in: {file_path}")


def generate_database_logs(file_path, num_entries=10):
    """Generuje przykładowe logi bazodanowe"""
    log_levels = ['INFO', 'DEBUG', 'WARN', 'ERROR']
    db_operations = [
        "Query: SELECT * FROM users WHERE id = ?",
        "Transaction started",
        "Transaction committed",
        "Index created on table: orders",
        "Backup completed successfully",
        "Slow query detected: 2.5s",
        "Deadlock resolved",
        "Connection pool exhausted",
        "Replica sync in progress",
        "Table optimized: user_logs",
        "Constraint violation: duplicate key",
        "Query cache hit ratio: 85%"
    ]

    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(num_entries):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            level = random.choice(log_levels)
            operation = random.choice(db_operations)

            log_line = f"{timestamp} {level} [database] {operation}\n"
            f.write(log_line)

            time.sleep(0.01)

    print(f"Generated {num_entries} database logs in: {file_path}")


def generate_all_logs():
    """Generuje logi dla wszystkich warstw"""
    import os

    examples_dir = os.path.join(os.path.dirname(__file__), '..', 'Examples')
    os.makedirs(examples_dir, exist_ok=True)

    generate_frontend_logs(os.path.join(examples_dir, 'frontend_app.log'), 20)
    generate_backend_logs(os.path.join(examples_dir, 'backend_api.log'), 20)
    generate_database_logs(os.path.join(examples_dir, 'database.log'), 20)

    print("\n✅ All log files generated successfully!")


if __name__ == "__main__":
    generate_all_logs()