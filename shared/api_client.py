#!/usr/bin/env python3
"""
API Client for routerai.ru
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения из .env файла в папке config
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(dotenv_path=env_path)
    print(f"Загружаем .env из: {env_path}")  # для отладки
except ImportError:
    pass  # python-dotenv не установлен, надеемся на переменные окружения

import json
import base64
import time
import requests
import re
import os
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

# Импортируем логгер
from logs.logger import get_logger

# ==================== Константы ====================

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB в байтах
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB для изображений

# ==================== Типы данных ====================

class InputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"

class OutputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"

@dataclass
class ModelConfig:
    """Конфигурация модели"""
    name: str
    api_key: str
    model_id: str
    input_types: Set[InputType]
    output_types: Set[OutputType]
    
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 120
    size: Optional[str] = None
    extra_body: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'ModelConfig':
        return cls(
            name=name,
            api_key=data['api_key'],
            model_id=data['model'],
            input_types={InputType(t) for t in data.get('input', ['text'])},
            output_types={OutputType(t) for t in data.get('output', ['text'])},
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 4000),
            timeout=data.get('timeout', 120),
            size=data.get('size'),
            extra_body=data.get('extra_body', {})
        )

# ==================== Работа с файлами ====================

class FileHandler:
    """Работа с файлами"""
    
    def __init__(self, logger, temp_dir: str = "temp", 
                 max_file_size: int = MAX_FILE_SIZE,
                 max_image_size: int = MAX_IMAGE_SIZE):
        self.logger = logger
        self.temp_dir = Path(temp_dir)
        self.images_dir = self.temp_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.max_image_size = max_image_size
        
        self.mime_map = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.webp': 'image/webp', '.bmp': 'image/bmp',
            '.pdf': 'application/pdf', '.txt': 'text/plain',
            '.md': 'text/markdown', '.csv': 'text/csv',
            '.json': 'application/json', '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
            '.mp4': 'video/mp4', '.mov': 'video/quicktime'
        }
    
    def get_mime(self, path: Path) -> str:
        return self.mime_map.get(path.suffix.lower(), 'application/octet-stream')
    
    def to_base64(self, path: Path) -> str:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def validate_file_size(self, path: Path) -> bool:
        """Проверяет размер файла"""
        try:
            size = path.stat().st_size
            mime = self.get_mime(path)
            
            if mime.startswith('image/'):
                if size > self.max_image_size:
                    self.logger.error(f"Изображение {path.name} слишком большое: {size/1024/1024:.1f} MB > {self.max_image_size/1024/1024} MB")
                    return False
            else:
                if size > self.max_file_size:
                    self.logger.error(f"Файл {path.name} слишком большой: {size/1024/1024:.1f} MB > {self.max_file_size/1024/1024} MB")
                    return False
            
            self.logger.debug(f"Размер файла {path.name}: {size/1024:.1f} KB")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка проверки размера файла {path.name}: {e}")
            return False
    
    def save_image(self, data: str, model: str, idx: int = 0) -> Optional[Path]:
        timestamp = int(time.time())
        filename = f"{model}_{timestamp}_{idx}.png"
        filepath = self.images_dir / filename
        
        try:
            if data.startswith(('http://', 'https://')):
                r = requests.get(data, timeout=60, stream=True)
                r.raise_for_status()
                
                # Проверяем размер перед сохранением
                content_length = r.headers.get('content-length')
                if content_length and int(content_length) > self.max_image_size:
                    self.logger.error(f"Изображение по URL слишком большое: {int(content_length)/1024/1024:.1f} MB")
                    return None
                
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                self.logger.success(f"Изображение сохранено: {filepath}")
            else:
                if ',' in data:
                    data = data.split(',', 1)[1]
                data = re.sub(r'\s+', '', data)
                
                # Проверяем размер base64
                approx_size = len(data) * 3 / 4  # приблизительный размер в байтах
                if approx_size > self.max_image_size:
                    self.logger.error(f"Изображение в base64 слишком большое: {approx_size/1024/1024:.1f} MB")
                    return None
                
                content = base64.b64decode(data)
                with open(filepath, 'wb') as f:
                    f.write(content)
                self.logger.success(f"Изображение сохранено: {filepath}")
            
            return filepath
        except Exception as e:
            self.logger.error(f"Ошибка сохранения изображения: {e}")
            return None

# ==================== HTTP клиент ====================

class HTTPClient:
    """HTTP клиент с повторными попытками"""
    
    def __init__(self, logger, max_retries: int = 3):
        self.logger = logger
        self.max_retries = max_retries
    
    def post(self, url: str, headers: Dict, json_data: Dict, timeout: int) -> Dict:
        for attempt in range(self.max_retries):
            try:
                start = time.time()
                r = requests.post(url, headers=headers, json=json_data, timeout=timeout)
                elapsed = time.time() - start
                
                self.logger.debug(f"HTTP {r.status_code} за {elapsed:.2f}с")
                
                # Парсим JSON
                try:
                    result = r.json()
                except Exception as e:
                    self.logger.error(f"Ошибка парсинга JSON: {e}")
                    return {'error': f'Невалидный JSON от сервера: {r.text[:100]}'}
                
                # Успешный ответ
                if r.status_code == 200:
                    return result
                
                # Обрабатываем ошибки
                error_msg = "Unknown error"
                if isinstance(result, dict):
                    if 'error' in result:
                        if isinstance(result['error'], dict):
                            error_msg = result['error'].get('message', str(result['error']))
                        else:
                            error_msg = str(result['error'])
                    elif 'message' in result:
                        error_msg = result['message']
                
                # Rate limiting (429)
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limit exceeded. Retry after {retry_after}s")
                    
                    if attempt < self.max_retries - 1:
                        # Ждем столько, сколько сказал сервер, или по формуле
                        wait = max(retry_after, 1 * (2 ** attempt))
                        self.logger.warning(f"Ожидание {wait}с перед повтором...")
                        time.sleep(wait)
                        continue
                    else:
                        return {
                            'error': 'rate_limit',
                            'message': f'Rate limit exceeded. Try again in {retry_after}s',
                            'retry_after': retry_after,
                            'status_code': 429
                        }
                
                # Если это серверная ошибка (5xx) и есть попытки, повторяем
                if r.status_code >= 500 and attempt < self.max_retries - 1:
                    wait = 1 * (2 ** attempt)
                    self.logger.warning(f"Ошибка сервера ({r.status_code}), повтор через {wait}с...")
                    time.sleep(wait)
                    continue
                
                # Возвращаем ошибку
                return {
                    'error': error_msg,
                    'status_code': r.status_code,
                    'raw_response': result
                }
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут (попытка {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait = 1 * (2 ** attempt)
                    time.sleep(wait)
                    continue
                return {'error': f'Таймаут после {timeout}с'}
                
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Ошибка соединения (попытка {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait = 1 * (2 ** attempt)
                    time.sleep(wait)
                    continue
                return {'error': 'Ошибка соединения'}
                
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка: {e}")
                if attempt < self.max_retries - 1:
                    wait = 1 * (2 ** attempt)
                    time.sleep(wait)
                    continue
                return {'error': str(e)}
        
        return {'error': 'Превышено количество попыток'}

# ==================== Основной клиент ====================

class RouterAIClient:
    """Клиент для RouterAI API"""
    
    def __init__(self, config_path: str, model_name: str, 
                 base_url: str = "https://routerai.ru/api/v1",
                 verbose: bool = False):
        
        self.logger = get_logger(verbose)
        self.base_url = base_url
        self.api_url = f"{self.base_url}/chat/completions"
        
        self.logger.divider()
        self.logger.info(f"Инициализация клиента для модели: {model_name}")
        
        # Загружаем конфиг
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)['models']
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфига: {e}")
            raise

        # СНАЧАЛА проверяем, есть ли модель
        if model_name not in configs:
            available = ', '.join(configs.keys())
            raise ValueError(f"Модель '{model_name}' не найдена. Доступны: {available}")

        # ПОТОМ работаем с ключами
        if 'api_key_env' in configs[model_name]:
            env_var = configs[model_name]['api_key_env']
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"Переменная окружения {env_var} не найдена в .env файле")
            configs[model_name]['api_key'] = api_key
        else:
            # Для обратной совместимости
            if 'api_key' not in configs[model_name]:
                raise ValueError(f"В конфиге модели {model_name} нет ни api_key, ни api_key_env")
        
        self.config = ModelConfig.from_dict(model_name, configs[model_name])
        self.files = FileHandler(self.logger)
        self.http = HTTPClient(self.logger)
        
        self.logger.info(f"Модель: {self.config.model_id}")
        self.logger.info(f"Вход: {', '.join(t.value for t in self.config.input_types)}")
        self.logger.info(f"Выход: {', '.join(t.value for t in self.config.output_types)}")
        self.logger.divider()
    
    def _validate_inputs(self, images=None, files=None, audio=None, video=None):
        """Проверяет поддержку типов данных и размер файлов"""
        # Собираем все файлы для проверки размера
        all_files = []
        if images:
            all_files.extend(images)
        if files:
            all_files.extend(files)
        if audio:
            all_files.extend(audio)
        if video:
            all_files.extend(video)
        
        # Проверяем размер каждого файла
        for file_path in all_files:
            path = Path(file_path)
            if not path.exists():
                raise ValueError(f"Файл {file_path} не найден")
            if not self.files.validate_file_size(path):
                raise ValueError(f"Файл {file_path} превышает допустимый размер")
        
        # Проверяем поддержку типов
        if images:
            for img in images:
                if InputType.IMAGE not in self.config.input_types:
                    raise ValueError(f"Модель {self.config.name} не поддерживает изображения")
            self.logger.debug(f"Изображений: {len(images)}")
        
        if files:
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in ['.pdf', '.txt', '.md', '.csv', '.json', '.doc', '.docx']:
                    if InputType.FILE not in self.config.input_types:
                        raise ValueError(f"Модель {self.config.name} не поддерживает файлы")
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    if InputType.IMAGE not in self.config.input_types:
                        raise ValueError(f"Модель {self.config.name} не поддерживает изображения")
            self.logger.debug(f"Файлов: {len(files)}")
        
        if audio:
            if InputType.AUDIO not in self.config.input_types:
                raise ValueError(f"Модель {self.config.name} не поддерживает аудио")
            self.logger.debug(f"Аудио: {len(audio)}")
        
        if video:
            if InputType.VIDEO not in self.config.input_types:
                raise ValueError(f"Модель {self.config.name} не поддерживает видео")
            self.logger.debug(f"Видео: {len(video)}")
    
    def _build_content(self, prompt, images=None, files=None, audio=None, video=None):
        """Строит content для запроса"""
        content = [{"type": "text", "text": prompt}]
        
        # Изображения
        if images:
            for img_path in images:
                path = Path(img_path)
                if not path.exists():
                    self.logger.warning(f"Файл {img_path} не найден")
                    continue
                
                self.logger.debug(f"Добавляю изображение: {path.name}")
                b64 = self.files.to_base64(path)
                mime = self.files.get_mime(path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{b64}"
                    }
                })
        
        # Файлы
        if files:
            for file_path in files:
                path = Path(file_path)
                if not path.exists():
                    self.logger.warning(f"Файл {file_path} не найден")
                    continue
                
                self.logger.debug(f"Добавляю файл: {path.name}")
                b64 = self.files.to_base64(path)
                mime = self.files.get_mime(path)
                
                # Для JSON файлов показываем содержимое и меняем MIME
                if path.suffix.lower() == '.json':
                    mime = 'text/plain'
                    self.logger.debug(f"JSON файл, принудительно устанавливаю MIME: {mime}")
                    with open(path, 'r', encoding='utf-8') as f:
                        self.logger.debug(f"Содержимое JSON (первые 100): {f.read()[:100]}")
                
                if mime.startswith('image/'):
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}"
                        }
                    })
                else:
                    content.append({
                        "type": "file",
                        "file": {
                            "filename": path.name,
                            "file_data": f"data:{mime};base64,{b64}"
                        }
                    })
        
        # Аудио
        if audio:
            for audio_path in audio:
                path = Path(audio_path)
                if not path.exists():
                    continue
                
                self.logger.debug(f"Добавляю аудио: {path.name}")
                b64 = self.files.to_base64(path)
                mime = self.files.get_mime(path)
                content.append({
                    "type": "input_audio",
                    "input_audio": {
                        "data": f"data:{mime};base64,{b64}",
                        "format": path.suffix[1:]
                    }
                })
        
        # Видео
        if video:
            for video_path in video:
                path = Path(video_path)
                if not path.exists():
                    continue
                
                self.logger.debug(f"Добавляю видео: {path.name}")
                b64 = self.files.to_base64(path)
                mime = self.files.get_mime(path)
                content.append({
                    "type": "file",
                    "file": {
                        "filename": path.name,
                        "file_data": f"data:{mime};base64,{b64}"
                    }
                })
        
        return content
    
    def chat(self,
            prompt: str,
            images: Optional[List[str]] = None,
            files: Optional[List[str]] = None,
            audio: Optional[List[str]] = None,
            video: Optional[List[str]] = None,
            web_search: bool = False,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            pdf_engine: str = "pdf-text",
            **kwargs) -> Dict:
        """Основной метод для всех типов запросов"""
        
        self.logger.info(f"Запрос: {prompt[:100]}..." if len(prompt) > 100 else f"Запрос: {prompt}")
        
        # Валидация
        try:
            self._validate_inputs(
                images=images,
                files=files,
                audio=audio,
                video=video
            )
        except ValueError as e:
            self.logger.error(str(e))
            return {'success': False, 'error': str(e)}
        
        if web_search:
            self.logger.debug("Включен веб-поиск")
        
        # Собираем контент
        content = self._build_content(
            prompt=prompt,
            images=images,
            files=files,
            audio=audio,
            video=video
        )
        
        messages = [{"role": "user", "content": content}]
        
        # Базовый запрос
        request = {
            "model": self.config.model_id,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        # Extra body из конфига
        if self.config.extra_body:
            request["extra_body"] = self.config.extra_body
            self.logger.debug(f"Extra body: {json.dumps(self.config.extra_body)}")
        
        # Плагины
        plugins = []
        if web_search:
            plugins.append({"id": "web"})
        
        if files:
            has_pdf = any(Path(f).suffix.lower() == '.pdf' for f in files)
            if has_pdf:
                plugins.append({
                    "id": "file-parser",
                    "pdf": {"engine": pdf_engine}
                })
                self.logger.debug(f"PDF движок: {pdf_engine}")
        
        if plugins:
            request["plugins"] = plugins
            self.logger.debug(f"Плагины: {json.dumps(plugins)}")
        
        # Для генерации изображений
        if OutputType.IMAGE in self.config.output_types and self.config.size:
            request["size"] = self.config.size
            self.logger.debug(f"Размер изображения: {self.config.size}")
        
        # Дополнительные параметры
        request.update(kwargs)
        
        # Отправляем запрос
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        start = time.time()
        result = self.http.post(self.api_url, headers, request, self.config.timeout)
        elapsed = time.time() - start
        
        self.logger.debug(f"Полное время запроса: {elapsed:.2f}с")
        
        # Ошибка
        if 'error' in result:
            self.logger.error(f"Ошибка API: {result['error']}")
            return {'success': False, 'error': result['error']}
        
        # Пустой ответ
        if not result.get('choices'):
            self.logger.error("Нет ответа от модели")
            return {'success': False, 'error': 'Нет ответа от модели'}
        
        # Парсим ответ
        choice = result['choices'][0]
        message = choice.get('message', {})
        
        response = {
            'success': True,
            'usage': result.get('usage', {}),
            'model': result.get('model', self.config.model_id)
        }
        
        # Текст
        if OutputType.TEXT in self.config.output_types:
            if content := message.get('content'):
                response['text'] = content
                # Показываем превью ответа
                preview = content[:300] + "..." if len(content) > 300 else content
                preview = preview.replace('\n', '↵ ').replace('\r', '')
                self.logger.debug(f"📝 Ответ: {preview}")
            else:
                self.logger.warning("Нет текста в ответе")
        
        # Изображения
        if OutputType.IMAGE in self.config.output_types and message.get('images'):
            saved = []
            self.logger.info(f"Получено изображений: {len(message['images'])}")
            for i, img in enumerate(message['images']):
                if url := img.get('image_url', {}).get('url'):
                    if path := self.files.save_image(url, self.config.name, i):
                        saved.append({
                            'path': str(path),
                            'index': i,
                            'revised_prompt': img.get('revised_prompt')
                        })
            if saved:
                response['images'] = saved
                self.logger.success(f"Сохранено изображений: {len(saved)}")
        
        # Аннотации
        if annotations := message.get('annotations'):
            response['annotations'] = annotations
            self.logger.debug(f"Получены аннотации для {len(annotations)} файлов")
        
        # Использование токенов
        if response['usage']:
            usage = response['usage']
            self.logger.debug(f"Токены: {usage.get('prompt_tokens', 0)} входа, {usage.get('completion_tokens', 0)} выхода")
        
        self.logger.success("Запрос выполнен успешно")
        return response
