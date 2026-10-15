# Гайды по подключению AI-агентов

[English](agents.en.md) · [Русский](agents.ru.md) · [На главную](../README.ru.md)

Сначала определите, какие возможности хост-клиент действительно предоставил модели. Ссылка на репозиторий или промпт сами по себе не дают модели интернет и не подключают MCP:

| Среда | Маршрут | Что нужно |
| --- | --- | --- |
| Облачный чат с настройкой MCP | Подключить hosted MCP | URL сервера; иногда авторизация платформы |
| OpenAI или Anthropic API | Подключить remote MCP к API | API-ключ провайдера и MCP-конфигурация |
| DeepSeek Harness | Установить готовый MCP-патч | Node.js и DeepSeek API key |
| Чат без MCP, но с browser/HTTP-инструментом от хоста | Запросить официальный MediaWiki API этим инструментом | Хост-клиент предоставляет браузер/fetch/HTTP tool |
| Codex, Claude Desktop или иной клиент на своём ПК | Локальный stdio MCP | Python и локально синхронизированный индекс |
| Нет MCP и нет доступа к сети | Получить данные нельзя | Попросить пользователя включить источник данных |

## Облачный чат с MCP

**Сервер:** `https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp`

**Транспорт:** Streamable HTTP. Сервер обращается напрямую к Fischipedia; ваш компьютер и локальная база не нужны.

1. В настройках поддерживаемого клиента добавьте пользовательский remote MCP сервер с URL выше.
2. Пройдите авторизацию, если её запросит клиент.
3. В новом чате включите инструменты **Fisch Wiki**.
4. Попросите проверить доступ: агент должен вызвать `wiki_status`, затем показать название официального источника.
5. Для ответов по фактам агент должен найти страницу и сослаться на выданный `source_url`.

Вставьте [готовый системный промпт](CLOUD_PROMPT.ru.md) в инструкции агента, если платформа поддерживает это поле. MCP сервер также передаёт свою короткую инструкцию при подключении.

### ChatGPT Web

Пользовательские MCP-серверы доступны в ChatGPT Web для планов Business и Enterprise/Edu; создание и публикация также зависят от роли и разрешений рабочего пространства. Откройте **Plugins → + → Add custom MCP server**, вставьте URL, настройте авторизацию, подтвердите предупреждение, создайте plugin и включите нужные read-only инструменты в чате. Следуйте [официальной инструкции OpenAI](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

### Claude Web

Custom connectors доступны для планов Pro, Max, Team и Enterprise. Откройте **Settings → Connectors → Add custom connector**, добавьте URL, затем выберите Fisch Wiki в **Search and tools** в чате. Для Team/Enterprise создание подключения может требовать владельца workspace. Следуйте [официальной инструкции Anthropic](https://support.anthropic.com/en/articles/11175166-about-custom-integrations-using-remote-mcp).

### Другие облачные MCP-клиенты

Выберите транспорт **Streamable HTTP**, вставьте URL выше, выполните OAuth/авторизацию при запросе и включите обнаруженные инструменты. Если клиент предлагает только `stdio` и не может подключаться к удалённым серверам, используйте его локальный режим или HTTP fallback.

## Клиенты разработчика

Эти клиенты работают на компьютере, но могут вызывать **облачный** MCP endpoint напрямую. Для этого не нужно устанавливать Python, запускать локальную Fisch Wiki базу или выполнять синхронизацию.

### Codex CLI и IDE

```sh
codex mcp add fish-wiki --url https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp
codex mcp list
```

Если нужна авторизация, завершите её в Codex. После подключения в чате попросите проверить источник через `wiki_status`. Команда добавляет remote HTTP MCP; локальный MCP из следующего раздела — отдельный вариант.

### Claude Code

```sh
claude mcp add --transport http fish-wiki https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp
claude mcp list
```

Если Claude сообщает, что нужна авторизация, следуйте его OAuth flow. Внутри сессии используйте `/mcp`, чтобы проверить статус. См. [официальный гайд Claude Code MCP](https://code.claude.com/docs/en/mcp).

### Claude Desktop: облачное подключение

В Claude Desktop подключите этот же remote server через **Settings → Connectors**. Подключение remote MCP настраивается в Claude; удалённый URL не нужно прописывать как локальный stdio-процесс. См. [официальный гайд](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp-servers).

## Только ссылка на репозиторий

Если нейросети отправили только ссылку на этот проект, попросите её прочитать [короткую карту `llms.txt`](../llms.txt), затем [инструкции агенту `AGENTS.md`](../AGENTS.md). Ссылка сама по себе не предоставляет модели сетевые инструменты. Выбирать нужно только маршрут, который реально поддерживает хост:

1. **Хост подключил remote MCP и предоставил модели инструменты:** вызвать их. Если хост поддерживает MCP, но ещё не настроен, администратор/пользователь должен добавить URL из этого гайда в настройки хоста, включить найденные инструменты и передавать модели результаты вызовов.
2. **MCP-инструментов нет, но хост предоставил browser/HTTP tool:** вызывайте JSON-маршруты репозитория обычными GET-запросами. Проверьте `https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/api/status`, найдите страницу через `/api/search?query=Napoleonfish&limit=10`, затем прочитайте `/api/page?title=Napoleonfish` или `/api/table?title=Napoleonfish&index=0`. Для полного списка используйте `/api/category?name=<закодированная категория>&limit=100` или `/api/pages?namespace=0&limit=100`, передавая `continue_token` без изменений. Эти маршруты обращаются к тому же официальному API и возвращают JSON со ссылками `source_url`. Если они недоступны, запросите Fischipedia напрямую:

   ```text
   https://fischipedia.org/w/api.php?action=query&list=search&srsearch=Napoleonfish&srlimit=10&format=json&formatversion=2
   ```

   Затем прочитать её через `action=parse`. Следовать MediaWiki `continue` до конца, если нужен полный список.

3. **Хост только открывает URL или даёт веб-поиск:** это не вызывает MCP. Для MCP хост должен поддерживать Streamable HTTP JSON-RPC, авторизацию при необходимости и передачу результатов модели. Веб-поиск применяйте только если он действительно возвращает материал с официального домена.
4. **Хост не предоставил ни MCP-инструменты, ни browser/HTTP tool:** сообщить, что проверить свежие данные нельзя. Не отвечать по памяти и не использовать стороннюю Fisch Wiki.

GitHub хранит код и инструкции, но не исполняет MCP и не даёт чату сетевой доступ автоматически. Обычный browser/HTTP fetch URL `/mcp` также не является MCP-клиентом.

## Агенты через API

Эти варианты работают в облаке провайдера. Отдельный локальный MCP-процесс не требуется, но нужны API-доступ и ключ провайдера. Если MCP endpoint запросит OAuth, приложение должно получить access token и передать его API-коннектору; `require_approval` управляет подтверждением вызовов инструментов, а не авторизацией MCP. Не сохраняйте токены в репозитории.

### OpenAI Responses API

Для запуска запроса нужен OpenAI API key в серверном окружении. Добавьте удалённый сервер в `tools`:

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="YOUR_MODEL",
    input="Найди на официальной Fischipedia страницу о fishing rods и изложи подтверждённые факты со ссылками.",
    tools=[{
        "type": "mcp",
        "server_label": "fish_wiki",
        "server_url": "https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp",
        "headers": {"Authorization": f"Bearer {os.environ['FISCH_WIKI_MCP_TOKEN']}"},
        "require_approval": "always",
    }],
)
```

Добавьте `import os`, задайте `FISCH_WIKI_MCP_TOKEN` безопасным способом после OAuth и замените `YOUR_MODEL`. Если провайдер выполняет OAuth сам, используйте его штатный поток авторизации вместо ручной передачи токена. Подробности и параметры доступа к инструментам — в [документации Responses API](https://developers.openai.com/api/docs/guides/tools-remote-mcp).

### Anthropic Messages API

Используйте MCP connector в запросе Messages API. Укажите модель, доступную аккаунту, URL сервера, имя `fish_wiki` и включите `mcp_toolset`:

```python
response = client.beta.messages.create(
    model="YOUR_CLAUDE_MODEL",
    max_tokens=1200,
    messages=[{"role": "user", "content": "Найди на официальной Fischipedia страницу о fishing rods и изложи подтверждённые факты со ссылками."}],
    mcp_servers=[{
        "type": "url",
        "url": "https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp",
        "name": "fish_wiki",
        "authorization_token": os.environ["FISCH_WIKI_MCP_TOKEN"],
    }],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "fish_wiki"}],
    betas=["mcp-client-2025-11-20"],
)
```

Добавьте `import os`, получите OAuth access token для MCP и храните его вне репозитория. Создайте `client` через Anthropic SDK, задайте API key безопасно и замените `YOUR_CLAUDE_MODEL`. Если платформа выполняет OAuth сама, используйте её штатный flow. См. [документацию Anthropic MCP connector](https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector).

## DeepSeek

### Обычный `chat.deepseek.com`

В стандартном веб-чате нет настройки для подключения этого custom MCP-сервера. Включённый Internet Search может найти Fischipedia, но **не вызывает MCP-инструменты проекта**. Если доступен веб-поиск, дайте агенту [промпт для режима без MCP](CLOUD_PROMPT.ru.md#промпт-для-режима-без-mcp). Иначе свежие данные получить нельзя.

### DeepSeek Harness

Harness — отдельный веб-чат, который умеет подключать MCP. Нужны Node.js и DeepSeek API key.

```sh
git clone https://github.com/zarell1/fish-wiki-mcp.git
cd fish-wiki-mcp
npx @deepseek-ai/dsh web --patch ./integrations/deepseek-harness/cordis.patch.yml
```

Откройте адрес, который напечатает команда, настройте модель и API key в Harness, затем включите новый чат. Команда запускает Harness на текущем компьютере. Для постоянного облачного доступа разместите его на собственном сервере с HTTPS и защитой входа. Документы: [DeepSeek Harness](https://deepseek.com/harness/) · [настройка модели](https://deepseek-harness.github.io/deepseek-harness/en/guide/providers) · [MCP-клиент](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md).

## Локальный MCP

Используйте этот маршрут, если MCP-сервер должен работать как локальный stdio-процесс. Данные сначала нужно синхронизировать; облачный MCP этого шага не требует. Codex и Claude Code обычно проще подключить к удалённому endpoint командами выше; Claude Desktop поддерживает remote connector через Settings.

```powershell
git clone https://github.com/zarell1/fish-wiki-mcp.git
cd fish-wiki-mcp
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fischwiki_api.py probe
.\.venv\Scripts\python.exe fischwiki_api.py sync
```

### Claude Desktop или другой stdio-клиент

Укажите в настройках локального MCP-клиента команду запуска:

```text
<путь-к-репозиторию>\.venv\Scripts\python.exe <путь-к-репозиторию>\fischwiki_mcp.py
```

На macOS/Linux используйте `<repo>/.venv/bin/python <repo>/fischwiki_mcp.py`. Не запускайте `sync` при каждом вопросе: индекс обновляется отдельно. Список локальных MCP-инструментов отличается от облачного — см. [справочник](TOOLS.ru.md#локальный-mcp).

## Связанные гайды

- [Подробный промпт облачного агента](CLOUD_PROMPT.ru.md)
- [Справочник инструментов и их параметров](TOOLS.ru.md)
- [Английский гайд](agents.en.md)
