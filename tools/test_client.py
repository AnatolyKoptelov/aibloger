#!/usr/bin/env python3
"""
Тестирование API клиента для всех моделей и типов запросов
"""

import sys
import json
import time
from pathlib import Path

# Добавляем shared в путь
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.api_client import RouterAIClient

# ==================== Тестовые данные ====================

TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DATA_DIR.mkdir(exist_ok=True)

# Создаем тестовые файлы если их нет
def create_test_files():
    """Создает тестовые файлы для проверки"""
    
    # Тестовый текст
    text_file = TEST_DATA_DIR / "test.txt"
    if not text_file.exists():
        text_file.write_text("Это тестовый текстовый файл. Он содержит простой текст для проверки работы с файлами.")
    
    # Тестовый Markdown
    md_file = TEST_DATA_DIR / "test.md"
    if not md_file.exists():
        md_file.write_text("""# Тестовый Markdown файл

## Заголовок 2
- пункт 1
- пункт 2

**жирный текст** и *курсив*
""")
    
    # Тестовый CSV
    csv_file = TEST_DATA_DIR / "test.csv"
    if not csv_file.exists():
        csv_file.write_text("""name,age,city
Иван,30,Москва
Мария,25,СПб
Петр,35,Казань
""")
    
    # Создаем простой JSON
    json_file = TEST_DATA_DIR / "test.json"
    if not json_file.exists():
        json_file.write_text(json.dumps({
            "name": "Тест",
            "items": [1, 2, 3],
            "nested": {"key": "value"}
        }, ensure_ascii=False, indent=2))
    
    # Простой PDF мы не можем создать, но можем скачать тестовый
    pdf_file = TEST_DATA_DIR / "test.pdf"
    if not pdf_file.exists():
        try:
            import urllib.request
            print("Скачиваю тестовый PDF...")
            urllib.request.urlretrieve(
                "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                pdf_file
            )
        except:
            print("Не удалось скачать PDF, тест с PDF будет пропущен")
    
    # Тестовое изображение (создаем простой PNG через PIL если есть)
    img_file = TEST_DATA_DIR / "test.png"
    if not img_file.exists():
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (200, 100), color='white')
            d = ImageDraw.Draw(img)
            d.text((10, 40), "Тестовое изображение", fill='black')
            img.save(img_file)
            print("Создано тестовое изображение")
        except ImportError:
            print("PIL не установлен, тест с изображением может не работать")

# ==================== Тесты ====================

def test_text_only(client):
    """Тест 1: Только текст"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Только текст")
    print("="*60)
    
    start = time.time()
    result = client.chat(
        prompt="Напиши короткое приветствие на русском языке, одно предложение."
    )
    elapsed = time.time() - start
    
    print(f"Время: {elapsed:.2f}с")
    print(f"Успех: {result.get('success')}")
    
    if result.get('success'):
        text = result.get('text', '')
        print(f"Ответ: {text[:500]}..." if len(text) > 500 else f"Ответ: {text}")
        print(f"Токены: {result.get('usage', {})}")
    else:
        print(f"Ошибка: {result.get('error')}")
    
    return result

def test_with_image(client):
    """Тест 2: С изображением"""
    print("\n" + "="*60)
    print("ТЕСТ 2: С изображением")
    print("="*60)
    
    img_path = TEST_DATA_DIR / "test.png"
    if not img_path.exists():
        print("Пропускаем: нет тестового изображения")
        return None
    
    start = time.time()
    result = client.chat(
        prompt="Опиши, что ты видишь на этом изображении. Если изображение не видно, просто напиши 'изображение не распознано'.",
        images=[str(img_path)]
    )
    elapsed = time.time() - start
    
    print(f"Время: {elapsed:.2f}с")
    print(f"Успех: {result.get('success')}")
    
    if result.get('success'):
        text = result.get('text', '')
        print(f"Ответ: {text[:200]}..." if len(text) > 200 else f"Ответ: {text}")
        print(f"Токены: {result.get('usage', {})}")
    else:
        print(f"Ошибка: {result.get('error')}")
    
    return result

def test_with_text_file(client, file_type="txt"):
    """Тест 3: С текстовым файлом"""
    print("\n" + "="*60)
    print(f"ТЕСТ 3: С {file_type.upper()} файлом")
    print("="*60)
    
    file_map = {
        "txt": TEST_DATA_DIR / "test.txt",
        "md": TEST_DATA_DIR / "test.md",
        "csv": TEST_DATA_DIR / "test.csv",
        "json": TEST_DATA_DIR / "test.json",
        "pdf": TEST_DATA_DIR / "test.pdf"
    }
    
    file_path = file_map.get(file_type)
    if not file_path or not file_path.exists():
        print(f"Пропускаем: нет тестового {file_type} файла")
        return None
    
    start = time.time()
    result = client.chat(
        prompt=f"Прочитай этот {file_type.upper()} файл и кратко опиши его содержимое.",
        files=[str(file_path)]
    )
    elapsed = time.time() - start
    
    print(f"Время: {elapsed:.2f}с")
    print(f"Успех: {result.get('success')}")
    
    if result.get('success'):
        text = result.get('text', '')
        print(f"Ответ: {text[:200]}..." if len(text) > 200 else f"Ответ: {text}")
        print(f"Токены: {result.get('usage', {})}")
    else:
        print(f"Ошибка: {result.get('error')}")
    
    return result

def test_image_generation(client):
    """Тест 4: Генерация изображения"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Генерация изображения")
    print("="*60)
    
    start = time.time()
    result = client.chat(
        prompt="Нарисуй простой цветок, схематично, черно-белый."
    )
    elapsed = time.time() - start
    
    print(f"Время: {elapsed:.2f}с")
    print(f"Успех: {result.get('success')}")
    
    if result.get('success'):
        if result.get('images'):
            print(f"Сгенерировано изображений: {len(result['images'])}")
            for img in result['images']:
                print(f"  - {img['path']}")
        else:
            print("Нет изображений в ответе")
    else:
        print(f"Ошибка: {result.get('error')}")
    
    return result

def test_web_search(client):
    """Тест 5: Веб-поиск"""
    print("\n" + "="*60)
    print("ТЕСТ 5: Веб-поиск")
    print("="*60)
    
    start = time.time()
    result = client.chat(
        prompt="Какой сегодня праздник? Найди информацию в интернете.",
        web_search=True
    )
    elapsed = time.time() - start
    
    print(f"Время: {elapsed:.2f}с")
    print(f"Успех: {result.get('success')}")
    
    if result.get('success'):
        text = result.get('text', '')
        print(f"Ответ: {text[:200]}..." if len(text) > 200 else f"Ответ: {text}")
        print(f"Токены: {result.get('usage', {})}")
    else:
        print(f"Ошибка: {result.get('error')}")
    
    return result

def test_mixed_input(client):
    """Тест 6: Смешанный ввод (текст + файл)"""
    print("\n" + "="*60)
    print("ТЕСТ 6: Смешанный ввод (текст + файл)")
    print("="*60)
    
    txt_file = TEST_DATA_DIR / "test.txt"
    if not txt_file.exists():
        print("Пропускаем: нет тестового txt файла")
        return None
    
    start = time.time()
    result = client.chat(
        prompt="У меня есть текстовый файл. Прочитай его и ответь: сколько в нем строк?",
        files=[str(txt_file)]
    )
    elapsed = time.time() - start
    
    print(f"Время: {elapsed:.2f}с")
    print(f"Успех: {result.get('success')}")
    
    if result.get('success'):
        text = result.get('text', '')
        print(f"Ответ: {text[:200]}..." if len(text) > 200 else f"Ответ: {text}")
        print(f"Токены: {result.get('usage', {})}")
    else:
        print(f"Ошибка: {result.get('error')}")
    
    return result

# ==================== Запуск тестов ====================

def test_model(model_name, config_path="config/models.json"):
    """Тестирует конкретную модель"""
    print(f"\n{'#'*60}")
    print(f"ТЕСТИРОВАНИЕ МОДЕЛИ: {model_name}")
    print(f"{'#'*60}")
    
    try:
        client = RouterAIClient(config_path, model_name, verbose=True)
    except Exception as e:
        print(f"ОШИБКА: Не удалось создать клиент для {model_name}: {e}")
        return
    
    # Определяем какие тесты запускать на основе возможностей модели
    tests = []
    
    # Текст есть у всех
    tests.append(("Текст", test_text_only))
    
    # Изображения на входе
    if "image" in [t.value for t in client.config.input_types]:
        tests.append(("С изображением", test_with_image))
    
    # Файлы на входе
    if "file" in [t.value for t in client.config.input_types]:
        tests.append(("С TXT файлом", lambda c: test_with_text_file(c, "txt")))
        tests.append(("С JSON файлом", lambda c: test_with_text_file(c, "json")))
        # PDF тест только если есть
        if (TEST_DATA_DIR / "test.pdf").exists():
            tests.append(("С PDF файлом", lambda c: test_with_text_file(c, "pdf")))
    
    # Генерация изображений
    if "image" in [t.value for t in client.config.output_types]:
        tests.append(("Генерация изображения", test_image_generation))
    
    # Веб-поиск (по флагу)
    tests.append(("Веб-поиск", test_web_search))
    
    # Смешанный ввод (если есть поддержка файлов)
    if "file" in [t.value for t in client.config.input_types]:
        tests.append(("Смешанный ввод", test_mixed_input))
    
    # Запускаем тесты
    results = {}
    for test_name, test_func in tests:
        print(f"\n--- Тест: {test_name} ---")
        try:
            result = test_func(client)
            results[test_name] = result.get('success', False) if result else "Пропущен"
        except Exception as e:
            print(f"Ошибка при выполнении теста: {e}")
            results[test_name] = False
    
    # Итоги
    print("\n" + "="*60)
    print(f"ИТОГИ ТЕСТИРОВАНИЯ {model_name}")
    print("="*60)
    for test_name, status in results.items():
        status_str = "✅" if status is True else "❌" if status is False else "⏭️"
        print(f"{status_str} {test_name}")

def test_all_models(config_path="config/models.json"):
    """Тестирует все модели из конфига"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    models = config.get('models', {}).keys()
    
    print("="*60)
    print("ТЕСТИРОВАНИЕ ВСЕХ МОДЕЛЕЙ")
    print("="*60)
    
    for model_name in models:
        test_model(model_name, config_path)
        print("\n" + "="*60)

# ==================== Точка входа ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование API клиента")
    parser.add_argument('--config', default='config/models.json',
                       help='Путь к конфигу с моделями')
    parser.add_argument('--model', help='Конкретная модель для тестирования')
    parser.add_argument('--create-files', action='store_true',
                       help='Создать тестовые файлы')
    
    args = parser.parse_args()
    
    if args.create_files:
        create_test_files()
        print("Тестовые файлы созданы")
        return
    
    if args.model:
        test_model(args.model, args.config)
    else:
        test_all_models(args.config)

if __name__ == '__main__':
    main()
