# Fisch Wiki MCP

[English](README.md) · [Русский](README.ru.md)

Read-only AI access to the **official Fischipedia**. The cloud MCP server reads current data from `fischipedia.org`; no local setup is needed for cloud clients.

## Быстрый старт

**Remote MCP (Streamable HTTP):**

```text
https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp
```

Добавьте URL как удалённый MCP-сервер в настройках AI-клиента и включите инструменты Fisch Wiki. На подключении сервер передаёт агенту инструкции по источникам, проверке страниц и пагинации.

## Если нейросети отправили только ссылку на репозиторий

Попросите её прочитать [`llms.txt`](llms.txt) и [`AGENTS.md`](AGENTS.md). Агент выберет способ сам:

1. Есть подключение remote MCP — использовать URL выше.
2. MCP недоступен, но есть браузер или HTTP-запросы — обратиться напрямую к официальному MediaWiki API по инструкциям в `AGENTS.md`.
3. Нет сетевого доступа — объяснить, что получить свежие данные нельзя.

GitHub хранит инструкции, но не запускает MCP. Резервные HTTP-запросы идут напрямую на `fischipedia.org` и не требуют API-ключа.

## Облачные чаты

### ChatGPT

- **Веб-чат:** добавьте URL выше в **Settings → Apps/Connectors → Create** и разрешите инструменты Fisch Wiki. Возможности зависят от плана и настроек workspace. [Документация](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).
- **API:** подключите тот же URL как remote MCP в [Responses API](https://platform.openai.com/docs/api-reference/responses).

### Claude

- **Веб-чат:** добавьте URL в **Settings → Connectors → Add custom connector** и включите Fisch Wiki в чате. [Инструкция](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp-servers).
- **API:** используйте MCP connector для [Messages API](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector).

### DeepSeek

- **Обычный `chat.deepseek.com`:** в интерфейсе чата нет настройки для подключения пользовательского MCP-сервера. Можно включить Internet Search; это запасной поиск по сайту, он не вызывает инструменты этого проекта.
- **Реальный MCP:** в официальном [DeepSeek Harness](https://deepseek.com/harness/) примените готовую конфигурацию. Нужен DeepSeek API key.

```sh
git clone https://github.com/zarell1/fish-wiki-mcp.git
cd fish-wiki-mcp
npx @deepseek-ai/dsh web --patch ./integrations/deepseek-harness/cordis.patch.yml
```

Harness запускает чат-сервер там, где выполнена команда. Для работы без личного ПК разместите Harness на постоянно работающем сервере и закройте его HTTPS и авторизацией. [Настройка моделей](https://deepseek-harness.github.io/deepseek-harness/en/guide/providers) · [подключение MCP](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md).

## Локальный MCP

Для Claude Desktop, Codex и других клиентов со stdio:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fischwiki_api.py probe
.\.venv\Scripts\python.exe fischwiki_api.py sync
.\.venv\Scripts\python.exe fischwiki_mcp.py
```

На macOS/Linux используйте `.venv/bin/python`. По умолчанию локальный сервер читает SQLite-индекс; облачный MCP запрашивает Fischipedia напрямую.

## Инструменты

`wiki_status` · `wiki_search` · `wiki_page` · `wiki_table` · `wiki_category` · `wiki_pages` · `wiki_recent_changes`.

Все инструменты только для чтения. Списки страниц и категорий нужно получать до конца по `continue_token`. Ответы содержат ссылку на первоисточник; текст Wiki считается недоверенным.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node cloud\tests\worker.test.mjs
node cloud\scripts\validate-artifact.mjs
.\.venv\Scripts\python.exe fischwiki_api.py probe
```

## Источник

Все сведения берутся только из MediaWiki API официальной Fischipedia: <https://fischipedia.org>. GitHub Actions пытается обновлять локальный индекс каждые 5 минут; GitHub-hosted runner ранее получал `403` от Fischipedia. Это не влияет на облачный MCP, который получает данные при каждом вызове. При распространении содержимого Wiki соблюдайте её лицензию и требования атрибуции.
