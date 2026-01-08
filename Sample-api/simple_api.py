from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import time
import random
import threading
import os

app = Flask(__name__)
CORS(app)  # Włącz CORS

# Użyj SQLite zamiast MySQL
DB_FILE = 'logs.db'


def init_database():
    """Inicjalizacja bazy danych SQLite"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Tabela logów
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                service TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT DEFAULT 'api'
            )
        ''')

        # Tabela serwisów
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')

        # Dodaj domyślne serwisy
        services = [
            ('frontend-ui', 'User Interface'),
            ('backend-api', 'Backend API'),
            ('database', 'Database Service'),
            ('auth-service', 'Authentication'),
            ('payment-service', 'Payment Processing')
        ]

        for service in services:
            cursor.execute('INSERT OR IGNORE INTO services (name, description) VALUES (?, ?)', service)

        # Dodaj przykładowe logi
        sample_logs = [
            ('INFO', 'frontend-ui', 'Application started successfully', 'system'),
            ('INFO', 'backend-api', 'Server listening on port 8080', 'api'),
            ('WARN', 'database', 'Slow query detected', 'database'),
            ('ERROR', 'auth-service', 'Token validation failed', 'api'),
            ('INFO', 'payment-service', 'Payment processed: $49.99', 'api')
        ]

        for log in sample_logs:
            cursor.execute(
                'INSERT INTO logs (level, service, message, source) VALUES (?, ?, ?, ?)',
                log
            )

        conn.commit()
        conn.close()

        print(f"✅ Database initialized: {DB_FILE}")
        return True

    except Exception as e:
        print(f"❌ Database init failed: {e}")
        return False


def get_db():
    """Pobierz połączenie z bazą danych"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'log-api',
            'database': 'sqlite'
        })
    except:
        return jsonify({'status': 'unhealthy'}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Pobierz logi z bazy"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        level = request.args.get('level')
        service = request.args.get('service')

        conn = get_db()
        cursor = conn.cursor()

        # Buduj zapytanie
        query = 'SELECT * FROM logs WHERE 1=1'
        params = []

        if level:
            query += ' AND level = ?'
            params.append(level)

        if service:
            query += ' AND service = ?'
            params.append(service)

        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]

        # Pobierz całkowitą liczbę
        cursor.execute('SELECT COUNT(*) as total FROM logs')
        total = cursor.fetchone()['total']

        conn.close()

        return jsonify({
            'success': True,
            'logs': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/logs', methods=['POST'])
def add_log():
    """Dodaj nowy log"""
    try:
        data = request.json

        required = ['level', 'service', 'message']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing {field}'}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO logs (timestamp, level, service, message, source) VALUES (?, ?, ?, ?, ?)',
            (
                data.get('timestamp', datetime.now().isoformat()),
                data['level'],
                data['service'],
                data['message'],
                data.get('source', 'api')
            )
        )

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'id': log_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/services', methods=['GET'])
def get_services():
    """Pobierz listę serwisów"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name, description FROM services ORDER BY name')
        services = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'services': services})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Statystyki logów"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Statystyki per poziom
        cursor.execute('SELECT level, COUNT(*) as count FROM logs GROUP BY level ORDER BY count DESC')
        level_stats = [dict(row) for row in cursor.fetchall()]

        # Statystyki per serwis
        cursor.execute('SELECT service, COUNT(*) as count FROM logs GROUP BY service ORDER BY count DESC')
        service_stats = [dict(row) for row in cursor.fetchall()]

        # Ostatnia godzina
        cursor.execute('''
            SELECT COUNT(*) as recent 
            FROM logs 
            WHERE timestamp >= datetime("now", "-1 hour")
        ''')
        recent = cursor.fetchone()['recent']

        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'levels': level_stats,
                'services': service_stats,
                'recent_hour': recent,
                'total': sum(item['count'] for item in level_stats)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def log_generator():
    """Generator przykładowych logów"""
    time.sleep(5)  # Poczekaj na start API

    services = ['frontend-ui', 'backend-api', 'database', 'auth-service', 'payment-service']
    levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']

    while True:
        try:
            service = random.choice(services)
            level = random.choice(levels)

            messages = {
                'frontend-ui': [
                    'User clicked button',
                    'Page loaded',
                    'Form submitted',
                    'Route changed'
                ],
                'backend-api': [
                    'Processing request',
                    'Database query',
                    'Cache updated',
                    'Response sent'
                ],
                'database': [
                    'Query executed',
                    'Connection opened',
                    'Transaction started',
                    'Index used'
                ]
            }

            message = random.choice(messages.get(service, ['System event']))
            full_message = f"{message} at {datetime.now().strftime('%H:%M:%S')}"

            # Dodaj przez API
            import requests
            requests.post(
                'http://localhost:3000/api/logs',
                json={
                    'level': level,
                    'service': service,
                    'message': full_message,
                    'source': 'generator'
                },
                timeout=2
            )

            print(f"📝 Generated: {service} - {level}")

        except Exception as e:
            pass  # Ignoruj błędy

        time.sleep(random.uniform(3, 8))


if __name__ == '__main__':
    print("🚀 Simple Log API (SQLite)")
    print("=" * 50)

    if init_database():
        # Uruchom generator w tle
        thread = threading.Thread(target=log_generator, daemon=True)
        thread.start()

        print("✅ Database ready")
        print("🌐 API available at: http://localhost:3000")
        print("📊 Endpoints:")
        print("  GET  /api/health     - Health check")
        print("  GET  /api/logs       - Get logs")
        print("  POST /api/logs       - Add log")
        print("  GET  /api/services   - Get services")
        print("  GET  /api/stats      - Get statistics")
        print("=" * 50)

        app.run(host='0.0.0.0', port=3000, debug=False)
    else:
        print("❌ Failed to start")