# AI agent setup guides

[English](agents.en.md) · [Русский](agents.ru.md) · [Home](../README.md)

First check which tools the host client actually exposes to the model. A repository link or prompt does not give the model internet access or connect MCP:

| Environment | Route | Requirements |
| --- | --- | --- |
| Cloud chat with MCP settings | Connect hosted MCP | Server URL; platform authorization if prompted |
| OpenAI or Anthropic API agent | Connect remote MCP in the API request | Provider API access and key |
| DeepSeek Harness | Install the ready MCP patch | Node.js and DeepSeek API key |
| Chat without MCP but with a host-provided browser/HTTP tool | Query the official MediaWiki API through that tool | Host client exposes browser/fetch/HTTP |
| Codex, Claude Desktop, or another local client | Run local stdio MCP | Python and a synced local index |
| No MCP and no network access | Live data is unavailable | Ask the user to enable a data source |

## Cloud chat with MCP

**Server:** `https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp`

**Transport:** Streamable HTTP. The server calls Fischipedia directly; no local computer or database is needed.

1. Add the URL as a custom remote MCP server in a supported client.
2. Complete the authorization flow if the client asks.
3. Enable **Fisch Wiki** tools in a new chat.
4. Verify the connection by asking the agent to call `wiki_status` and report the official source name.
5. For facts, the agent should inspect the relevant page and cite its returned `source_url`.

Paste the [ready-to-use system prompt](CLOUD_PROMPT.en.md) into the agent instructions if the platform supports it. The MCP server also sends a short instruction on connection.

### ChatGPT Web

Custom MCP servers are available in ChatGPT Web on Business and Enterprise/Edu plans; creating and publishing one also depends on workspace role and permissions. Open **Plugins → + → Add custom MCP server**, enter the URL, configure authentication, acknowledge the warning, create the plugin, and enable the read-only tools in chat. Follow [OpenAI's setup guide](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

### Claude Web

Custom connectors are available on Pro, Max, Team, and Enterprise plans. Open **Settings → Connectors → Add custom connector**, add the URL, then select Fisch Wiki from **Search and tools** in chat. On Team/Enterprise, an organization owner may need to create the connector. Follow [Anthropic's setup guide](https://support.anthropic.com/en/articles/11175166-about-custom-integrations-using-remote-mcp).

### Other cloud MCP clients

Choose **Streamable HTTP**, enter the server URL, complete OAuth/authorization if requested, and enable the discovered tools. If the client only supports `stdio`, use its local mode or the HTTP fallback.

## Developer clients

These clients run on your computer but can call the **cloud** MCP endpoint directly. You do not need to install Python, run the local Fisch Wiki database, or sync the index for this route.

### Codex CLI and IDE

```sh
codex mcp add fish-wiki --url https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp
codex mcp list
```

Complete the authorization flow in Codex if prompted. In a chat, ask it to verify the source with `wiki_status`. This registers the remote HTTP MCP; the local MCP described later is a separate option. See [Codex MCP setup](https://developers.openai.com/learn/docs-mcp).

### Claude Code

```sh
claude mcp add --transport http fish-wiki https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp
claude mcp list
```

Follow Claude's OAuth flow if it requests authorization. Inside a session, use `/mcp` to check the connection. See [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

### Claude Desktop: cloud connection

In Claude Desktop, add this remote server through **Settings → Connectors**. Remote MCP setup happens in Claude; do not configure this remote URL as a local stdio process. See [Anthropic's guide](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp-servers).

## Repository link only

If an AI receives only this repository link, ask it to read the short map in [`llms.txt`](../llms.txt), then the agent instructions in [`AGENTS.md`](../AGENTS.md). The link itself gives the model no network tools. It should select a route the host actually provides:

1. **The host connected remote MCP and exposed its tools:** call them. If the host supports MCP but is not configured yet, its administrator/user must add the URL from this guide, enable the discovered tools, and forward results to the model.
2. **No MCP tools, but the host provided a browser/HTTP tool:** use that tool to query `https://fischipedia.org/w/api.php`. For example, search:

   ```text
   https://fischipedia.org/w/api.php?action=query&list=search&srsearch=Napoleonfish&srlimit=10&format=json&formatversion=2
   ```

   Read a result with `action=parse`. Follow MediaWiki `continue` fields when a complete listing is required.

3. **The host only opens URLs or provides web search:** this does not invoke MCP. The host must support Streamable HTTP JSON-RPC, handle authorization if required, and pass MCP results to the model. Use web search only when it actually returns material from the official domain.
4. **The host provides neither MCP tools nor a browser/HTTP tool:** say that current facts cannot be checked. Do not answer from memory or use another Fisch Wiki.

GitHub hosts code and instructions; it does not run MCP or grant a chat network access. An ordinary browser/HTTP fetch of the `/mcp` URL is not an MCP client either.

## API agents

These agents run in the provider's cloud. They do not need a local MCP process, but they do need API access and a provider key. If the MCP endpoint requires OAuth, your application must obtain an access token and pass it to the API connector; `require_approval` controls tool-call approval, not MCP authentication. Keep tokens out of the repository.

### OpenAI Responses API

Create the OpenAI client with an API key in your server environment, then add the remote server to `tools`:

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="YOUR_MODEL",
    input="Find the official Fischipedia page about fishing rods and summarize verified facts with links.",
    tools=[{
        "type": "mcp",
        "server_label": "fish_wiki",
        "server_url": "https://fish-wiki-mcp.leafy-bream-8099.chatgpt.site/mcp",
        "headers": {"Authorization": f"Bearer {os.environ['FISCH_WIKI_MCP_TOKEN']}"},
        "require_approval": "always",
    }],
)
```

Add `import os`, set `FISCH_WIKI_MCP_TOKEN` securely after OAuth, and replace `YOUR_MODEL`. If the provider handles OAuth itself, use its built-in authorization flow instead of passing a token manually. See the [Responses API MCP guide](https://developers.openai.com/api/docs/guides/tools-remote-mcp) for approval and allowed-tool options.

### Anthropic Messages API

Use the MCP connector with the Messages API. Set an available model, the server URL, the `fish_wiki` name, and enable `mcp_toolset`:

```python
response = client.beta.messages.create(
    model="YOUR_CLAUDE_MODEL",
    max_tokens=1200,
    messages=[{"role": "user", "content": "Find the official Fischipedia page about fishing rods and summarize verified facts with links."}],
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

Add `import os`, obtain an OAuth access token for the MCP server, and keep it outside the repository. Create `client` with the Anthropic SDK, set the API key securely, and replace `YOUR_CLAUDE_MODEL`. If the platform handles OAuth itself, use its built-in flow. See [Anthropic's MCP connector guide](https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector).

## DeepSeek

### Regular `chat.deepseek.com`

The regular web chat has no setting for this custom MCP server. Internet Search may find Fischipedia, but **it does not invoke this project's MCP tools**. If web search is available, use the [prompt for no-MCP mode](CLOUD_PROMPT.en.md#no-mcp-mode). Otherwise current facts cannot be retrieved.

### DeepSeek Harness

Harness is a separate web chat that supports MCP. You need Node.js and a DeepSeek API key.

```sh
git clone https://github.com/zarell1/fish-wiki-mcp.git
cd fish-wiki-mcp
npx @deepseek-ai/dsh web --patch ./integrations/deepseek-harness/cordis.patch.yml
```

Open the address printed by the command, configure the model and API key in Harness, then enable the Fisch Wiki tools in a new chat. The command runs Harness on the current machine. For always-on cloud access, host it on your own server with HTTPS and access controls. References: [DeepSeek Harness](https://deepseek.com/harness/) · [model setup](https://deepseek-harness.github.io/deepseek-harness/en/guide/providers) · [MCP client](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md).

## Local MCP

Use this when the MCP server itself should run as a local stdio process. Sync local data first; the cloud server does not need this step. Codex and Claude Code can connect to the remote endpoint with the commands above; Claude Desktop supports a remote connector through Settings.

```powershell
git clone https://github.com/zarell1/fish-wiki-mcp.git
cd fish-wiki-mcp
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe fischwiki_api.py probe
.\.venv\Scripts\python.exe fischwiki_api.py sync
```

### Claude Desktop or another stdio client

Set the local MCP command in your client:

```text
<path-to-repo>\.venv\Scripts\python.exe <path-to-repo>\fischwiki_mcp.py
```

On macOS/Linux, use `<repo>/.venv/bin/python <repo>/fischwiki_mcp.py`. Do not run `sync` for every question; update the index separately. Local tool names differ from cloud tools; see the [reference](TOOLS.en.md#local-mcp).

## Related guides

- [Detailed cloud-agent prompt](CLOUD_PROMPT.en.md)
- [Tool reference and parameters](TOOLS.en.md)
- [Russian guide](agents.ru.md)
