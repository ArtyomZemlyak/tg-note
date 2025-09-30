#!/usr/bin/env python3
"""
Verification script for Phase 1 implementation
Checks that all required files and directories exist
"""

import os
import sys
from pathlib import Path


def check_file(path: str) -> bool:
    """Check if file exists"""
    exists = Path(path).exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {path}")
    return exists


def check_dir(path: str) -> bool:
    """Check if directory exists"""
    exists = Path(path).is_dir()
    status = "✓" if exists else "✗"
    print(f"  {status} {path}/")
    return exists


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         Phase 1: Структура проекта - Верификация            ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    
    all_ok = True
    
    # Check directories
    print("📁 Проверка директорий:")
    dirs = [
        "config",
        "src",
        "src/bot",
        "src/processor",
        "src/agents",
        "src/knowledge_base",
        "src/tracker",
        "tests",
        "data",
        "logs"
    ]
    
    for d in dirs:
        if not check_dir(d):
            all_ok = False
    
    # Check core files
    print("\n📄 Проверка основных файлов:")
    files = [
        "main.py",
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "pytest.ini",
        "README.md",
        "PHASE1_IMPLEMENTATION.md",
        "QUICK_START.md"
    ]
    
    for f in files:
        if not check_file(f):
            all_ok = False
    
    # Check config files
    print("\n⚙️  Проверка config/:")
    config_files = [
        "config/__init__.py",
        "config/settings.py"
    ]
    
    for f in config_files:
        if not check_file(f):
            all_ok = False
    
    # Check source modules
    print("\n🐍 Проверка src/ модулей:")
    src_files = [
        "src/__init__.py",
        "src/bot/__init__.py",
        "src/bot/handlers.py",
        "src/bot/utils.py",
        "src/processor/__init__.py",
        "src/processor/message_aggregator.py",
        "src/processor/content_parser.py",
        "src/agents/__init__.py",
        "src/agents/base_agent.py",
        "src/agents/stub_agent.py",
        "src/knowledge_base/__init__.py",
        "src/knowledge_base/manager.py",
        "src/knowledge_base/git_ops.py",
        "src/tracker/__init__.py",
        "src/tracker/processing_tracker.py"
    ]
    
    for f in src_files:
        if not check_file(f):
            all_ok = False
    
    # Check tests
    print("\n🧪 Проверка tests/:")
    test_files = [
        "tests/__init__.py",
        "tests/test_tracker.py",
        "tests/test_content_parser.py",
        "tests/test_stub_agent.py"
    ]
    
    for f in test_files:
        if not check_file(f):
            all_ok = False
    
    # Statistics
    print("\n" + "="*60)
    print("\n📊 Статистика:")
    
    py_files = list(Path(".").rglob("*.py"))
    py_files = [f for f in py_files if not any(
        p in str(f) for p in [".git", "venv", "__pycache__"]
    )]
    print(f"  • Python файлов: {len(py_files)}")
    
    total_lines = 0
    for f in py_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                total_lines += len(file.readlines())
        except:
            pass
    
    print(f"  • Строк кода: {total_lines}")
    print(f"  • Директорий: {len(dirs)}")
    print(f"  • Тестов: {len(test_files)}")
    
    # Summary
    print("\n" + "="*60)
    if all_ok:
        print("\n✅ Все проверки пройдены успешно!")
        print("✅ Phase 1: Базовая инфраструктура - ЗАВЕРШЕНА")
        print("\n📝 Следующие шаги:")
        print("  1. Установите зависимости: pip install -r requirements.txt")
        print("  2. Настройте .env файл: cp .env.example .env")
        print("  3. Запустите тесты: pytest")
        print("  4. Читайте QUICK_START.md для деталей\n")
        return 0
    else:
        print("\n❌ Некоторые файлы отсутствуют!")
        print("❌ Проверьте список выше\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())