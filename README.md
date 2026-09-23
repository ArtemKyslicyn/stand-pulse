# Stand Pulse

Операторский клиент к MCP-инструментам живого стенда: health, рейтинг моделей, периодическая сводка.

Это не учебный echo-сервер. `probe_stand` и `model_pulse` читают те же API, по которым смотрят на стенд люди. `schedule_digest` пишет задание в SQLite на стороне сервера и сразу возвращает агрегат.

Сервер живёт в [AIChallenge](https://github.com/ArtemKyslicyn/AIChallenge) (`apps/mcp`). Этот репозиторий — публичный CLI.

## Что умеет

| Команда | Инструмент | Зачем |
|---|---|---|
| `pulse list` | `list_tools` | Каталог с описаниями |
| `pulse probe` | `probe_stand` | `/api/v1/health` + задержка |
| `pulse call model_pulse hours=24` | `model_pulse` | Pareto + down-votes |
| `pulse schedule --every 3600` | `schedule_digest` | Первая сводка сразу, дальше по таймеру |
| `pulse digest` | `latest_digest` | Последний агрегат |
| `pulse jobs` | `list_jobs` | Что крутится 24/7 |

## Установка

```bash
pip install -e .
# или
uv sync
```

Токен не коммитится. Задайте `MCP_SHARED_TOKEN` в окружении.

```bash
export MCP_URL=https://aichallenge.arcilite.ru/mcp
export MCP_SHARED_TOKEN=   # ваш Bearer, не в git

pulse list
pulse probe
pulse schedule --every 3600 --note "night-watch"
pulse digest
```

Локальный сервер без сети:

```bash
pulse --stdio list
```

(`--stdio` запускает `python -m aichallenge_mcp` из вашего PATH / монорепо.)

## Протокол

- Streamable HTTP MCP, `initialize` → `list_tools` / `call_tool`
- Публичный путь стенда: `/mcp` (не отдельный порт)
- Без токена HTTP-клиент отказывается работать; значение токена в вывод не печатается
