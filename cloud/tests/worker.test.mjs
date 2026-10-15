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

const listing = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }),
}));
assert.equal((await listing.json()).result.tools.length, 7);

const discovery = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 20, method: "server/discover" }),
}));
const discoveryResult = (await discovery.json()).result;
assert.ok(discoveryResult.supportedVersions.includes("2026-07-28"));
assert.equal(discoveryResult.instructions, initialization.result.instructions);

const status = await worker.fetch(new Request("https://example.test/mcp", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "wiki_status", arguments: {} } }),
}));
const payload = await status.json();
assert.equal(payload.result.isError, false);
assert.match(payload.result.content[0].text, /Official Fisch Wiki/);
assert.equal(apiCalls.length, 1);

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
console.log("Cloud MCP protocol, tool listing, and official-domain status call passed");
