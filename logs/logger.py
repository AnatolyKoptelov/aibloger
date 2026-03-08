"""
Модуль логирования для API клиента
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class Logger:
    """Простой логгер с цветами"""
    
    COLORS = {
        'info': '\033[92m',      # зеленый
        'warning': '\033[93m',   # желтый
        'error': '\033[91m',     # красный
        'debug': '\033[94m',     # синий
        'reset': '\033[0m'       # сброс
    }
    
    def __init__(self, name: str = "api", verbose: bool = False, log_file: bool = True):
        self.name = name
        self.verbose = verbose
        
        # Создаем папку для логов если нужно
        if log_file:
            self.log_dir = Path(__file__).parent
            self.log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m')}.log"
            self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Создает папку для логов если её нет"""
        self.log_dir.mkdir(exist_ok=True)
    
    def _write_to_file(self, level: str, msg: str):
        """Записывает в файл"""
        if hasattr(self, 'log_file'):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {level}: {msg}\n")
    
    def _color(self, text: str, color: str) -> str:
        """Добавляет цвет если вывод в терминал"""
        if sys.stdout.isatty():
            return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
        return text
    
    def info(self, msg: str):
        print(self._color(f"ℹ️ {msg}", 'info'))
        self._write_to_file('INFO', msg)
    
    def success(self, msg: str):
        print(self._color(f"✅ {msg}", 'info'))
        self._write_to_file('SUCCESS', msg)
    
    def warning(self, msg: str):
        print(self._color(f"⚠️ {msg}", 'warning'))
        self._write_to_file('WARNING', msg)
    
    def error(self, msg: str):
        print(self._color(f"❌ {msg}", 'error'), file=sys.stderr)
        self._write_to_file('ERROR', msg)
    
    def debug(self, msg: str):
        if self.verbose:
            print(self._color(f"🔍 {msg}", 'debug'))
        self._write_to_file('DEBUG', msg)
    
    def response_preview(self, text: str, max_len: int = 300):
        """Показывает превью ответа"""
        if not text:
            return
        
        preview = text[:max_len] + "..." if len(text) > max_len else text
        preview = preview.replace('\n', '↵ ').replace('\r', '')
        
        print(self._color(f"\n📝 Ответ: {preview}", 'debug'))
        self._write_to_file('RESPONSE', preview)
    
    def divider(self):
        print(self._color("-" * 60, 'debug'))

# Синглтон для удобства
_default_logger: Optional[Logger] = None

def get_logger(verbose: bool = False) -> Logger:
    """Возвращает или создает логгер"""
    global _default_logger
    if _default_logger is None:
        _default_logger = Logger(verbose=verbose)
    return _default_logger
