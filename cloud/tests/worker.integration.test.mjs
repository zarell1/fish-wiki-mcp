import assert from "node:assert/strict";
import worker from "../worker/index.js";

let id = 0;
async function rpc(method, params = {}) {
  const body = {
    jsonrpc: "2.0",
    id: ++id,
    method,
    params: { ...params, _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28" } },
  };
  const headers = {
    accept: "application/json, text/event-stream",
    "content-type": "application/json",
    "MCP-Protocol-Version": "2026-07-28",
    "Mcp-Method": method,
  };
  if (method === "tools/call") headers["Mcp-Name"] = params.name;
  const response = await worker.fetch(new Request("https://local.test/mcp", {
    method: "POST", headers, body: JSON.stringify(body),
  }));
  assert.equal(response.status, 200, `${method} returned HTTP ${response.status}`);
  assert.equal(response.headers.get("MCP-Protocol-Version"), "2026-07-28");
  const payload = await response.json();
  assert.equal(payload.jsonrpc, "2.0");
  assert.equal(payload.id, body.id);
  return payload.result;
}

const discovered = await rpc("server/discover");
assert.ok(discovered.supportedVersions.includes("2026-07-28"));
const listed = await rpc("tools/list");
const expectedTools = ["wiki_status", "wiki_search", "wiki_page", "wiki_table", "wiki_category", "wiki_pages", "wiki_recent_changes"];
assert.deepEqual(listed.tools.map(tool => tool.name), expectedTools);

const cases = [
  ["wiki_status", {}],
  ["wiki_search", { query: "Bestiary", limit: 5 }],
  ["wiki_page", { title: "Napoleonfish", max_chars: 1000 }],
  ["wiki_table", { title: "Napoleonfish", index: 0 }],
  ["wiki_category", { name: "Fish", limit: 2 }],
  ["wiki_pages", { namespace: 0, limit: 2 }],
  ["wiki_recent_changes", { limit: 2 }],
];
const failures = [];
for (const [name, arguments_] of cases) {
  try {
    let result = await rpc("tools/call", { name, arguments: arguments_ });
    if (result.isError && result.content?.[0]?.text.includes("Could not read the official Fischipedia API")) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      result = await rpc("tools/call", { name, arguments: arguments_ });
    }
    if (result.isError) throw new Error(result.content?.[0]?.text || "tool returned isError");
    const value = JSON.parse(result.content[0].text);
    if (value.source_url) assert.match(value.source_url, /^https:\/\/fischipedia\.org\//);
    for (const item of value.results || []) {
      if (item.source_url) assert.match(item.source_url, /^https:\/\/fischipedia\.org\//);
    }
    if (value.continue_token) {
      const pageTwo = await rpc("tools/call", { name, arguments: { ...arguments_, continue_token: value.continue_token } });
      if (pageTwo.isError) throw new Error(`pagination: ${pageTwo.content?.[0]?.text}`);
    }
    console.log(`${name}: passed`);
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
    console.error(`${name}: failed: ${error.message}`);
  }
}

if (failures.length) throw new Error(`${failures.length}/${cases.length} live tool checks failed`);
console.log("Live MCP integration passed against the official Fischipedia API for all seven tools");
