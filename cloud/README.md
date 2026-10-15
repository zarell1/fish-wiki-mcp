# Cloud MCP Worker

This is the read-only, live-data Streamable HTTP MCP endpoint used by ChatGPT and Claude cloud connections. It calls only the official Fischipedia MediaWiki API. For hosts that expose HTTP GET tools but cannot act as MCP clients, the same tools are available as public JSON routes: `/api/status`, `/api/search`, `/api/page`, `/api/table`, `/api/category`, `/api/pages`, and `/api/recent-changes`. They return the tool result directly and support CORS; see the repository's agent guide for parameters and pagination.

The Worker entry point is `worker/index.js`; the Site project and MCP capability are declared in `.openai/hosting.json`. Run `bash scripts/build.sh`, then `node scripts/validate-artifact.mjs` and `node tests/worker.test.mjs` to build and check the deployable artifact.
