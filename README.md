# Stand Pulse

**Дежурство стенда.** Пока модели отвечают посетителям, этот MCP-сервер сидит на вахте: падение `/health`, рост задержки, модели с жалобами. Агент или CLI спрашивают не «какие есть tools», а **можно ли отойти**.

Сервер: [AIChallenge](https://github.com/ArtemKyslicyn/AIChallenge) (`apps/mcp`).  
Консоль: `/?shell=mcp` — блок «Сейчас» говорит, что делать.

## Продукт

| Кто | Работа |
|---|---|
| Оператор стенда | Открыл экран перед уходом: жив ли стенд, кого ругают, крутится ли ночная сводка |
| Агент | Тот же контур через MCP: `watch_brief` → действие (`probe`, `ack`, `schedule`) |
| CLI | То же с ноутбука, без браузера |

Правило вахты:

1. Стенд молчит → `critical`, не оставляйте без присмотра  
2. Есть неподтверждённый инцидент → подтвердите, что видели  
3. Нет расписания → включите ежечасный обход  
4. Иначе → можно отойти

Инциденты живут в SQLite: `stand_down`, `high_latency`, `model_attention`. Сводка пишется по таймеру, даже когда консоль закрыта.

## Команды

```bash
pip install -e .

export MCP_URL=https://aichallenge.arcilite.ru/mcp
export MCP_SHARED_TOKEN=   # не в git

pulse watch
pulse probe
pulse schedule --every 3600 --note night-watch
pulse ack <incident_id>
```

Рядом с монорепо, без токена:

```bash
pulse --stdio watch
```

Демо: [`demo.mp4`](demo.mp4)
