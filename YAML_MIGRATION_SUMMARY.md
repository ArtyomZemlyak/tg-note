# YAML Configuration Migration Summary

## Выполнено ✅

Добавлена поддержка YAML файла конфигурации с правильным порядком приоритета загрузки настроек.

## Изменения

### 1. Новые зависимости
- Добавлен `PyYAML==6.0.1` в `requirements.txt`

### 2. Обновлен `config/settings.py`
- Добавлена поддержка `YamlConfigSettingsSource` из pydantic-settings
- Реализован кастомный `CliSettingsSource` (заглушка для будущей реализации CLI)
- Настроен порядок приоритета источников конфигурации

### 3. Новые файлы
- `config.yaml` - базовая конфигурация (не хранить в Git)
- `config.example.yaml` - пример конфигурации (для Git)
- `YAML_CONFIGURATION.md` - подробная документация
- `YAML_MIGRATION_SUMMARY.md` - этот файл

### 4. Обновлена документация
- `PYDANTIC_SETTINGS_MIGRATION.md` - добавлена секция о YAML
- `QUICK_START.md` - обновлена секция настройки
- `.gitignore` - добавлен `config.yaml`

## Порядок загрузки (приоритет)

```
ENV > CLI > .env > YAML > defaults
```

1. **Environment Variables** - наивысший приоритет
2. **CLI arguments** - будет реализовано позже
3. **.env file** - для credentials
4. **config.yaml** - базовая конфигурация
5. **Default values** - значения по умолчанию

## Что хранить где

### config.yaml (НЕ чувствительные данные)
```yaml
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main
MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: ./data/processed.json
LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log
ALLOWED_USER_IDS: ""
```

### .env (ТОЛЬКО credentials)
```bash
TELEGRAM_BOT_TOKEN=your_token_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Environment Variables (переопределение)
```bash
export LOG_LEVEL=DEBUG
export MESSAGE_GROUP_TIMEOUT=60
```

## Тестирование

### ✅ Все тесты пройдены

#### 1. Базовая загрузка YAML
```bash
✓ YAML файл загружается корректно
✓ Все поля парсятся правильно
✓ Типы данных сохраняются (Path, int, bool, str)
```

#### 2. Приоритет источников
```bash
✓ ENV переопределяет .env и YAML
✓ .env переопределяет YAML
✓ YAML используется когда нет переопределения
✓ Приоритет работает для всех типов полей
```

#### 3. Обратная совместимость
```bash
✓ Все существующие тесты проходят (13/13)
✓ Старый код работает без изменений
✓ .env файл работает как раньше
✓ ENV переменные работают как раньше
```

## Примеры использования

### Пример 1: Только YAML
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

```bash
$ python main.py
# MESSAGE_GROUP_TIMEOUT=30, LOG_LEVEL=INFO
```

### Пример 2: YAML + .env
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

```bash
# .env
MESSAGE_GROUP_TIMEOUT=60
TELEGRAM_BOT_TOKEN=secret
```

```bash
$ python main.py
# MESSAGE_GROUP_TIMEOUT=60 (from .env)
# LOG_LEVEL=INFO (from YAML)
# TELEGRAM_BOT_TOKEN=secret (from .env)
```

### Пример 3: YAML + .env + ENV
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

```bash
# .env
MESSAGE_GROUP_TIMEOUT=60
LOG_LEVEL=WARNING
```

```bash
$ LOG_LEVEL=DEBUG python main.py
# MESSAGE_GROUP_TIMEOUT=60 (from .env, ENV не установлен)
# LOG_LEVEL=DEBUG (from ENV, переопределяет все)
```

## Техническая реализация

### Как это работает

1. **Pydantic-settings** читает конфигурацию из нескольких источников
2. **Порядок важен**: первый источник, который находит значение, побеждает
3. **YamlConfigSettingsSource** - встроенный класс pydantic-settings для YAML
4. **settings_customise_sources** - метод определяет порядок приоритета

```python
@classmethod
def settings_customise_sources(cls, ...):
    yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
    cli_settings = CliSettingsSource(settings_cls)
    
    # Возвращаем источники слева направо (левый = высший приоритет)
    return (
        env_settings,       # Highest priority - check first
        cli_settings,       # Check second
        dotenv_settings,    # Check third
        yaml_settings,      # Lowest priority - check last
    )
```

## Migration Path

### Для существующих пользователей
1. Ничего не меняйте - все работает как раньше
2. Опционально создайте `config.yaml` для удобства

### Для новых пользователей
1. Скопируйте `config.example.yaml` → `config.yaml`
2. Создайте `.env` с credentials
3. Запустите приложение

## Преимущества

✅ **Разделение concerns**: credentials отдельно от конфигурации  
✅ **Гибкость**: легко переопределить любую настройку  
✅ **Читаемость**: YAML более читаем чем .env для сложных структур  
✅ **CI/CD friendly**: легко переопределить через ENV  
✅ **Безопасность**: credentials не в config.yaml  
✅ **Обратная совместимость**: старый код работает без изменений  

## Команды для проверки

```bash
# Проверить загрузку настроек
python3 -c "from config.settings import settings; print(repr(settings))"

# Проверить приоритет
MESSAGE_GROUP_TIMEOUT=999 python3 -c "from config.settings import settings; print(f'Timeout: {settings.MESSAGE_GROUP_TIMEOUT}')"

# Запустить тесты
pytest tests/ -v

# Проверить линтер
python3 -c "from config.settings import settings"  # No errors = ✓
```

## Следующие шаги (опционально)

- [ ] Реализовать CLI аргументы (argparse/click)
- [ ] Добавить поддержку нескольких YAML файлов (dev.yaml, prod.yaml)
- [ ] Добавить JSON Schema для валидации config.yaml
- [ ] Добавить автоматическую генерацию config.example.yaml из модели

## Заключение

Миграция завершена успешно! Приложение теперь поддерживает гибкую конфигурацию из нескольких источников с правильным порядком приоритета.

**Все тесты пройдены** ✅  
**Обратная совместимость сохранена** ✅  
**Документация обновлена** ✅  
