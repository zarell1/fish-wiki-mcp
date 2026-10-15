const API_URLS = [
  "https://fischipedia.org/w/api.php",
  "https://fischipedia.org/api.php",
];
const SERVER_INFO = { name: "fish-wiki-mcp", version: "1.0.0" };
const PROTOCOLS = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"];
const TOOLS = [
  tool("wiki_status", "Check live access to the official Fischipedia API and data limits."),
  tool("wiki_search", "Search page titles and text on the official Fischipedia.", { query: string(), limit: integer(20, 1, 50) }),
  tool("wiki_page", "Read official page wikitext and categories. Cite the returned source_url.", { title: string(), max_chars: integer(12000, 1, 30000) }),
  tool("wiki_table", "Read one table from an official wiki page as extracted cell text.", { title: string(), index: integer(0, 0, 100) }),
  tool("wiki_category", "List official category members; use continue_token to paginate.", { name: string(), limit: integer(100, 1, 500), continue_token: optionalString() }),
  tool("wiki_pages", "List official wiki pages; use continue_token to paginate.", { namespace: { type: "integer" }, prefix: optionalString(), limit: integer(100, 1, 500), continue_token: optionalString() }),
  tool("wiki_recent_changes", "List recent edits on the official wiki.", { limit: integer(20, 1, 100) }),
];

function tool(name, description, properties = {}) {
  return {
    name, description,
    inputSchema: {
      type: "object", properties,
      required: Object.entries(properties).filter(([, v]) => v.required).map(([k]) => k),
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: true },
  };
}
function string() { return { type: "string", required: true }; }
function optionalString() { return { type: "string" }; }
function integer(defaultValue, minimum, maximum) {
  return { type: "integer", default: defaultValue, minimum, maximum };
}

function response(id, result, protocolVersion) {
  return json({ jsonrpc: "2.0", id, result }, 200, protocolVersion);
}
function json(value, status = 200, protocolVersion = "2025-11-25") {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "MCP-Protocol-Version": protocolVersion,
    },
  });
}
function rpcError(id, code, message) {
  return json({ jsonrpc: "2.0", id, error: { code, message } });
}
function textResult(value, isError = false) {
  return { content: [{ type: "text", text: JSON.stringify(value) }], isError };
}
function pageUrl(title) {
  return `https://fischipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}
function decodeHtml(text) {
  return text.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (_, entity) => {
    if (entity[0] === "#") {
      const hex = entity[1]?.toLowerCase() === "x";
      const value = Number.parseInt(entity.slice(hex ? 2 : 1), hex ? 16 : 10);
      return Number.isFinite(value) ? String.fromCodePoint(value) : "";
    }
    return ({ amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " })[entity.toLowerCase()];
  });
}
function htmlText(html) {
  return decodeHtml(html.replace(/<br\s*\/?>/gi, " ")
    .replace(/<\/(?:p|li|tr|h[1-6])\s*>/gi, "\n")
    .replace(/<[^>]*>/g, " ").replace(/[\t ]+/g, " ")
    .replace(/ *\n */g, "\n").trim());
}

async function mw(params) {
  const query = new URLSearchParams({ format: "json", formatversion: "2", ...params });
  let lastError;
  for (const endpoint of API_URLS) {
    try {
      const response = await fetch(`${endpoint}?${query}`, {
        headers: { accept: "application/json", "user-agent": "FishWikiMCP/1.0 (https://github.com/zarell1/fish-wiki-mcp)" },
        signal: AbortSignal.timeout(15000),
      });
      if (!response.ok) throw new Error(`Official MediaWiki API returned HTTP ${response.status}`);
      const data = await response.json();
      if (data.error) throw new Error(`MediaWiki API error: ${data.error.info || data.error.code}`);
      return { data, endpoint };
    } catch (error) {
      lastError = error;
    }
  }
  throw new Error(`Could not read the official Fischipedia API: ${lastError?.message || "request failed"}`);
}

async function callTool(name, args) {
  if (name === "wiki_status") {
    const { data, endpoint } = await mw({ action: "query", meta: "siteinfo", siprop: "general|namespaces" });
    return {
      source: "https://fischipedia.org", endpoint,
      site_name: data.query.general.sitename,
      namespaces: Object.keys(data.query.namespaces).length,
      mode: "live MediaWiki API; no local database or scheduled artifact required",
      complete: false,
      note: "Search and listing tools return paginated results, not a complete mirrored index.",
      checked_at: new Date().toISOString(),
    };
  }
  if (name === "wiki_search") {
    const query = requiredString(args.query, "query");
    const limit = boundedInt(args.limit, 20, 1, 50);
    const { data } = await mw({ action: "query", list: "search", srsearch: query, srlimit: String(limit), srprop: "snippet|timestamp" });
    const results = data.query.search.map(page => ({
      title: page.title, timestamp: page.timestamp, snippet: htmlText(page.snippet).slice(0, 800),
      source_url: pageUrl(page.title),
    }));
    return { query, total: data.query.searchinfo.totalhits, results, continue_token: continuation(data.continue) };
  }
  if (name === "wiki_page") {
    const title = requiredString(args.title, "title");
    const maxChars = boundedInt(args.max_chars, 12000, 1, 30000);
    const { data } = await mw({ action: "parse", page: title, prop: "wikitext|categories", disablelimitreport: "1" });
    const page = data.parse;
    return {
      title: page.title, source_url: pageUrl(page.title), revision_id: page.revid,
      categories: (page.categories || []).map(category => category.category),
      wikitext: page.wikitext.slice(0, maxChars),
      has_more: page.wikitext.length > maxChars,
    };
  }
  if (name === "wiki_table") {
    const title = requiredString(args.title, "title");
    const index = boundedInt(args.index, 0, 0, 100);
    const { data } = await mw({ action: "parse", page: title, prop: "text", disablelimitreport: "1" });
    const html = data.parse.text;
    const tables = [...html.matchAll(/<table\b[^>]*>[\s\S]*?<\/table>/gi)].map((match, tableIndex) => ({
      index: tableIndex,
      rows: [...match[0].matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)].map(row =>
        [...row[1].matchAll(/<(?:th|td)\b[^>]*>([\s\S]*?)<\/(?:th|td)>/gi)].map(cell => htmlText(cell[1])))
        .filter(row => row.length),
    }));
    if (!tables[index]) throw new Error(`Table ${index} was not found on ${title}`);
    return { title, source_url: pageUrl(data.parse.title), table: tables[index] };
  }
  if (name === "wiki_category") {
    const category = requiredString(args.name, "name").replace(/^Category:/i, "").replaceAll(" ", "_");
    const limit = boundedInt(args.limit, 100, 1, 500);
    const params = { action: "query", list: "categorymembers", cmtitle: `Category:${category}`, cmtype: "page", cmlimit: String(limit) };
    applyContinuation(params, args.continue_token);
    const { data } = await mw(params);
    return {
      category: category.replaceAll("_", " "),
      results: data.query.categorymembers.map(page => ({ title: page.title, source_url: pageUrl(page.title) })),
      continue_token: continuation(data.continue),
    };
  }
  if (name === "wiki_pages") {
    const limit = boundedInt(args.limit, 100, 1, 500);
    const params = { action: "query", list: "allpages", aplimit: String(limit) };
    if (Number.isInteger(args.namespace)) params.apnamespace = String(args.namespace);
    if (args.prefix) params.apprefix = requiredString(args.prefix, "prefix");
    applyContinuation(params, args.continue_token);
    const { data } = await mw(params);
    return {
      results: data.query.allpages.map(page => ({ title: page.title, namespace: page.ns, source_url: pageUrl(page.title) })),
      continue_token: continuation(data.continue),
    };
  }
  if (name === "wiki_recent_changes") {
    const limit = boundedInt(args.limit, 20, 1, 100);
    const { data } = await mw({ action: "query", list: "recentchanges", rclimit: String(limit), rcprop: "title|ids|timestamp|comment", rctype: "edit|new" });
    return { results: data.query.recentchanges.map(change => ({
      title: change.title, timestamp: change.timestamp, comment: change.comment,
      revision_id: change.revid, source_url: pageUrl(change.title),
    })) };
  }
  throw new Error(`Unknown tool: ${name}`);
}

function requiredString(value, name) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${name} must be a non-empty string`);
  return value.trim();
}
function boundedInt(value, fallback, min, max) {
  if (value === undefined) return fallback;
  if (!Number.isInteger(value) || value < min || value > max) throw new Error(`integer must be between ${min} and ${max}`);
  return value;
}
function continuation(value) { return value ? JSON.stringify(value) : null; }
function applyContinuation(params, token) {
  if (token === undefined || token === null || token === "") return;
  let values;
  try { values = JSON.parse(requiredString(token, "continue_token")); }
  catch { throw new Error("continue_token must be copied unchanged from the previous result"); }
  const allowed = new Set(["continue", "sroffset", "cmcontinue", "apcontinue"]);
  if (!values || typeof values !== "object" || Array.isArray(values) ||
      Object.keys(values).some(key => !allowed.has(key)) ||
      Object.values(values).some(value => typeof value !== "string" || value.length > 256)) {
    throw new Error("continue_token is invalid; copy it from the previous result");
  }
  Object.assign(params, values);
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/") {
      return new Response("Fisch Wiki MCP · Official source: https://fischipedia.org · MCP endpoint: /mcp", {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }
    if (url.pathname !== "/mcp") return new Response("Not found", { status: 404 });
    if (request.method === "GET") return new Response("MCP Streamable HTTP endpoint; send JSON-RPC POST requests.", { status: 405, headers: { allow: "POST" } });
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405, headers: { allow: "POST" } });

    let message;
    try { message = await request.json(); }
    catch { return rpcError(null, -32700, "Invalid JSON"); }
    if (!message || message.jsonrpc !== "2.0" || typeof message.method !== "string") {
      return rpcError(message?.id ?? null, -32600, "Invalid JSON-RPC request");
    }
    if (!("id" in message)) return new Response(null, { status: 202 });

    const protocol = PROTOCOLS.includes(message.params?.protocolVersion) ? message.params.protocolVersion : "2025-11-25";
    if (message.method === "initialize") {
      return response(message.id, {
        protocolVersion: protocol,
        capabilities: { tools: { listChanged: false } },
        serverInfo: SERVER_INFO,
      }, protocol);
    }
    if (message.method === "ping") return response(message.id, {}, protocol);
    if (message.method === "server/discover") {
      return response(message.id, { supportedVersions: PROTOCOLS, capabilities: { tools: {} }, serverInfo: SERVER_INFO }, protocol);
    }
    if (message.method === "tools/list") return response(message.id, { tools: TOOLS }, protocol);
    if (message.method === "tools/call") {
      const name = message.params?.name;
      try {
        const result = await callTool(name, message.params?.arguments || {});
        return response(message.id, textResult(result), protocol);
      } catch (error) {
        return response(message.id, textResult({ error: error.message }, true), protocol);
      }
    }
    return rpcError(message.id, -32601, `Method not found: ${message.method}`);
  },
};
