import assert from "node:assert/strict";
import worker from "../worker/index.js";

const apiCalls = [];
globalThis.fetch = async (input) => {
  const url = new URL(input);
  apiCalls.push(url);
  assert.equal(url.hostname, "fischipedia.org");
  if (url.searchParams.get("meta") === "siteinfo") {
    return Response.json({ query: { general: { sitename: "Official Fisch Wiki" }, namespaces: { 0: {}, 1: {} } } });
  }
  if (url.searchParams.get("list") === "categorymembers") {
    return Response.json({ query: { categorymembers: [] }, continue: { continue: "||", cmcontinue: "next" } });
  }
  if (url.searchParams.get("list") === "allpages") return Response.json({ query: { allpages: [] } });
  if (url.searchParams.get("list") === "recentchanges") return Response.json({ query: { recentchanges: [] } });
  if (url.searchParams.get("list") === "search") {
    return Response.json({ query: { searchinfo: { totalhits: 1 }, search: [{ title: "Blue Whale", timestamp: "now", snippet: "Official result" }] } });
  }
  if (url.searchParams.get("action") === "parse" && url.searchParams.get("prop")?.includes("wikitext")) {
    return Response.json({ parse: { title: "Blue Whale", revid: 12, categories: [{ category: "Fish" }], wikitext: "{{FishInfobox}}" } });
  }
  if (url.searchParams.get("action") === "parse") {
    return Response.json({ parse: { title: "Blue Whale", text: "<table><tr><th>Fish</th></tr><tr><td>Blue Whale</td></tr></table>" } });
  }
  return Response.json({ query: {} });
};

const initialized = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25" } }),
}));
assert.equal(initialized.status, 200);
const initialization = await initialized.json();
assert.equal(initialization.result.protocolVersion, "2025-11-25");
assert.match(initialization.result.instructions, /official https:\/\/fischipedia\.org/);

const initializedNotification = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }),
}));
assert.equal(initializedNotification.status, 202);
assert.equal(await initializedNotification.text(), "");
assert.equal((await worker.fetch(new Request("https://example.test/mcp"))).status, 405);
assert.equal((await worker.fetch(new Request("https://example.test/unknown"))).status, 404);

const listing = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }),
}));
assert.equal((await listing.json()).result.tools.length, 7);

const discovery = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json", "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "server/discover" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 20, method: "server/discover", params: { _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } } }),
}));
const discoveryResult = (await discovery.json()).result;
assert.ok(discoveryResult.supportedVersions.includes("2026-07-28"));
assert.equal(discoveryResult.instructions, initialization.result.instructions);
assert.equal(discovery.headers.get("MCP-Protocol-Version"), "2026-07-28");

const modernStatus = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json", "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/call", "Mcp-Name": "wiki_status" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 21, method: "tools/call", params: { name: "wiki_status", arguments: {}, _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } } }),
}));
assert.equal(modernStatus.headers.get("MCP-Protocol-Version"), "2026-07-28");
assert.equal((await modernStatus.json()).result.isError, false);

const headerMismatch = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json", "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tools/call", "Mcp-Name": "wiki_page" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 22, method: "tools/call", params: { name: "wiki_status", arguments: {}, _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } } }),
}));
assert.equal(headerMismatch.status, 400);
assert.equal((await headerMismatch.json()).error.code, -32020);

const badOrigin = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { origin: "https://untrusted.example", "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 23, method: "tools/list" }),
}));
assert.equal(badOrigin.status, 403);

const status = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "wiki_status", arguments: {} } }),
}));
const payload = await status.json();
assert.equal(payload.result.isError, false);
assert.match(payload.result.content[0].text, /Official Fisch Wiki/);
assert.equal(apiCalls.length, 2);

const category = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "wiki_category", arguments: { name: "Fish" } } }),
}));
const token = JSON.parse((await category.json()).result.content[0].text).continue_token;
assert.equal(JSON.parse(token).continue, "||");
assert.equal(JSON.parse(token).cmcontinue, "next");

const nextPage = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 5, method: "tools/call", params: { name: "wiki_category", arguments: { name: "Fish", continue_token: token } } }),
}));
assert.equal((await nextPage.json()).result.isError, false);
const continuationQuery = apiCalls.at(-1).searchParams;
assert.equal(continuationQuery.get("continue"), "||");
assert.equal(continuationQuery.get("cmcontinue"), "next");

const readTool = async (name, args) => {
  const response = await worker.fetch(new Request("https://example.test/mcp", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 30, method: "tools/call", params: { name, arguments: args } }),
  }));
  return JSON.parse((await response.json()).result.content[0].text);
};
const page = await readTool("wiki_page", { title: "Blue Whale" });
assert.equal(page.source_url, "https://fischipedia.org/wiki/Blue_Whale");
assert.equal(page.categories[0], "Fish");
const table = await readTool("wiki_table", { title: "Blue Whale" });
assert.equal(table.table.rows[1][0], "Blue Whale");
const pages = await readTool("wiki_pages", { namespace: 0, limit: 5 });
assert.equal(pages.results.length, 0);
const changes = await readTool("wiki_recent_changes", { limit: 5 });
assert.equal(changes.results.length, 0);

const httpStatus = await worker.fetch(new Request("https://example.test/api/status"));
assert.equal(httpStatus.status, 200);
assert.equal(httpStatus.headers.get("access-control-allow-origin"), "*");
assert.equal((await httpStatus.json()).source, "https://fischipedia.org");
assert.equal(apiCalls.at(-1).hostname, "fischipedia.org");

const httpSearch = await worker.fetch(new Request("https://example.test/api/search?query=Blue%20Whale&limit=5"));
assert.equal(httpSearch.status, 200);
assert.equal(apiCalls.at(-1).searchParams.get("srsearch"), "Blue Whale");
assert.equal(apiCalls.at(-1).searchParams.get("srlimit"), "5");

const invalidHttpQuery = await worker.fetch(new Request("https://example.test/api/search?query=test&limit=500"));
assert.equal(invalidHttpQuery.status, 400);
const preflight = await worker.fetch(new Request("https://example.test/api/page", { method: "OPTIONS" }));
assert.equal(preflight.status, 204);
assert.equal(preflight.headers.get("access-control-allow-methods"), "GET, OPTIONS");
console.log("Cloud MCP and HTTP API routes, validation, CORS, and official-domain calls passed");
