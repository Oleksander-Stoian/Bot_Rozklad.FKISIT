FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# --proxy-headers + trusted proxy: за NPM беремо реальний IP клієнта з X-Forwarded-For
# (потрібно для rate-limit логіну). Обмежуємо довіру docker-мережею NPM.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]