# Docker Healthcheck Troubleshooting

## Проблема

При запуске `docker-compose.vector.yml` healthcheck может не работать для контейнеров Qdrant и Infinity.

## Причина

Официальные образы `qdrant/qdrant:latest` и `michaelf34/infinity:latest` не включают утилиту `curl`, которая часто используется для проверки HTTP эндпоинтов.

## Решения

### ✅ Решение 1: Использовать wget (рекомендуется)

Обновленный `docker-compose.vector.yml` теперь использует `wget` вместо `curl`:

```yaml
# Для Qdrant
healthcheck:
  test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:6333/ || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 20s

# Для Infinity
healthcheck:
  test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7997/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 90s  # Загрузка модели занимает время
```

### ✅ Решение 2: Использовать TCP проверку через bash

Если wget также недоступен, можно использовать встроенные возможности bash:

```yaml
# Для Qdrant
healthcheck:
  test: ["CMD-SHELL", "timeout 2 bash -c '</dev/tcp/localhost/6333' || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 20s

# Для Infinity
healthcheck:
  test: ["CMD-SHELL", "timeout 2 bash -c '</dev/tcp/localhost/7997' || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 90s
```

**Примечание:** Этот метод проверяет только открыт ли порт, но не проверяет HTTP ответ.

### ✅ Решение 3: Отключить healthcheck

Самое простое решение - отключить healthcheck и использовать `service_started` вместо `service_healthy`:

```yaml
services:
  qdrant:
    # ... остальная конфигурация ...
    # healthcheck закомментирован или удален

  infinity:
    # ... остальная конфигурация ...
    # healthcheck закомментирован или удален

  mcp-hub:
    depends_on:
      qdrant:
        condition: service_started  # вместо service_healthy
      infinity:
        condition: service_started  # вместо service_healthy
```

**Недостаток:** Сервисы запустятся сразу после старта контейнера, не дожидаясь полной готовности. Может потребоваться дополнительная логика retry в приложении.

### ✅ Решение 4: Установить curl в custom образ

Создать свой Dockerfile для Qdrant/Infinity с установленным curl:

```dockerfile
# Dockerfile.qdrant-healthcheck
FROM qdrant/qdrant:latest

USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER qdrant
```

Затем использовать этот образ в docker-compose:

```yaml
qdrant:
  build:
    context: .
    dockerfile: Dockerfile.qdrant-healthcheck
  # ... остальная конфигурация ...
```

**Недостаток:** Увеличивает размер образа и время сборки.

## Текущее состояние

В текущей версии `docker-compose.vector.yml`:
- ✅ **Qdrant**: использует `wget` для healthcheck
- ✅ **Infinity**: использует `wget` для healthcheck  
- ✅ **MCP Hub**: использует `curl` (установлен в Dockerfile.hub)
- ✅ **Bot**: не требует сетевого healthcheck (использует Python check)

## Проверка работы healthcheck

```bash
# Проверить статус всех контейнеров
docker-compose -f docker-compose.vector.yml ps

# Проверить логи healthcheck конкретного контейнера
docker inspect tg-note-qdrant --format='{{json .State.Health}}' | jq

# Проверить доступность вручную
docker exec tg-note-qdrant wget --spider http://localhost:6333/
docker exec tg-note-infinity wget --spider http://localhost:7997/health
```

## Полезные команды для отладки

```bash
# Запустить bash в контейнере для проверки доступных утилит
docker exec -it tg-note-qdrant sh
# Проверить наличие curl/wget
which curl
which wget
which bash

# Проверить порты изнутри контейнера
netstat -tulpn | grep LISTEN
ss -tulpn | grep LISTEN

# Проверить HTTP эндпоинт вручную
wget -O- http://localhost:6333/
curl http://localhost:6333/
```

## Рекомендации

1. **Для production:** Используйте Решение 1 (wget) или Решение 2 (TCP check)
2. **Для разработки:** Можно использовать Решение 3 (отключить healthcheck)
3. **Увеличьте `start_period`** для Infinity до 90-120 секунд при первом запуске (загрузка модели)
4. **Мониторьте логи** при первом запуске: `docker-compose logs -f qdrant infinity`

## Дополнительные параметры healthcheck

```yaml
healthcheck:
  interval: 30s        # Как часто проверять
  timeout: 10s         # Максимальное время ожидания ответа
  retries: 5           # Сколько раз повторить при ошибке
  start_period: 60s    # Время на инициализацию (не считаются failures)
```

Для медленных систем или больших моделей увеличьте эти значения.
