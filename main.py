import base64
import json
import logging
import os
import re
import uuid
from datetime import datetime
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models.gigachat import GigaChat
from typing import List, Optional, Union
import pytesseract
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
import fitz
import configparser


app = FastAPI()


HISTORY_FILE = "history.json"


origins = [
    "http://localhost:5173",
    "http://localhost:4173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


try:
    config = configparser.RawConfigParser()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, 'data', 'config.ini')
    config.read(config_file_path)
    temp_path = "/images"
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)

    host = config.get("ENVIRONMENT", "HOST")
    port = int(config.get("ENVIRONMENT", "PORT"))
    credentials = config.get("ENVIRONMENT", "GIGACHAT_CREDENTIALS")
except Exception as e:
    print(f"Error reading configuration: {e}")


class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Union[dict, list, str]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None


class HistoryEntry(BaseModel):
    uid: str
    summary: str
    timestamp: str
    plantuml_code: str


class HistoryResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[List[HistoryEntry]] = None


def send_to_giga(payload):
    # OTM2NDRlNDgtMmNkYi00YWZhLThiZTktYjE0YTk2YzkzYzY4OjQ5ZGNhMzVkLTg1OTMtNDZlYy05YmIwLTA5OTQ4MzczMGUwOA==
    chat = GigaChat(credentials="OTM2NDRlNDgtMmNkYi00YWZhLThiZTktYjE0YTk2YzkzYzY4OjQ5ZGNhMzVkLTg1OTMtNDZlYy05YmIwLTA5OTQ4MzczMGUwOA==",
                    scope="GIGACHAT_API_PERS", verify_ssl_certs=False, model="GigaChat")

    messages = [
        SystemMessage(
            content="Ты бот, который помогает пользователю выделить основную часть текста и постоить mindmap на языке plantuml"
        ),
        HumanMessage(content=payload)

    ]

    res = chat(messages)
    messages.append(res)
    return res.content


def save_to_history(summary: str, plantuml_code: str) -> str:
    uid = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    history_entry = {
        "uid": uid,
        "timestamp": timestamp,
        "summary": summary,
        "plantuml_code": plantuml_code
    }

    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        else:
            history = {}
        history[uid] = history_entry
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

    except Exception as e:
        logging.error(f"Error saving history: {e}")
    
    return uid


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except UnicodeDecodeError:
            with open(HISTORY_FILE, "r", encoding="latin-1") as f:
                return json.load(f)
    return {}


def convert_to_json(file_name: str = None, file_format: str = None, base64_str: str = None):
    return {
        "ObjectName": file_name,
        "ObjectFormat": file_format,
        "Object": base64_str
    }


def convert_input_to_format(file_input: dict, temp_path: str):
    try:
        base64_str = file_input['Object']
        file_name = file_input['ObjectName']
        file_format = file_input['ObjectFormat']
        decoded_bytes = base64.b64decode(base64_str)
        file_path = os.path.join(temp_path, f"{file_name}.{file_format}")
        with open(file_path, "wb") as output_file:
            output_file.write(decoded_bytes)
        return file_path
    except Exception as e:
        logging.error(str(e), exc_info=True)


class PDFSplitter:
    def __init__(self):
        pass

    def split_pdf_to_images(self, pstr_pdf_file_path: str, pstr_temp_folder_path: str):
        try:
            llist_pages = []
            pdf_document = fitz.open(pstr_pdf_file_path)
            for page_number in range(pdf_document.page_count):
                page = pdf_document[page_number]
                image = page.get_pixmap()
                lint_page_number = page_number + 1
                image_path = os.path.join(pstr_temp_folder_path, f"page_{
                                          lint_page_number}.png")
                image.save(image_path, "png")
                llist_pages.append(
                    {"page_number": lint_page_number, "page_path": image_path})
            pdf_document.close()
            return llist_pages
        except Exception as e:
            logging.error(str(e), exc_info=True)


class GetTextFromImage:
    def __init__(self):
        self.obj_pdf_splitter = PDFSplitter()
        self.language = ["eng", "rus"]

    def get_text_from_image_path(self, pstr_file_path: str):
        try:
            llst_file_path = []
            if self.get_file_format(pstr_file_path) == "pdf":
                llst_file_path = self.get_images_from_pdf_file(pstr_file_path)
            else:
                llst_file_path = [
                    {"page_number": 1, "page_path": pstr_file_path}]
            llst_file_path = self.extract_text_from_image(llst_file_path)
            return llst_file_path
        except Exception as e:
            logging.error(str(e), exc_info=True)

    def extract_text_from_image(self, list_images: list):
        try:
            lang_string = '+'.join(self.language)
            custom_config = f'-l {lang_string} --psm 6'
            for ldict_image in list_images:
                image = Image.open(ldict_image['page_path'])

                text = pytesseract.image_to_string(image, config=custom_config)
                ldict_image['text'] = text
            return list_images
        except Exception as e:
            logging.error(str(e), exc_info=True)

    def get_images_from_pdf_file(self, pstr_file_path: str):
        try:
            return self.obj_pdf_splitter.split_pdf_to_images(pstr_file_path, "images")
        except Exception as e:
            logging.error(str(e), exc_info=True)

    def get_file_format(self, pstr_file_path):
        try:
            root, extension = os.path.splitext(pstr_file_path)
            return extension[1:]  # Возвращает расширение файла без точки
        except Exception as e:
            logging.error(str(e), exc_info=True)


def clean_and_merge_text(llist_file_path):
    combined_text = []
    prompt = """
Преобразуй текст в JSON-формат с полями "summary" и "plantuml_code". JSON должен СТРОГО соответствовать следующей структуре: 
> 
> { 
>   "summary": "<основная тема из текста>" 
>   "plantuml_code": "@startmindmap\n* Операционные системы для серверов\n** Linux\n*** Преимущества\n**** Открытый код\n**** Масштабируемость\n**** Безопасность\n*** Применение\n**** Облачные вычисления\n***** Контейнеризация\n***** Виртуализация\n** Windows Server\n*** Преимущества\n**** Простота управления\n**** Интеграция с продуктами Microsoft\n*** Недостатки\n**** Лицензирование\n** BSD-системы\n*** Основные представители\n**** FreeBSD\n**** NetBSD\n**** OpenBSD\n*** Преимущества\n**** Надежность и стабильность\n**** Высокий уровень безопасности\n**** Масштабируемость\n*** Сферы применения\n**** Маршрутизация\n***** Сетевые решения\n** Критерии выбора серверной операционной системы\n*** Производительность\n*** Безопасность\n*** Стоимость владения\n*** Совместимость\n*** Поддержка и обновления\n** Тенденции серверных операционных систем\n*** Облачные решения\n**** Контейнеризация и микросервисы\n**** Интеграция с облачными платформами\n**** Автоматизация и DevOps\n*** Кибербезопасность в серверных операционных системах\n**** Linux\n**** Windows Server\n**** BSD-системы\n*** Автоматизация серверных операций\n**** Инструменты автоматизации\n***** DevOps и CI/CD\n**** Контейнеризация\n**** Мониторинг и самовосстановление\n**** Infrastructure as Code\n** Будущее серверных ОС\n*** Облачные нативные OC\n**** Квантовые вычисления\n**** Искусственный интеллект\n**** Serverless\n** Заключение\n*** Лидерство Linux\n**** Популярность Windows Server\n**** Стабильность BSD-систем\n*** Современные тенденции\n**** Облачные решения\n**** Контейнеризация\n**** Автоматизация\n*** Будущее серверных ОС\n@endmindmap" 
> } 
> 
> Обрати внимание, что текст и структура JSON должны точно соответствовать образцу. Не добавляй никаких лишних данных, комментариев или объяснений.
> Переносы строк должны обозначаться СТРОГО через \n. НЕ ОСТАВЛЯЙ ПУСТЫХ СТРОК НА МЕСТЕ ПЕРЕНОСА СТРОК
> НЕ ЗАБЫВАЙ ЗАКРЫВАТЬ ФИГУРНЫЕ СКОБКИ JSON. ВНИМАТЕЛЬНО ПРОВЕРЯЙ ЕГО ПРАВЕЛЬНОСТЬ!
> Символы * ДОЛЖНЫ! идти последовательно, например после ** не может идти ****, а должно идти либо ** либо ***
> ЕЩЕ РАЗ ПРОВЕРЯЙ, ЧТО ТЫ МНЕ ОТПРАВЛЯЕШЬ!!! ВСЕ ИНСТРУКЦИИ ВЫШЕ ОБЯЗАТЕЛЬНЫ
> СОКРАТИ ЕСЛИ НУЖНО ДО 4 главных выводов!
"""

    for page in llist_file_path:
        text = page.get('text', '')

        text = re.sub(r'\f', '', text)
        text = re.sub(r'\n+', '\n', text)
        text = text.strip()

        combined_text.append(text)

    pre_final_text = '\n\n'.join(combined_text)

    final_text = prompt + '\n\n' + pre_final_text

    return final_text


def clean_json_string(json_string):
    pattern = r'"plantuml_code":\s*"([^"]*?)"'

    parts = re.split(pattern, json_string)

    cleaned_string = ""
    for i, part in enumerate(parts):
        if i % 2 == 0:
            cleaned_string += re.sub(r'\n', ' ', part)
        else:
            cleaned_string += f'"plantuml_code": "{part}"'

    return cleaned_string




def format_mindmap(text):
    formatted_text = re.sub(r"(\s)\*", r"\n*", text)

    formatted_text = formatted_text.replace(
        "@startmindmap", "@startmindmap\n").replace("@endumindmap", "\n@endmindmap")

    return formatted_text


@app.get("/history/{uid}", response_model=Union[HistoryEntry, ErrorResponse])
async def get_history(uid: str):
    history = load_history()

    if uid in history:
        return HistoryEntry(**history[uid])
    else:
        raise HTTPException(status_code=404, detail="History entry not found")


@app.get("/history", response_model=HistoryResponse)
async def get_all_history():
    history = load_history()

    history_entries = [HistoryEntry(**entry) for entry in history.values()]

    return HistoryResponse(message="History retrieved successfully", data=history_entries)


@app.post("/file_for_text_extract/")
async def file_for_text_extract(file: UploadFile = File(...)):
    file_contents = await file.read()
    base64_string = base64.b64encode(file_contents).decode()
    file_input = convert_to_json(
        file.filename, file.filename.split(".")[-1], base64_string)
    lstr_file_path = convert_input_to_format(file_input, temp_path)

    lobj_text_from_image = GetTextFromImage()
    llist_file_path = lobj_text_from_image.get_text_from_image_path(
        lstr_file_path)
    cleaned_data = clean_and_merge_text(llist_file_path=llist_file_path)
    data = send_to_giga(cleaned_data)
    print(data)

    data = re.sub(r"^```json|```$", "", data.strip())
    data = clean_json_string(data)
    data = data.replace("  ", "", -1)
    data = data.replace('\n', '\\n')

    try:
        parsed_data = json.loads(data)
        summary = parsed_data.get("summary", "")
        plantuml_code = parsed_data.get("plantuml_code", "")

        uid = save_to_history(summary, plantuml_code)

        response_data = {"uid": uid, "summary": summary,
                         "plantuml_code": plantuml_code}
        return SuccessResponse(message="Request processed successfully", data=response_data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Failed to parse JSON")


@app.post("/test_file_for_text_extract/")
async def test_file_for_text_extract(file: UploadFile = File(...)):
    mock_response = {
        "summary": "Тестовая тема",
        "plantuml_code": "@startmindmap\n* Тестовая тема\n** Тестовый ключевой пункт\n*** Подпункт 1\n@endmindmap"
    }

    return SuccessResponse(message="Test request processed successfully", data=mock_response)
