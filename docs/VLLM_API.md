# API локального vLLM

Документ описывает сервер, запущенный локально:

```text
vLLM 0.27.1
модель: Qwen/Qwen3-8B-AWQ
адрес: http://127.0.0.1:8000
```

Он составлен по фактической OpenAPI-спецификации работающего сервера: `GET /openapi.json`.
Интерактивная версия документации доступна в браузере по `http://127.0.0.1:8000/docs`.

## Общие правила

- Все тела запросов — JSON с заголовком `Content-Type: application/json`.
- Для всех генеративных запросов явно передавайте `model: "Qwen/Qwen3-8B-AWQ"`.
- Сервер слушает только `127.0.0.1`; извне сети он недоступен.
- API-ключ не задан. Если позднее сервер будет доступен из сети, перезапустите vLLM с `--api-key` и передавайте `Authorization: Bearer <key>`.
- Для голосового менеджера основной маршрут — `POST /v1/chat/completions`.
- `temperature: 0` делает ответы наиболее воспроизводимыми. Для заказа также задавайте ограничение `max_tokens`.

Общие параметры генерации, поддерживаемые основными OpenAI-совместимыми методами:

| Параметр | Назначение |
| --- | --- |
| `temperature` | Случайность ответа. Для tool calls и извлечения заказа: `0`. |
| `top_p`, `top_k`, `min_p` | Альтернативные способы ограничить выбор токенов. Обычно не нужны вместе с `temperature: 0`. |
| `max_tokens` / `max_completion_tokens` | Максимальное число токенов ответа. |
| `stream` | `true` — вернуть Server-Sent Events, `false` — один JSON-ответ. |
| `stop` | Строка либо массив строк, на которых генерация завершается. |
| `seed` | Seed для воспроизводимости. |
| `response_format` | Требуемый формат ответа: текст, JSON object или JSON schema. |
| `tools`, `tool_choice` | Описание функций, которые модель может вызвать. |
| `request_id` | Идентификатор запроса для логирования и трассировки. |

## Быстрый старт: чат

### `POST /v1/chat/completions`

Основной OpenAI-совместимый чат. Обязателен только `messages`; `model` можно опустить, когда на сервере одна модель, но в приложении его лучше указывать всегда.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-8B-AWQ",
    "temperature": 0,
    "max_tokens": 120,
    "messages": [
      {
        "role": "system",
        "content": "Ты менеджер пиццерии. Отвечай кратко и по-русски."
      },
      {
        "role": "user",
        "content": "Хочу две пепперони"
      }
    ]
  }'
```

Важные поля ответа:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

#### Streaming

Добавьте `"stream": true`. Ответ будет потоком SSE: каждая строка `data: {...}` содержит очередную дельту, финальная строка — `data: [DONE]`.

```bash
curl --no-buffer http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-8B-AWQ",
    "stream": true,
    "temperature": 0,
    "messages": [{"role": "user", "content": "Назови три напитка"}]
  }'
```

#### Structured JSON для заказа

Используйте это для извлечения намерения, но всегда валидируйте JSON в Pydantic и проверяйте данные меню в Python.

```json
{
  "model": "Qwen/Qwen3-8B-AWQ",
  "temperature": 0,
  "messages": [
    {"role": "system", "content": "Верни только JSON заказа."},
    {"role": "user", "content": "Две пепперони и колу"}
  ],
  "response_format": {"type": "json_object"}
}
```

Поддерживаются также `tools`, `tool_choice`, `logprobs`, `top_logprobs`, `frequency_penalty`, `presence_penalty`, `n`, `stop_token_ids`, `ignore_eos`, `min_tokens`, `repetition_penalty`, `documents`, `chat_template` и vLLM-специфичные параметры из OpenAPI.

### `POST /v1/chat/completions/batch`

Пакетный вариант чата. Поле `messages` — массив независимых разговоров; каждый разговор — массив сообщений в формате обычного chat completion. Полезно для офлайн-оценок, не для одного голосового диалога.

```json
{
  "model": "Qwen/Qwen3-8B-AWQ",
  "temperature": 0,
  "messages": [
    [{"role": "user", "content": "Привет"}],
    [{"role": "user", "content": "Какие есть напитки?"}]
  ]
}
```

### `POST /v1/completions`

OpenAI-compatible completion для уже сформированного текстового prompt. Для Qwen-чата используйте предпочтительно `/v1/chat/completions`: он сам применяет chat template.

```bash
curl http://127.0.0.1:8000/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-8B-AWQ",
    "prompt": "Продолжи фразу: Пицца пепперони — это",
    "temperature": 0,
    "max_tokens": 50
  }'
```

Обязательных полей нет, но нужен хотя бы `prompt` или заранее заданная серверная конфигурация. `prompt` принимает строку, массив строк, token IDs либо массив token IDs.

### `POST /v1/responses`

Совместимость с OpenAI Responses API. Обязательное поле — `input`: строка или массив сообщений/элементов. Поддерживает `instructions`, `tools`, `tool_choice`, `previous_response_id`, `background`, `stream`, `max_output_tokens` и `text`.

```bash
curl http://127.0.0.1:8000/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-8B-AWQ",
    "instructions": "Отвечай одним коротким предложением.",
    "input": "Какая пицца наиболее острая?",
    "temperature": 0
  }'
```

### `GET /v1/responses/{response_id}`

Получает ранее созданный Response по его `id`.

```bash
curl http://127.0.0.1:8000/v1/responses/resp_123
```

### `POST /v1/responses/{response_id}/cancel`

Отменяет фоновый Response. Актуально только для запроса, созданного через `/v1/responses` с `"background": true`.

```bash
curl -X POST http://127.0.0.1:8000/v1/responses/resp_123/cancel
```

## Токены и шаблоны

### `POST /tokenize`

Преобразует текст или чат в IDs токенов модели.

Текстовый prompt:

```json
{
  "model": "Qwen/Qwen3-8B-AWQ",
  "prompt": "Хочу две пепперони",
  "add_special_tokens": true,
  "return_token_strs": true
}
```

Чат с применением chat template:

```json
{
  "model": "Qwen/Qwen3-8B-AWQ",
  "messages": [{"role": "user", "content": "Хочу пиццу"}],
  "add_generation_prompt": true,
  "return_token_strs": true
}
```

Ответ содержит `tokens` и, при `return_token_strs: true`, текстовые представления токенов.

### `POST /detokenize`

Преобразует token IDs обратно в текст.

```json
{
  "model": "Qwen/Qwen3-8B-AWQ",
  "tokens": [1, 2, 3]
}
```

### `POST /v1/chat/completions/render`

Не генерирует ответ. Применяет chat template и возвращает prompt/token IDs, которые были бы переданы модели. Используйте для отладки system prompt и шаблона Qwen.

Тело совпадает с `/v1/chat/completions`; полезные дополнительные поля: `return_prompt_text`, `return_token_ids`, `return_token_offsets`, `return_assistant_tokens_mask`.

### `POST /v1/completions/render`

Не генерирует ответ. Токенизирует completion prompt и возвращает подготовленное представление. Тело совпадает с `/v1/completions`.

### `POST /v1/chat/completions/derender`

Внутренний обратный адаптер vLLM: превращает результат `/inference/v1/generate` в OpenAI chat-completion ответ. Для обычного приложения не нужен.

Необходимы `model` и `generate_response`; для stream-варианта передавайте `stream: true`, `generate_chunk` и при необходимости `stream_state`.

### `POST /v1/completions/derender`

То же, что chat `derender`, но для Completion API. В non-streaming варианте обязательны `model` и `generate_responses`.

### `POST /inference/v1/generate`

Низкоуровневая генерация от уже подготовленных token IDs. Предназначена для внутренней/disaggregated архитектуры vLLM. Для него обязательны:

```json
{
  "token_ids": [1, 2, 3],
  "sampling_params": {"temperature": 0, "max_tokens": 32},
  "model": "Qwen/Qwen3-8B-AWQ"
}
```

В прикладном сервисе этот endpoint не используйте: `/v1/chat/completions` безопаснее, потому что применяет правильный шаблон чата.

## Совместимость с Anthropic

### `POST /v1/messages`

Anthropic Messages API. Обязательны `model`, `messages`, `max_tokens`.

```json
{
  "model": "Qwen/Qwen3-8B-AWQ",
  "max_tokens": 80,
  "system": "Ты менеджер пиццерии.",
  "messages": [
    {"role": "user", "content": "Хочу маргариту"}
  ],
  "temperature": 0
}
```

Также доступны `tools`, `tool_choice`, `stream`, `stop_sequences`, `top_k`, `top_p` и `cache_salt`.

### `POST /v1/messages/count_tokens`

Подсчитывает токены Anthropic-формата. Обязательны `model` и `messages`; дополнительно допустимы `system`, `tools`, `tool_choice`, `chat_template_kwargs`.

## Инфраструктура и наблюдаемость

### `GET /health`

Healthcheck. Успешный HTTP 200 означает, что API-сервер работает.

```bash
curl -i http://127.0.0.1:8000/health
```

### `GET /ping` и `POST /ping`

Ping-check, в частности для SageMaker. Оба варианта возвращают 200, если сервер доступен.

### `GET /version`

Возвращает версию vLLM.

### `GET /v1/models`

Возвращает список загруженных моделей, их ID и `max_model_len`.

```bash
curl http://127.0.0.1:8000/v1/models
```

### `GET /load`

Внутренние метрики текущей нагрузки vLLM. Полезен для собственного балансировщика, не нужен голосовому приложению на одном ПК.

### `GET /metrics`

Метрики в формате Prometheus. Их можно опрашивать Prometheus/Grafana.

```bash
curl http://127.0.0.1:8000/metrics
```

### `POST /invocations`

Совместимость с AWS SageMaker. Сервер выбирает формат обработчика на основе заголовка `Content-Type`. Для локального FastAPI-бэкенда используйте стандартные `/v1/...` маршруты.

### `POST /generative_scoring`

Внутренний endpoint для generative scoring. Не является OpenAI API и не нужен для диалогового агента.

### `POST /scale_elastic_ep`

Управление Elastic Expert Parallelism в распределённых инсталляциях. Не применимо к одному GPU.

### `POST /is_scaling_elastic_ep`

Проверяет состояние Elastic Expert Parallelism. Не применимо к одному GPU.

## Web-документация

| Маршрут | Назначение |
| --- | --- |
| `GET /docs` | Swagger UI: интерактивный запуск запросов. |
| `GET /redoc` | ReDoc: просмотр спецификации. |
| `GET /openapi.json` | Машиночитаемая OpenAPI-спецификация. |

## Коды ошибок

| Код | Значение и действие |
| --- | --- |
| `200` | Успешный ответ. |
| `400` | Некорректные параметры, неподдерживаемая функция модели или переполненный контекст. Проверьте тело запроса. |
| `404` | Не найдена модель либо `response_id`. Проверьте `model` и URL. |
| `415` | Неподдерживаемый `Content-Type` для `/invocations`. |
| `422` | JSON не соответствует схеме запроса. Сверьте обязательные поля. |
| `500` | Ошибка сервера/инференса. Проверьте лог vLLM и свободную VRAM через `nvidia-smi`. |
| `501` | Функция API существует, но не поддерживается текущей конфигурацией или моделью. |

## Рекомендация для этого проекта

В коде FastAPI вызывайте только `POST /v1/chat/completions` через `httpx` или `langchain-openai` с базовым URL `http://127.0.0.1:8000/v1`.
Остальные методы нужны для мониторинга, отладки токенов и совместимости с внешними клиентами.
