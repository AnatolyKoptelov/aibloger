#!/usr/bin/env python3
"""
CLI для RouterAI API Client
"""

import sys
import json
import argparse
from pathlib import Path

# Добавляем shared в путь
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.api_client import RouterAIClient

def main():
    parser = argparse.ArgumentParser(description='RouterAI API Client')
    
    parser.add_argument('--config', default='config/models.json',
                       help='Путь к конфигу с моделями')
    parser.add_argument('--model', required=True,
                       help='Имя модели из конфига')
    parser.add_argument('--prompt', required=True,
                       help='Текстовый промпт')
    parser.add_argument('--verbose', action='store_true',
                       help='Подробный вывод')
    
    parser.add_argument('--image', action='append', dest='images',
                       help='Изображение (можно несколько)')
    parser.add_argument('--file', action='append', dest='files',
                       help='Файл (можно несколько)')
    parser.add_argument('--audio', action='append', dest='audio',
                       help='Аудиофайл')
    parser.add_argument('--video', action='append', dest='video',
                       help='Видеофайл')
    
    parser.add_argument('--web-search', action='store_true',
                       help='Включить поиск в интернете')
    parser.add_argument('--temperature', type=float,
                       help='Температура (0-1)')
    parser.add_argument('--max-tokens', type=int,
                       help='Максимум токенов')
    parser.add_argument('--pdf-engine', default='pdf-text',
                       choices=['pdf-text', 'mistral-ocr', 'native'],
                       help='Движок для PDF')
    
    args = parser.parse_args()
    
    client = RouterAIClient(
        config_path=args.config,
        model_name=args.model,
        verbose=args.verbose
    )
    
    result = client.chat(
        prompt=args.prompt,
        images=args.images,
        files=args.files,
        audio=args.audio,
        video=args.video,
        web_search=args.web_search,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        pdf_engine=args.pdf_engine
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('success') else 1

if __name__ == '__main__':
    sys.exit(main())
