FROM python:3.11-slim

WORKDIR /app

COPY requirements_simple.txt .
RUN pip install --no-cache-dir -r requirements_simple.txt

COPY simple_api.py .

EXPOSE 3000

CMD ["python", "simple_api.py"]