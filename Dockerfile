# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем необходимые зависимости для Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Указываем переменные окружения для FastAPI
ENV TEMP_FOLDER_PATH=/app/images
ENV HOST=0.0.0.0 
ENV PORT=8000 

# Запускаем приложение с использованием fastapi dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
