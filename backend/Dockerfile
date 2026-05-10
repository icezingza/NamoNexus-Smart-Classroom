FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง Curl สำหรับการทำ Health Check
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV NAMO_API_HOST=0.0.0.0
CMD ["python", "-m", "namo_core.main"]