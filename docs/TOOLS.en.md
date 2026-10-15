# MCP tool reference

[English](TOOLS.en.md) · [Русский](TOOLS.ru.md) · [Setup guides](agents.en.md) · [Home](../README.md)

The cloud endpoint queries the live MediaWiki API of the official Fischipedia. All its tools are read-only. Search and listing results may be paginated.

## Cloud MCP

| Tool | Arguments | Purpose and limits |
| --- | --- | --- |
| `wiki_status` | None | Check API access; returns the official source, endpoint, mode, and check time. `complete: false` means this is not a complete local Wiki mirror. |
| `wiki_search` | `query` (required), `limit` (1–50, default 20) | Find pages and text snippets. Results are candidates, not full pages or evidence of completeness. May return a `continue_token`. |
| `wiki_page` | `title` (required), `max_chars` (1–30,000, default 12,000) | Read wikitext, categories, and `source_url`. `has_more: true` means the text was truncated; request again with a larger limit (up to 30,000). |
| `wiki_table` | `title` (required), `index` (0–100, default 0) | Read one table as rows and cells. Index starts at zero. Check headers, units, and notes. |
| `wiki_category` | `name` (required), `limit` (1–500, default 100), `continue_token` | List category members. Repeat with the returned token unchanged until it is `null`. |
| `wiki_pages` | `namespace` (optional), `prefix` (optional), `limit` (1–500, default 100), `continue_token` | List Wiki pages. Pass the token back unchanged until `null`; the full page inventory can be very large. |
| `wiki_recent_changes` | `limit` (1–100, default 20) | Return a short recent-changes list. It is not full history and does not paginate. |

### Call order

1. `wiki_status` — confirm that the official API responds.
2. `wiki_search` — find candidate pages.
3. `wiki_page` and, when needed, `wiki_table` — verify primary sources.
4. `wiki_category` / `wiki_pages` — only when a listing is requested; continue until `continue_token: null`.
5. Cite `source_url` next to every fact. If a field is absent, say “Not stated”.

**Important:** do not construct, truncate, or rewrite a `continue_token`. Pass the returned value directly to the next call.

## Local MCP

The local `fischwiki_mcp.py` server reads a SQLite index created by `fischwiki_api.py sync`. Its tools differ from the cloud server:

| Local tool | Difference |
| --- | --- |
| `wiki_status` | Reports local-index coverage and freshness. Check completeness before claiming “all”. |
| `wiki_search` | Uses `q`, `limit`, and `offset`; searches local indexed fragments. |
| `wiki_page` | Also accepts text offset/limit and options for extracting tables and links. |
| `wiki_table` | Reads a table from a locally stored page. |
| `wiki_category` | Uses `offset` and `total`; increase the offset until the list is exhausted. |
| `wiki_pages` | Uses `offset` and optional namespace/prefix filters. |
| `wiki_failed` | Lists pages that failed during the last sync. Not available in the cloud version. |

The local MCP does not provide `wiki_recent_changes`; that tool is cloud-only. Local results depend on successful sync and may lag behind the Wiki. See the [local setup guide](agents.en.md#local-mcp).

## Local REST API and prompt files

The repository root also contains `agent_config.json`, `api_tools.json`, `agent_prompt.txt`, and `browser_prompt.txt`. These are helper configurations, not a connected cloud agent or a public API URL.

- `agent_config.json` and `api_tools.json` describe the local REST API at `http://127.0.0.1:8765`. It is available only after running `python fischwiki_api.py serve`; first create the index with `python fischwiki_api.py sync`.
- `agent_prompt.txt` is a research instruction set for that local indexed API. It does not add tools or connect MCP.
- `browser_prompt.txt` is a browser-search instruction set. It is not an MCP connection and cannot guarantee exhaustive Wiki coverage.
- For cloud agents, use the hosted MCP and [cloud prompt](CLOUD_PROMPT.en.md), or the official HTTP fallback in the [route-selection guide](agents.en.md#repository-link-only).

## Hosted HTTP and direct MediaWiki API

If the host client exposes a browser/HTTP tool but no MCP client, use GET requests to the hosted JSON routes. Base URL: `https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/api/`.

| GET route | Parameters |
| --- | --- |
| `status` | none |
| `search` | required `query`; optional `limit` (1–50) |
| `page` | required `title`; optional `max_chars` (1–30000) |
| `table` | required `title`; optional `index` (0–100) |
| `category` | required `name`; optional `limit` (1–500), `continue_token` |
| `pages` | optional `namespace`, `prefix`, `limit` (1–500), `continue_token` |
| `recent-changes` | optional `limit` (1–100) |

Each route returns the JSON tool result directly, including `source_url` and `continue_token` where relevant. URL-encode parameter values and pass continuation tokens unchanged. These public, read-only routes query the same official Fischipedia API as MCP. If the host gets HTTP 403/Cloudflare challenge or cannot reach these routes, use its HTTP tool with `https://fischipedia.org/w/api.php`. Neither path is MCP. A prompt or repository link cannot grant network access, and opening `/mcp` with an ordinary fetcher does not invoke MCP. See [Repository link only](agents.en.md#repository-link-only) for examples.
