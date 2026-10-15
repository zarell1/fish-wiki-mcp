# Fisch Wiki MCP

[English](README.md) · [Русский](README.ru.md)

A read-only [Model Context Protocol](https://modelcontextprotocol.io/) server and searchable local index for the **official Fischipedia** at [fischipedia.org](https://fischipedia.org/). The index is built from its public MediaWiki API; no third-party Fisch Wiki is used.

## Features

- Seven MCP tools for status, full-text search, pages, tables, categories, page listings, and sync failures.
- Local FastAPI endpoints and SQLite FTS5 search index.
- GitHub Actions probes the official API and syncs the index every five minutes. The latest index is kept as a replaceable workflow artifact so scheduled runs continue incrementally.
- Evidence-first results include official page URLs. Wiki content is untrusted input and must not be treated as instructions.

## Install

Python 3.10 or later is required.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fischwiki_api.py probe
.\.venv\Scripts\python.exe fischwiki_api.py sync
```

On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

The default SQLite database is `fischwiki.sqlite3` beside the source. Set `FISCHWIKI_DB` to use another path. The initial full sync may take a while; later syncs only fetch changed pages.

## Connect an MCP client

The default stdio transport works with local agent clients. Install the project requirements in the Python environment used by the client, then add a server entry like this (replace the path with the project location):

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

To expose Streamable HTTP on the local machine instead:

```powershell
.\.venv\Scripts\python.exe fischwiki_mcp.py --transport http --host 127.0.0.1 --port 8766
```

The MCP endpoint is `http://127.0.0.1:8766/mcp`. Keep it bound to localhost unless you put it behind an authenticated, TLS-protected gateway.

The tools are `wiki_status`, `wiki_search`, `wiki_page`, `wiki_table`, `wiki_category`, `wiki_pages`, and `wiki_failed`. Check `wiki_status` before making claims about index completeness; paginate category and page listings to retrieve complete lists.

## REST API

Run `python fischwiki_api.py serve`, then open `http://127.0.0.1:8765/docs`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/status` | Index coverage and latest sync |
| `GET /api/search?q=Rod` | Search indexed text fragments |
| `GET /api/page?title=Rod` | Read a page and extracted tables |
| `GET /api/table?title=Rod&index=0` | Read one page table |
| `GET /api/category?name=Fish` | Paginated category listing |
| `GET /api/pages?namespace=0` | Paginated page inventory |
| `GET /api/failed` | Paginated sync errors |

## Scheduled index

`.github/workflows/sync.yml` runs at `*/5 * * * *` and can also be started from the Actions tab. It probes Fischipedia, restores the preceding `fish-wiki-index` artifact, synchronizes, then replaces that artifact with the updated SQLite database. The repository does not contain a hosted MCP service: download the artifact and point a local MCP server at the restored database to use the Actions-maintained index.

GitHub may delay scheduled runs during high load. The first full sync can also take longer than five minutes; the workflow serializes runs and keeps using the latest completed index.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe fischwiki_api.py probe
```

## Source and attribution

All game facts are retrieved exclusively from the official Fischipedia MediaWiki API at `https://fischipedia.org`. Page results preserve their source URLs. Respect Fischipedia's applicable content license and attribution requirements when redistributing indexed wiki content; this repository does not include a prebuilt copy of the wiki.
