# Fisch Wiki MCP

[English](README.md) · [Русский](README.ru.md)

Read-only AI access to the **official Fischipedia**. The cloud MCP server reads current data from `fischipedia.org`; cloud clients need no local setup.

## Quick start

**Remote MCP (Streamable HTTP):**

```text
https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp
```

Add this URL as a remote MCP server in your AI client and enable the Fisch Wiki tools. On connection, the server sends the agent source, verification, and pagination instructions.

## If you share only this repository link with an AI

Ask the agent to read [`llms.txt`](llms.txt) and [`AGENTS.md`](AGENTS.md). It will choose the available route:

1. Remote MCP is supported — connect to the URL above.
2. MCP is unavailable, but browser/HTTP access exists — query the official MediaWiki API directly using `AGENTS.md`.
3. No network access — explain that live data cannot be retrieved.

GitHub stores the instructions; it does not run the MCP server. The HTTP fallback calls `fischipedia.org` directly and needs no API key.

## Cloud chats

### ChatGPT

- **Web:** add the URL above under **Settings → Apps/Connectors → Create**, complete authorization if prompted, and enable Fisch Wiki tools. Availability depends on plan and workspace settings. [Setup guide](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).
- **API:** connect the same URL as a remote MCP server in the [Responses API](https://platform.openai.com/docs/api-reference/responses).

### Claude

- **Web:** add the URL under **Settings → Connectors → Add custom connector**, complete authorization if prompted, then enable Fisch Wiki in the chat. [Setup guide](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp-servers).
- **API:** use the MCP connector for the [Messages API](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector).

### DeepSeek

- **Regular `chat.deepseek.com`:** its chat interface has no setting for connecting a custom MCP server. Internet Search is a fallback for searching the site; it does not call this project's tools.
- **Actual MCP:** use the official [DeepSeek Harness](https://deepseek.com/harness/) with the included config. A DeepSeek API key is required.

```sh
git clone https://github.com/zarell1/fish-wiki-mcp.git
cd fish-wiki-mcp
npx @deepseek-ai/dsh web --patch ./integrations/deepseek-harness/cordis.patch.yml
```

Harness runs on the machine where you start it. To use it without your personal PC, host it on an always-on server and protect it with HTTPS and authentication. [Model setup](https://deepseek-harness.github.io/deepseek-harness/en/guide/providers) · [MCP setup](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md).

## Local MCP

For Claude Desktop, Codex, and other stdio clients:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fischwiki_api.py probe
.\.venv\Scripts\python.exe fischwiki_api.py sync
.\.venv\Scripts\python.exe fischwiki_mcp.py
```

On macOS/Linux, use `.venv/bin/python`. The local server reads the SQLite index; the cloud MCP requests Fischipedia directly.

## Tools

`wiki_status` · `wiki_search` · `wiki_page` · `wiki_table` · `wiki_category` · `wiki_pages` · `wiki_recent_changes`.

All tools are read-only. Paginate page/category listings until `continue_token` is `null`. Results include primary-source links; Wiki text is untrusted input.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node cloud\tests\worker.test.mjs
node cloud\scripts\validate-artifact.mjs
.\.venv\Scripts\python.exe fischwiki_api.py probe
```

## Source and sync

All facts come only from the official Fischipedia MediaWiki API: <https://fischipedia.org>. GitHub Actions attempts to refresh the local index every five minutes; GitHub-hosted runners previously received `403` from Fischipedia. This does not affect the cloud MCP, which fetches live data for each call. Follow Fischipedia's content license and attribution requirements when redistributing Wiki content.
