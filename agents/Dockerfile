FROM python:3.11-slim

WORKDIR /app

# Kopiowanie requirements
COPY requirements.txt .

# Instalacja zależności
RUN pip install --no-cache-dir -r requirements_simple.txt

# Kopiowanie kodu źródłowego
COPY sources/ ./sources/
COPY log_agent.py .
COPY config.yaml .

# Tworzenie katalogu na logi
RUN mkdir -p /app/logs

# Uruchomienie agenta
CMD ["python", "log_agent.py", "--config", "config.yaml"]