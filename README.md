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

После старта PostgreSQL примените миграцию внутри backend-контейнера:

```bash
docker compose -f docker-compose.local.yml exec backend alembic upgrade head
```

API доступен по `http://127.0.0.1:8088/docs`.

Проверка unit-тестов:

```bash
poetry run pytest
```

## Веб-фронт и разговор с агентом

После запуска Docker откройте `http://127.0.0.1:3000`. Кнопка «Начать
разговор» использует распознавание речи браузера (Chrome/Edge) и озвучивает
ответ через Web Speech API. Поле текста остаётся запасным вариантом. Агент
проверяет моковое меню, спрашивает точку, доставку или самовывоз, адрес при
доставке и после подтверждения создаёт заказ. Справа отображается список
заказов.

После первого запуска примените миграции (они также добавляют демо-меню):

```bash
docker compose -f docker-compose.local.yml exec backend alembic upgrade head
```

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
