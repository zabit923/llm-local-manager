# Local voice ordering agent

Локальный backend для голосового менеджера ресторана:

```text
микрофон → Parakeet STT → Qwen/vLLM → логика заказа → Silero TTS
```

Backend хранит каталог блюд/напитков и заказы в PostgreSQL. Цена позиции
сохраняется в `OrderItem` на момент добавления в заказ и хранится в копейках
(`price_minor`), поэтому изменение цены в меню не меняет историю заказов.

## Локальный запуск

Нужны PostgreSQL 17, Redis и Python 3.12. Минимальный `.env` для Docker:

```env
FASTAPI_CFG__APP_ENV=local
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
POSTGRES_DB_TEST=postgres_test_01
POSTGRES_DB_PROD=postgres_prod_01
POSTGRES_HOST=db_postgres
REDIS_PASSWORD=local-redis-password
REDIS_PORT=6379
REDIS_HOST=redis
```

Запуск инфраструктуры и backend в Docker:

```bash
docker compose -f docker-compose.local.yml up --build
```

Backend автоматически применяет миграции при запуске.

API доступен по `http://127.0.0.1:8088/docs`.

Проверка unit-тестов:

```bash
poetry run pytest
```

## Веб-фронт и разговор с агентом

Браузер передаёт настоящий звук по WebSocket, а не распознанный текст.
Web Speech API не используется. Нужен доступ к микрофону через localhost
или HTTPS. Справа отображается список заказов, красный круг начинает и
завершает звонок. Аудиовизуализация показывает реальный сигнал микрофона
и голоса агента; громкость агента установлена на 40%.

Запустите три компонента из корня проекта в отдельных терминалах.
Если Qwen уже работает, повторно запускать его не нужно.

```bash
poetry run vllm serve Qwen/Qwen3-8B-AWQ \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.65
```

```bash
docker compose -f docker-compose.local.yml up -d --build
```

```bash
poetry run python -m src.entrypoint.voice
```

Затем откройте `http://localhost:3000`, разрешите микрофон и нажмите круг.
Первый запуск голосового сервиса скачивает модели; дождитесь сообщения
`Parakeet and Silero TTS v5_ru ready`. Его состояние доступно по
`http://localhost:8001/health`. Qwen и голосовой сервис работают на хосте,
backend и фронтенд — в Docker. Порты 8000 и 8001 предназначены для
локальной доверенной сети: не публикуйте их в интернете без защиты.

### Как проходит звонок

1. AudioWorklet переводит звук микрофона в mono PCM16LE, 16 kHz.
2. `/api/v1/pub/agent/audio` проксирует WebSocket на голосовой сервис.
3. Silero VAD на CPU определяет реплику и её конец после 750 мс тишины.
4. Parakeet-TDT-0.6B-v3 распознаёт завершённую реплику на GPU.
5. Агент получает текст, историю и каталог; Qwen предлагает действия
   и формулирует ответ. Backend проверяет позиции и сохраняет заказ.
6. Silero TTS v5_ru (голос xenia, CPU, 24 kHz) возвращает WAV.
7. После проигрывания браузер снова автоматически включает прослушивание.

После добавления позиции агент уточняет, нужно ли что-нибудь ещё.
Для самовывоза домашний адрес не нужен. При доставке запрашивается адрес.
Когда сведения собраны, заказ создаётся без дополнительного подтверждения,
а агент сообщает стоимость в рублях.

Текущая реализация — разговор по очереди, без перебивания агента.
Во время его ответа микрофон не отправляется на STT, чтобы не распознавать
собственную озвучку. Распознавание начинается после конца реплики,
а не потоково по каждому слову. Максимум реплики — около 30 секунд.
Сессии агента пока находятся в памяти backend: перезапуск сбрасывает их.

При нехватке VRAM запустите STT на CPU (будет медленнее):

```bash
VOICE_ASR_DEVICE=cpu poetry run python -m src.entrypoint.voice
```

Другие настройки: `VOICE_BACKEND_URL` (по умолчанию localhost:8088),
`VOICE_TTS_PATH` (путь к пакету v5_ru.pt), `VOICE_WS_URL` для backend
(по умолчанию ws://host.docker.internal:8001/ws). После изменений фронта
пересоберите Docker-образ, затем перезагрузите страницу.

### Протокол аудио-WebSocket

Первое сообщение — JSON `{"type":"start","session_id":"<UUID>"}`.
Далее клиент отправляет бинарные PCM16LE-пакеты. Сервер отвечает JSON:
`state` (thinking/speaking/listening/user/transcribing), `transcript`,
`reply` (ответ, корзина и order_id) или `error`.
После `state=speaking` приходит бинарный WAV. После его проигрывания
клиент отправляет `{"type":"playback_done"}` и ждёт `state=listening`.
Отключение WebSocket завершает звонок.

## API MVP

Все маршруты начинаются с `/api/v1/staff`.

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| `POST` | `/dishes/` | Создать блюдо. |
| `GET` | `/dishes/` | Получить весь каталог блюд. |
| `GET/PATCH/DELETE` | `/dishes/{dish_id}` | Прочитать, изменить или удалить блюдо. |
| `POST` | `/drinks/` | Создать напиток. |
| `GET` | `/drinks/` | Получить весь каталог напитков. |
| `GET/PATCH/DELETE` | `/drinks/{drink_id}` | Прочитать, изменить или удалить напиток. |
| `POST` | `/orders/` | Создать draft-заказ с позициями. |
| `GET` | `/orders/{order_id}` | Получить заказ и его позиции. |
| `POST` | `/orders/{order_id}/dishes/{dish_id}?quantity=2` | Добавить блюдо в draft. |
| `POST` | `/orders/{order_id}/drinks/{drink_id}?quantity=2` | Добавить напиток в draft. |
| `PATCH` | `/orders/{order_id}/items/{item_id}` | Изменить количество. |
| `DELETE` | `/orders/{order_id}/items/{item_id}` | Удалить позицию. |
| `POST` | `/orders/{order_id}/confirm` | Подтвердить заказ. |

Пример создания напитка:

```bash
curl -X POST http://127.0.0.1:8088/api/v1/staff/drinks/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Кола","volume_ml":500,"price_minor":15000}'
```

Пример заказа:

```json
{
  "branch": "Ермошкина",
  "delivery_type": "pickup",
  "items": [
    {"dish_id": "<UUID блюда>", "quantity": 2},
    {"drink_id": "<UUID напитка>", "quantity": 1}
  ]
}
```

## Голосовой прототип

Qwen запускается отдельным процессом:

```bash
poetry run vllm serve Qwen/Qwen3-8B-AWQ \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 4096 --gpu-memory-utilization 0.65
```

Локальный тест полного аудио-цикла:

```bash
poetry run python scripts/full_voice_agent.py
```

`full_voice_agent.py` загружает меню через staff API, создаёт реальный заказ,
добавляет позиции в корзину и подтверждает его. `voice_loop.py` остаётся
низкоуровневым разговорным тестом без обращения к БД.
