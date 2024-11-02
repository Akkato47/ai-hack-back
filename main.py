import base64
import json
import logging
import os
import re
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models.gigachat import GigaChat
import requests
from typing import List, Optional, Union
import pytesseract
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
import fitz  # PyMuPDF
import configparser

# Настройка FastAPI
app = FastAPI()

# Настройка CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def send_to_giga(payload):
    chat = GigaChat(credentials="YzdmYmZkYjMtNzgyNS00MTAzLTkxM2QtOTY0ZTdmZmNlZWZkOmEzOWE4MDQ5LTFhMGItNDEwMi04N2MxLTNlZTcwYjQyMmRhNQ==",
                    scope="GIGACHAT_API_PERS", verify_ssl_certs=False)

    messages = [
        SystemMessage(
            content="Ты бот, который помогает пользователю выделить основную часть текста и постоить mindmap на языке plantuml"
        ),
        HumanMessage(content=payload)

    ]

    res = chat(messages)
    messages.append(res)
    return res.content


def parse_response(response):
    parsed_json = json.loads(response)

    if parsed_json.get("success") is True:
        data_content = parsed_json.get("data", "")
        match = re.search(r'```json\n(.+?)\n```', data_content, re.DOTALL)
        if match:
            inner_json_str = match.group(1)
            inner_json = json.loads(inner_json_str)

            summary = inner_json.get("summary")
            plantuml_code = inner_json.get("plantuml_code")

            return {
                "summary": summary,
                "plantuml_code": plantuml_code
            }

    return None


class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Union[dict, list, str]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None


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


try:
    config = configparser.RawConfigParser()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, 'data', 'config.ini')
    config.read(config_file_path)
    temp_path = config.get("ENVIRONMENT", "TEMP_FOLDER_PATH")
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)
    host = config.get("ENVIRONMENT", "HOST")
    port = int(config.get("ENVIRONMENT", "PORT"))
except Exception as e:
    print(f"Error reading configuration: {e}")


def clean_and_merge_text(llist_file_path):
    combined_text = []
    prompt = """
Добавь к этому тексту следующий промпт в начале: 
Преобразуй текст в JSON-формат с полями "summary" и "plantuml_code". JSON должен строго соответствовать следующей структуре: 
> ```json 
> { 
>   "summary": { 
>     "Основная тема": "<основная тема из текста>" 
>   }, 
>   "plantuml_code": "@startmindmap\n* <основная тема из текста>\n** Ключевой пункт 1\n*** Подпункт 1.1\n*** Подпункт 1.2\n** Ключевой пункт 2\n*** Подпункт 2.1\n**** Детали\n*** Подпункт 2.2\n** Ключевой пункт 3\n*** Подпункт 3.1\n@endmindmap" 
> } 
> ``` 
> Обрати внимание, что текст и структура JSON должны точно соответствовать образцу. Не добавляй никаких лишних данных, комментариев или объяснений.
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
    pattern = r'("plantuml_code":\s*"[^"]*?)\\n([^"]*?")'

    cleaned_string = re.sub(r'\n', ' ', json_string)

    cleaned_string = re.sub(pattern, lambda m: m.group(
        1) + '\n' + m.group(2), cleaned_string)

    return cleaned_string


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
#     data = """```json
# {
#     "summary": {
#         "Основная тема": "Сравнение операционных систем для серверов"
#     },
#     "plantuml_code": "@startmindmap\n* Сравнение операционных систем для серверов\n** Linux\n*** Преимущества Linux\n**** Открытый код\n**** Масштабируемость\n**** Безопасность\n** Windows Server\n*** Преимущества Windows Server\n**** Простота управления\n**** Интеграция с Мегозой-продуктами\n**** Безопасность и поддержка\n** BSD-системы\n*** Преимущества BSD-систем\n**** Надежность и стабильность\n**** Высокий уровень безопасности\n** Роль Linux в серверных системах\n** Windows Server в бизнесе\n** Критерии выбора серверной операционной системы\n** Тенденции серверных операционных систем\n** Кибербезопасность в серверных операционных системах\n** Автоматизация серверных операций\n** Будущее серверных операционных систем\n** Заключение\n@endmindmap"
# }
#     ```"""

    # Удаление обертки ```json и ```
    data = re.sub(r"^```json|```$", "", data.strip())

    data = clean_json_string(data)
    data = data.replace("  ", "", -1)
    data = data.replace('\n', '\\n')
    # Парсинг JSON-данных
    # return SuccessResponse(message="Request processed successfully", data=data)
    try:
        parsed_data = json.loads(data)

        return SuccessResponse(message="Request processed successfully", data=parsed_data)
    except json.JSONDecodeError as e:
        return ErrorResponse(message="Failed to parse JSON", error_code="JSONDecodeError")


@app.post("/test_file_for_text_extract/")
async def test_file_for_text_extract(file: UploadFile = File(...)):
    mock_response = {
        "summary": {
            "Основная тема": "Тестовая тема"
        },
        "plantuml_code": "@startmindmap\n* Тестовая тема\n** Тестовый ключевой пункт\n*** Подпункт 1\n@endmindmap"
    }

    return SuccessResponse(message="Test request processed successfully", data=mock_response)