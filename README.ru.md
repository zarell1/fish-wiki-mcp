# Fisch Wiki MCP

[English](README.md) · [Русский](README.ru.md)

Сервер [Model Context Protocol](https://modelcontextprotocol.io/) только для чтения и локальный поисковый индекс **официальной Fischipedia**: [fischipedia.org](https://fischipedia.org/). Данные загружаются из её публичного MediaWiki API. Сторонние Fisch Wiki как источник не используются.

## Возможности

- Семь MCP-инструментов: статус индекса, полнотекстовый поиск, чтение страниц и таблиц, категории, список страниц и ошибки синхронизации.
- Локальные HTTP-методы FastAPI и полнотекстовый индекс SQLite FTS5.
- GitHub Actions проверяет официальный API и синхронизирует индекс каждые пять минут. Последняя база сохраняется в обновляемом артефакте workflow, поэтому следующие запуски продолжают инкрементальную синхронизацию.
- Результаты содержат ссылки на официальные страницы. Текст Wiki считается недоверенным содержимым, а не инструкциями.

## Установка

Требуется Python 3.10 или новее.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fischwiki_api.py probe
.\.venv\Scripts\python.exe fischwiki_api.py sync
```

В macOS/Linux замените `.\.venv\Scripts\python.exe` на `.venv/bin/python`.

По умолчанию база `fischwiki.sqlite3` создаётся рядом с кодом. Для другого пути задайте `FISCHWIKI_DB`. Первичная загрузка всей Wiki может занять много времени; последующие запуски получают только изменившиеся страницы.

## Подключение MCP-клиента

Локальный транспорт stdio совместим с агентскими приложениями. Установите зависимости проекта в окружение Python, которое использует клиент, и добавьте конфигурацию (замените путь на расположение проекта):

```json
{
  "mcpServers": {
    "fish-wiki": {
      "command": "C:/path/to/fischwiki_api/.venv/Scripts/python.exe",
      "args": ["C:/path/to/fischwiki_api/fischwiki_mcp.py"]
    }
  }
}
```

Для локального Streamable HTTP:

```powershell
.\.venv\Scripts\python.exe fischwiki_mcp.py --transport http --host 127.0.0.1 --port 8766
```

Адрес MCP: `http://127.0.0.1:8766/mcp`. Оставляйте его привязанным к localhost, если перед ним нет защищённого TLS-шлюза с аутентификацией.

Инструменты: `wiki_status`, `wiki_search`, `wiki_page`, `wiki_table`, `wiki_category`, `wiki_pages` и `wiki_failed`. Перед выводами о полноте проверяйте `wiki_status`; для получения полного списка листайте страницы результатов категорий и списка страниц.

## REST API

Запустите `python fischwiki_api.py serve`, затем откройте `http://127.0.0.1:8765/docs`.

| Endpoint | Назначение |
| --- | --- |
| `GET /api/status` | Полнота индекса и последняя синхронизация |
| `GET /api/search?q=Rod` | Поиск фрагментов текста |
| `GET /api/page?title=Rod` | Страница и извлечённые таблицы |
| `GET /api/table?title=Rod&index=0` | Одна таблица страницы |
| `GET /api/category?name=Fish` | Постраничный список категории |
| `GET /api/pages?namespace=0` | Постраничный список страниц |
| `GET /api/failed` | Постраничный список ошибок синхронизации |

## Автоматическая синхронизация

`.github/workflows/sync.yml` запускается по расписанию `*/5 * * * *`; его также можно запустить вручную на вкладке Actions. Workflow проверяет Fischipedia, восстанавливает предыдущий артефакт `fish-wiki-index`, обновляет базу и заменяет артефакт новой версией SQLite. Репозиторий не размещает общедоступный MCP-сервис: чтобы использовать индекс из Actions локально, скачайте артефакт и укажите его базу при запуске MCP-сервера.

GitHub может задерживать запланированные задания при высокой нагрузке. Первичная полная синхронизация также может длиться дольше пяти минут; запуски выполняются последовательно, используя последний успешно сохранённый индекс.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe fischwiki_api.py probe
```

## Источник и атрибуция

Все игровые сведения загружаются только через MediaWiki API официальной Fischipedia: `https://fischipedia.org`. Ответы сохраняют ссылки на первоисточники. При распространении содержимого Wiki соблюдайте применимую лицензию Fischipedia и требования атрибуции. В репозитории нет готовой копии Wiki.
