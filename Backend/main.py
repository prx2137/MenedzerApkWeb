from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import json
import time
import sqlite3
from contextlib import asynccontextmanager
import yaml
import requests


# Manager połączeń WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

# Połączenie z Elasticsearch
es = Elasticsearch(["http://localhost:9200"])


# Czekaj na Elasticsearch
def wait_for_elasticsearch():
    for i in range(30):
        try:
            if es.ping():
                print("✅ Connected to Elasticsearch")
                return True
        except Exception as e:
            print(f"⏳ Waiting for Elasticsearch... ({i + 1}/30) - Error: {e}")
        time.sleep(1)
    print("❌ Could not connect to Elasticsearch")
    return False


# System alertów w tle
async def alert_monitor():
    """Monitor logów w poszukiwaniu błędów"""
    while True:
        try:
            # Sprawdź błędy z ostatnich 5 minut
            five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()

            error_count = es.count(
                index="application-logs",
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"level": "ERROR"}},
                                {"range": {
                                    "timestamp": {"gte": five_min_ago}
                                }}
                            ]
                        }
                    }
                }
            )

            # Jeśli więcej niż 10 błędów w ciągu 5 minut - alert
            if error_count["count"] > 10:
                alert_message = {
                    "type": "alert",
                    "data": {
                        "title": "High Error Rate",
                        "message": f"Found {error_count['count']} errors in last 5 minutes",
                        "level": "CRITICAL",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await manager.broadcast(json.dumps(alert_message))

            await asyncio.sleep(60)

        except Exception as e:
            print(f"Alert monitor error: {e}")
            await asyncio.sleep(60)


# Helper functions for direct source reading
def read_from_database(db_path: str = "logs.db", limit: int = 100):
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
        print(f"Error reading from database: {e}")
        return []


def read_from_file(file_path: str, service_name: str, limit: int = 100):
    """Czytaj logi z pliku tekstowego"""
    logs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-limit:]  # Ostatnie `limit` linii
            for line in lines:
                if line.strip():
                    # Prosta detekcja poziomu logu
                    line_lower = line.lower()
                    if "error" in line_lower:
                        level = "ERROR"
                    elif "warning" in line_lower or "warn" in line_lower:
                        level = "WARNING"
                    elif "debug" in line_lower:
                        level = "DEBUG"
                    else:
                        level = "INFO"

                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "level": level,
                        "message": line.strip(),
                        "source": "file",
                        "service": service_name,
                        "original_data": {"line": line.strip()}
                    }
                    logs.append(log_entry)
        return logs
    except Exception as e:
        print(f"Error reading from file {file_path}: {e}")
        return []


def read_from_elasticsearch(query: dict = None, limit: int = 100):
    """Czytaj logi bezpośrednio z Elasticsearch"""
    try:
        if not query:
            query = {"match_all": {}}

        result = es.search(
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
        print(f"Error reading from Elasticsearch: {e}")
        return []


def read_from_api(api_config: dict, limit: int = 100):
    """Czytaj logi z API"""
    try:
        url = api_config.get('url')
        method = api_config.get('method', 'GET')
        params = api_config.get('params', {})
        params['limit'] = limit  # Dodaj limit do parametrów

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
            print(f"API returned status {response.status_code}")
            return []
    except Exception as e:
        print(f"Error reading API logs: {e}")
        return []


def load_config(config_path: str = "config.yaml"):
    """Ładuje konfigurację z pliku YAML"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"sources": []}


# Lifespan events dla FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔄 Starting Log Manager API...")
    if not wait_for_elasticsearch():
        print("❌ Exiting due to Elasticsearch connection failure")
    asyncio.create_task(alert_monitor())
    yield
    # Shutdown
    print("🛑 Stopping Log Manager API...")


app = FastAPI(
    title="Intelligent Log Manager API",
    description="API do zarządzania i analizy logów aplikacji webowych",
    version="1.0.0",
    lifespan=lifespan
)

# POPRAWIONA KONFIGURACJA CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    source: str
    service: str


class LogQuery(BaseModel):
    level: Optional[str] = None
    service: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search_text: Optional[str] = None


# Endpointy API
@app.get("/")
async def root():
    return {
        "message": "Intelligent Log Manager API",
        "version": "1.0.0",
        "endpoints": {
            "logs": "/logs",
            "stats": "/logs/stats",
            "services": "/logs/services",
            "levels": "/logs/levels",
            "sources": "/logs/sources",
            "direct_logs": "/logs/sources/direct",
            "compare_logs": "/logs/compare",
            "source_logs": "/logs/source/{source_type}"
        }
    }


@app.post("/logs/")
async def ingest_log(log: LogEntry):
    """Dodawanie nowego logu"""
    try:
        result = es.index(
            index="application-logs",
            document=log.dict()
        )

        await manager.broadcast(json.dumps({
            "type": "new_log",
            "data": log.dict()
        }))

        return {"status": "success", "id": result["_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/")
async def get_logs(
        level: Optional[str] = None,
        service: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_text: Optional[str] = None,
        page: int = 1,
        size: int = 50
):
    """Pobieranie logów z filtrami"""
    try:
        query = {"bool": {"must": []}}

        if level:
            query["bool"]["must"].append({"term": {"level": level}})
        if service:
            query["bool"]["must"].append({"term": {"service": service}})
        if date_from and date_to:
            query["bool"]["must"].append({
                "range": {
                    "timestamp": {
                        "gte": date_from,
                        "lte": date_to
                    }
                }
            })
        if search_text:
            query["bool"]["must"].append({
                "match": {"message": search_text}
            })

        result = es.search(
            index="application-logs",
            query=query if query["bool"]["must"] else {"match_all": {}},
            from_=(page - 1) * size,
            size=size,
            sort=[{"timestamp": {"order": "desc"}}]
        )

        logs = []
        for hit in result["hits"]["hits"]:
            log_data = hit["_source"]
            log_data["id"] = hit["_id"]
            logs.append(log_data)

        total = result["hits"]["total"]["value"]

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/stats")
async def get_logs_stats():
    """Statystyki logów"""
    try:
        level_stats = es.search(
            index="application-logs",
            body={
                "size": 0,
                "aggs": {
                    "levels": {
                        "terms": {"field": "level"}
                    }
                }
            }
        )

        service_stats = es.search(
            index="application-logs",
            body={
                "size": 0,
                "aggs": {
                    "services": {
                        "terms": {"field": "service"}
                    }
                }
            }
        )

        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        recent_stats = es.search(
            index="application-logs",
            body={
                "size": 0,
                "query": {
                    "range": {
                        "timestamp": {"gte": one_hour_ago}
                    }
                },
                "aggs": {
                    "errors_last_hour": {
                        "filter": {"term": {"level": "ERROR"}}
                    }
                }
            }
        )

        return {
            "level_stats": level_stats["aggregations"]["levels"]["buckets"],
            "service_stats": service_stats["aggregations"]["services"]["buckets"],
            "recent_errors": recent_stats["aggregations"]["errors_last_hour"]["doc_count"],
            "total_logs": recent_stats["hits"]["total"]["value"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/services")
async def get_services():
    """Lista unikalnych serwisów"""
    try:
        result = es.search(
            index="application-logs",
            body={
                "size": 0,
                "aggs": {
                    "services": {
                        "terms": {
                            "field": "service",
                            "size": 100
                        }
                    }
                }
            }
        )

        services = [bucket["key"] for bucket in result["aggregations"]["services"]["buckets"]]
        return {"services": services}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/levels")
async def get_levels():
    """Lista unikalnych poziomów logów"""
    try:
        result = es.search(
            index="application-logs",
            body={
                "size": 0,
                "aggs": {
                    "levels": {
                        "terms": {
                            "field": "level",
                            "size": 10
                        }
                    }
                }
            }
        )

        levels = [bucket["key"] for bucket in result["aggregations"]["levels"]["buckets"]]
        return {"levels": levels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/sources")
async def get_sources():
    """Lista unikalnych źródeł logów"""
    try:
        result = es.search(
            index="application-logs",
            body={
                "size": 0,
                "aggs": {
                    "sources": {
                        "terms": {
                            "field": "source.keyword",
                            "size": 20
                        }
                    }
                }
            }
        )

        sources = [bucket["key"] for bucket in result["aggregations"]["sources"]["buckets"]]
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/stats/sources")
async def get_source_stats():
    """Statystyki per źródło"""
    try:
        result = es.search(
            index="application-logs",
            body={
                "size": 0,
                "aggs": {
                    "sources": {
                        "terms": {
                            "field": "source.keyword",
                            "size": 10
                        }
                    },
                    "sources_by_level": {
                        "terms": {
                            "field": "source.keyword",
                            "size": 10
                        },
                        "aggs": {
                            "levels": {
                                "terms": {
                                    "field": "level.keyword"
                                }
                            }
                        }
                    }
                }
            }
        )

        return {
            "source_stats": result["aggregations"]["sources"]["buckets"],
            "detailed_stats": result["aggregations"]["sources_by_level"]["buckets"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/sources/direct")
async def get_logs_from_all_sources():
    """Pobierz logi ze wszystkich źródeł jednocześnie"""
    try:
        all_logs = []

        # 1. Z Elasticsearch (główne repozytorium)
        es_logs = read_from_elasticsearch(limit=50)
        for log in es_logs:
            log["source_type"] = "elasticsearch"
            all_logs.append(log)

        # 2. Z bazy danych SQLite (jeśli istnieje)
        try:
            db_logs = read_from_database("logs.db", limit=50)
            for log in db_logs:
                log["source_type"] = "database"
                all_logs.append(log)
        except Exception as e:
            print(f"Database read error: {e}")

        # 3. Z plików logów (z konfiguracji)
        config = load_config()
        for source in config.get('sources', []):
            if source['type'] == 'file':
                try:
                    file_logs = read_from_file(
                        source['path'],
                        source.get('service', 'unknown'),
                        limit=50
                    )
                    for log in file_logs:
                        log["source_type"] = "file"
                        all_logs.append(log)
                except Exception as e:
                    print(f"File read error for {source['path']}: {e}")

        # 4. Z API (jeśli skonfigurowane)
        for source in config.get('sources', []):
            if source['type'] == 'api':
                try:
                    api_logs = read_from_api(source, limit=50)
                    for log in api_logs:
                        log["source_type"] = "api"
                        all_logs.append(log)
                except Exception as e:
                    print(f"API read error for {source['url']}: {e}")

        # Sortuj po timestamp (malejąco)
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return {
            "success": True,
            "total": len(all_logs),
            "logs": all_logs[:100],  # Limit do 100 wpisów
            "sources_present": list(set([log.get("source_type", "unknown") for log in all_logs]))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/source/{source_type}")
async def get_logs_by_source(
        source_type: str,
        limit: int = 50,
        service: Optional[str] = None
):
    """Pobierz logi z konkretnego źródła"""
    try:
        logs = []

        if source_type == "elasticsearch":
            query = {}
            if service:
                query = {"term": {"service": service}}
            logs = read_from_elasticsearch(query, limit)

        elif source_type == "database":
            db_logs = read_from_database("logs.db", limit=limit)
            if service:
                logs = [log for log in db_logs if log.get("service") == service]
            else:
                logs = db_logs

        elif source_type == "file":
            config = load_config()
            for source in config.get('sources', []):
                if source['type'] == 'file' and (not service or source.get('service') == service):
                    file_logs = read_from_file(
                        source['path'],
                        source.get('service', 'unknown'),
                        limit=limit
                    )
                    logs.extend(file_logs)
            # Ogranicz do `limit` po zebraniu wszystkich plików
            logs = logs[:limit]

        elif source_type == "api":
            config = load_config()
            for source in config.get('sources', []):
                if source['type'] == 'api' and (not service or source.get('service') == service):
                    api_logs = read_from_api(source, limit=limit)
                    logs.extend(api_logs)
            logs = logs[:limit]

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source type: {source_type}")

        return {
            "success": True,
            "source": source_type,
            "total": len(logs),
            "logs": logs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/compare")
async def compare_logs_across_sources(
        time_range: str = "5m",  # 5m, 1h, 24h
        service: Optional[str] = None
):
    """Porównaj logi z różnych źródeł w tym samym przedziale czasowym"""
    try:
        # Oblicz timestamp dla zakresu
        now = datetime.now()
        if time_range == "5m":
            start_time = now - timedelta(minutes=5)
        elif time_range == "1h":
            start_time = now - timedelta(hours=1)
        else:  # 24h
            start_time = now - timedelta(days=1)

        results = {}

        # Logi z Elasticsearch
        es_query = {
            "range": {
                "timestamp": {
                    "gte": start_time.isoformat()
                }
            }
        }
        if service:
            es_query = {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"gte": start_time.isoformat()}}},
                        {"term": {"service": service}}
                    ]
                }
            }

        es_logs = read_from_elasticsearch(es_query, 100)
        results["elasticsearch"] = {
            "count": len(es_logs),
            "sample": es_logs[:5] if es_logs else []
        }

        # Logi z bazy danych
        try:
            db_logs = read_from_database("logs.db", limit=1000)  # Wczytaj więcej, aby móc filtrować
            db_logs_filtered = []
            for log in db_logs:
                try:
                    log_time = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                    if log_time >= start_time and (not service or log.get("service") == service):
                        db_logs_filtered.append(log)
                except:
                    # Jeśli nie uda się sparsować timestamp, pomiń
                    continue
            results["database"] = {
                "count": len(db_logs_filtered),
                "sample": db_logs_filtered[:5] if db_logs_filtered else []
            }
        except Exception as e:
            results["database"] = {"count": 0, "sample": [], "error": str(e)}

        # Logi z plików
        config = load_config()
        file_logs_all = []
        for source in config.get('sources', []):
            if source['type'] == 'file' and (not service or source.get('service') == service):
                try:
                    file_logs = read_from_file(
                        source['path'],
                        source.get('service', 'unknown'),
                        limit=1000
                    )
                    file_logs_all.extend(file_logs)
                except:
                    pass
        # Dla plików, ponieważ nie mamy dokładnego timestamp, zakładamy, że są aktualne
        results["file"] = {
            "count": len(file_logs_all),
            "sample": file_logs_all[:5] if file_logs_all else []
        }

        # Logi z API
        api_logs_all = []
        for source in config.get('sources', []):
            if source['type'] == 'api' and (not service or source.get('service') == service):
                try:
                    api_logs = read_from_api(source, limit=1000)
                    api_logs_all.extend(api_logs)
                except:
                    pass
        results["api"] = {
            "count": len(api_logs_all),
            "sample": api_logs_all[:5] if api_logs_all else []
        }

        return {
            "success": True,
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "service": service,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket dla rzeczywistych aktualizacji
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    # Dla development z reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)