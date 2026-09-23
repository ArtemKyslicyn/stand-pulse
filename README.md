# Stand Pulse

Дежурный MCP-клиент к живому стенду. Не каталог echo-инструментов, а **вахта**: сторож снимает `/health` и рейтинг моделей, открывает инциденты и держит периодическую сводку в SQLite.

Подключаешь агента или этот CLI — спрашиваешь «что на вахте?» вместо ручного обхода API.

Сервер: [AIChallenge](https://github.com/ArtemKyslicyn/AIChallenge) (`apps/mcp`).

## Зачем это

Стенд с моделями падает не «красиво»: health молчит, одна модель начинает собирать down-votes, задержка ползёт. `watch_brief` собирает это в один экран:

- `critical` — стенд не отвечает
- `warning` — высокая задержка или модель на внимании
- `ok` — спокойно, есть тренд latency

Инцидент можно подтвердить (`pulse ack`), сводку крутить 24/7 (`pulse schedule`).

## Команды

```bash
pip install -e .
# или: uv sync

export MCP_URL=https://aichallenge.arcilite.ru/mcp
export MCP_SHARED_TOKEN=   # Bearer, не в git

pulse watch                 # вахта: severity + инциденты
pulse probe                 # живой /health
pulse history               # последние пробы
pulse schedule --every 3600 --note night-watch
pulse digest
pulse ack <incident_id> --note "вижу, чиню"
pulse list
```

Локально, без токена (рядом должен быть монорепо AIChallenge):

```bash
pulse --stdio watch
pulse --stdio list
```

Токен в вывод не печатается.

## Инструменты сервера

| Инструмент | Роль |
|---|---|
| `watch_brief` | Главный: severity, открытые инциденты, Δ latency |
| `probe_stand` | `/api/v1/health` + задержка |
| `model_pulse` | Pareto + down-votes |
| `ack_incident` | Оператор увидел инцидент |
| `probe_history` | История проб в SQLite |
| `schedule_digest` / `latest_digest` / `list_jobs` | Периодический агрегат 24/7 |
