# Cloud MCP Worker

This is the read-only, live-data Streamable HTTP MCP endpoint used by ChatGPT and Claude cloud connections. It calls only the official Fischipedia MediaWiki API.

The Worker entry point is `worker/index.js`; the Site project and MCP capability are declared in `.openai/hosting.json`. Run `bash scripts/build.sh`, then `node scripts/validate-artifact.mjs` and `node tests/worker.test.mjs` to build and check the deployable artifact.
