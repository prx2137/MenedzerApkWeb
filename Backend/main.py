from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import json
import time
from contextlib import asynccontextmanager

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
            print(f"⏳ Waiting for Elasticsearch... ({i+1}/30) - Error: {e}")
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
            "levels": "/logs/levels"
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