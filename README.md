# Текстовый анализатор и генератор MindMap

## Описание

Этот проект представляет собой API для извлечения текста из изображений и PDF-документов, а также генерации краткого содержания и диаграмм MindMap в формате PlantUML. Он использует искусственный интеллект для обработки текста и представления его в структурированном виде.

## Возможности

- Извлечение текста из изображений и PDF-документов.
- Генерация краткого содержания из извлеченного текста.
- Создание диаграмм MindMap на основе содержания.
- Сохранение истории запросов и результатов.

## Технологии

- **FastAPI**: Для создания API.
- **PIL (Pillow)**: Для обработки изображений.
- **PyTesseract**: Для распознавания текста из изображений.
- **PyMuPDF (fitz)**: Для работы с PDF-документами.
- **LangChain**: Для взаимодействия с языковыми моделями.
- **Docker**: Для контейнеризации приложения.

## Установка и запуск через Docker Compose

1. **Клонируйте репозиторий:**

2. **Обновите файл конфигурации:**

   ```ini
   [ENVIRONMENT]
   HOST = 0.0.0.0
   PORT = 8000
   ```

3. **Запустите Docker Compose:**


   ```bash
   docker-compose up --build
   ```

   Это создаст и запустит контейнеры, а также установит все необходимые зависимости.

## Использование

API поддерживает следующие конечные точки:

### 1. Извлечение текста из файла

- **URL**: `/file_for_text_extract/`
- **Метод**: `POST`
- **Тело запроса**: Мультимедийный файл (изображение или PDF).

**Пример запроса**:

```bash
curl -X POST "http://127.0.0.1:8000/file_for_text_extract/" -F "file=@path_to_your_file"
```

### 2. Получение истории

- **URL**: `/history/`
- **Метод**: `GET`
- **Ответ**: Список всех записей истории.

```bash
curl -X GET "http://127.0.0.1:8000/history/"
```

### 3. Получение конкретной записи по UID

- **URL**: `/history/{uid}`
- **Метод**: `GET`
- **Параметры**: `uid` - уникальный идентификатор записи.

```bash
curl -X GET "http://127.0.0.1:8000/history/{uid}"
```

## Лицензия

Этот проект лицензирован под MIT License. См. файл [LICENSE](LICENSE) для получения подробной информации.

## Контрибьюция

Если вы хотите внести изменения, создайте форк репозитория, внесите ваши изменения и создайте pull request.

## Авторы

- [Akkato47](https://github.com/Akkato47)
