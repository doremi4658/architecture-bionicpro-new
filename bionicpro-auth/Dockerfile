FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запускаем Flask (встроенный сервер, для разработки)
CMD ["python", "main.py"]