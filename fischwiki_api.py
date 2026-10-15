"""Local, read-only MediaWiki mirror and evidence API for fischipedia.org.

No external API accessibility is assumed: run `python fischwiki_api.py probe` first.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from fastapi import FastAPI, HTTPException, Query

BASE = "https://fischipedia.org"
API_CANDIDATES = [f"{BASE}/w/api.php", f"{BASE}/api.php"]
DB = Path(os.environ.get("FISCHWIKI_DB", str(Path(__file__).with_name("fischwiki.sqlite3"))))
USER_AGENT = os.environ.get("FISCHWIKI_USER_AGENT", "FischWikiReader/1.0 (personal noncommercial wiki indexing)")
DELAY = float(os.environ.get("FISCHWIKI_DELAY", "0.8"))
TIMEOUT = float(os.environ.get("FISCHWIKI_TIMEOUT", "35"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def page_url(title: str) -> str:
    return BASE + "/wiki/" + quote(title.replace(" ", "_"), safe="/:()")


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS inventory (
        page_id INTEGER PRIMARY KEY, ns INTEGER NOT NULL,
        title TEXT NOT NULL, seen_run TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS ix_inventory_ns_title ON inventory(ns,title);
      CREATE TABLE IF NOT EXISTS pages (
        page_id INTEGER PRIMARY KEY, ns INTEGER NOT NULL, title TEXT NOT NULL,
        url TEXT NOT NULL, revid INTEGER, fetched_at TEXT NOT NULL,
        rendered_text TEXT NOT NULL, html TEXT NOT NULL, wikitext TEXT NOT NULL,
        categories_json TEXT NOT NULL, tables_json TEXT NOT NULL,
        links_json TEXT NOT NULL, images_json TEXT NOT NULL DEFAULT '[]',
        FOREIGN KEY(page_id) REFERENCES inventory(page_id) ON DELETE CASCADE
      );
      CREATE UNIQUE INDEX IF NOT EXISTS ix_pages_title ON pages(title);
      CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER NOT NULL, section TEXT NOT NULL, anchor TEXT NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY(page_id) REFERENCES inventory(page_id) ON DELETE CASCADE
      );
      CREATE INDEX IF NOT EXISTS ix_chunks_page ON chunks(page_id);
      CREATE VIRTUAL TABLE IF NOT EXISTS chunk_search USING fts5(
        page_title, section, content, page_id UNINDEXED, chunk_id UNINDEXED,
        tokenize='unicode61 remove_diacritics 2'
      );
      CREATE TABLE IF NOT EXISTS category_members (
        category TEXT NOT NULL, page_id INTEGER NOT NULL,
        PRIMARY KEY(category,page_id),
        FOREIGN KEY(page_id) REFERENCES inventory(page_id) ON DELETE CASCADE
      );
      CREATE TABLE IF NOT EXISTS failed_pages (
        page_id INTEGER PRIMARY KEY, title TEXT NOT NULL,
        error TEXT NOT NULL, failed_at TEXT NOT NULL,
        FOREIGN KEY(page_id) REFERENCES inventory(page_id) ON DELETE CASCADE
      );
      CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY, value TEXT NOT NULL
      );
    """)
    return db


def set_meta(db: sqlite3.Connection, key: str, value: Any) -> None:
    db.execute("INSERT INTO metadata(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))


def get_meta(db: sqlite3.Connection, key: str) -> Any:
    row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


class WikiClient:
    def __init__(self) -> None:
        self.client = httpx.Client(
            follow_redirects=True, timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        self.endpoint: str | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.client.close()

    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        data = {"format": "json", "formatversion": "2", **params}
        for attempt in range(5):
            if DELAY:
                time.sleep(DELAY)
            try:
                res = self.client.get(url, params=data)
                if res.status_code in (429, 502, 503, 504):
                    retry_after = res.headers.get("Retry-After", "")
                    pause = min(60., float(retry_after)) if retry_after.isdigit() else min(60., 2 ** attempt)
                    time.sleep(pause)
                    continue
                res.raise_for_status()
                payload = res.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("MediaWiki returned non-JSON-object payload")
                if "error" in payload:
                    raise RuntimeError(f"MediaWiki API error: {payload['error']}")
                return payload
            except (httpx.TransportError, ValueError) as exc:
                if attempt == 4:
                    raise RuntimeError(f"Network/JSON error: {exc}") from exc
                time.sleep(min(60., 2 ** attempt))
        raise RuntimeError(f"API endpoint unavailable: {url}")

    def probe(self) -> tuple[str, dict[str, Any]]:
        failures = []
        for candidate in API_CANDIDATES:
            try:
                response = self._request(candidate, {
                    "action": "query", "meta": "siteinfo", "siprop": "general|namespaces"
                })
                site = response.get("query", {})
                if isinstance(site.get("namespaces"), dict):
                    self.endpoint = candidate
                    return candidate, site
                failures.append(f"{candidate}: no namespaces in response")
            except Exception as exc:
                failures.append(f"{candidate}: {exc}")
        raise RuntimeError("Could not verify a functioning MediaWiki endpoint:\n" + "\n".join(failures))

    def call(self, **params: Any) -> dict[str, Any]:
        if not self.endpoint:
            self.probe()
        return self._request(self.endpoint, params)  # type: ignore[arg-type]

    def allpages(self, ns: int):
        cont = {}
        while True:
            response = self.call(action="query", list="allpages", aplimit="max", apnamespace=ns, **cont)
            for page in response.get("query", {}).get("allpages", []):
                if "pageid" in page:
                    yield {"page_id": int(page["pageid"]), "ns": int(page["ns"]), "title": page["title"]}
            cont = response.get("continue", {})
            if not cont:
                break

    def lastrevids(self, pageids: list[int]) -> dict[int, int | None]:
        response = self.call(action="query", prop="info", pageids="|".join(map(str, pageids)))
        return {int(p["pageid"]): p.get("lastrevid") for p in response.get("query", {}).get("pages", []) if "pageid" in p}

    def parse(self, title: str) -> dict[str, Any]:
        response = self.call(action="parse", page=title, prop="text|wikitext|revid|categories", disablelimitreport=1)
        if "parse" not in response:
            raise RuntimeError("No parse result")
        return response["parse"]


def string_field(v: Any) -> str:
    if isinstance(v, str):
        return v
    return v.get("*", "") if isinstance(v, dict) else ""


def parsed_page(parsed: dict[str, Any], title: str) -> dict[str, Any]:
    html = string_field(parsed.get("text"))
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".mw-parser-output") or soup
    for bad in root.select("script, style, noscript, .mw-editsection, .reference, .mw-cite-backlink"):
        bad.decompose()
    clean_text = root.get_text(" ", strip=True)
    tables = []
    for table in root.select("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            rows.append([{
                "text": cell.get_text(" ", strip=True),
                "type": cell.name,
                "rowspan": int(cell.get("rowspan", 1)) if str(cell.get("rowspan", 1)).isdigit() else 1,
                "colspan": int(cell.get("colspan", 1)) if str(cell.get("colspan", 1)).isdigit() else 1,
            } for cell in cells])
        if rows:
            tables.append({"index": len(tables), "caption": table.caption.get_text(" ", strip=True) if table.caption else "", "rows": rows})
    cats = []
    for v in parsed.get("categories", []):
        value = v if isinstance(v, str) else v.get("*", "")
        if value:
            cats.append(value.replace("_", " "))
    cats = list(dict.fromkeys(cats))
    links = []
    for a in root.select("a[href]"):
        href = a.get("href", "")
        if href.startswith("/wiki/") or href.startswith(BASE + "/wiki/"):
            links.append({"title": a.get_text(" ", strip=True), "url": urljoin(BASE, href)})
    links = list({x["url"]: x for x in links}.values())
    images = []
    for img in root.select("img[src]"):
        url = urljoin(BASE, img.get("src", ""))
        images.append({"url": url, "alt": img.get("alt", ""), "title": img.get("title", "")})
    images = list({x["url"]: x for x in images}.values())

    sections = []
    current_section = "Introduction"
    current_anchor = ""
    buffer = []
    length = 0

    def flush():
        nonlocal buffer, length
        text = "\n".join(buffer).strip()
        if text:
            sections.append((current_section, current_anchor, text))
        buffer = []
        length = 0

    for element in root.find_all(["h2", "h3", "h4", "h5", "h6", "p", "li", "tr", "dt", "dd", "pre", "blockquote"]):
        if element.name.startswith("h") and element.name[1:].isdigit():
            flush()
            current_section = element.get_text(" ", strip=True) or current_section
            headline = element.select_one(".mw-headline[id]")
            current_anchor = (headline.get("id") if headline else element.get("id")) or ""
            continue
        if element.find_parent(["p", "li", "tr", "dt", "dd", "pre", "blockquote"]):
            continue
        line = element.get_text(" ", strip=True)
        if not line:
            continue
        if len(line) > 1800:
            flush()
            for start in range(0, len(line), 1600):
                sections.append((current_section, current_anchor, line[start:start + 1600]))
        else:
            if length + len(line) > 1800:
                flush()
            buffer.append(line)
            length += len(line) + 1
    flush()
    if not sections and clean_text:
        sections = [("Introduction", "", clean_text[i:i + 1600]) for i in range(0, len(clean_text), 1600)]
    return {
        "rendered_text": clean_text, "html": html,
        "wikitext": string_field(parsed.get("wikitext")),
        "tables": tables, "categories": cats, "links": links, "images": images,
        "sections": sections,
        "revid": parsed.get("revid"), "title": title,
    }


def save_page(db: sqlite3.Connection, page: dict[str, Any], parsed: dict[str, Any]) -> None:
    obj = parsed_page(parsed, page["title"])
    pid = page["page_id"]
    db.execute("DELETE FROM chunk_search WHERE page_id=?", (pid,))
    db.execute("DELETE FROM chunks WHERE page_id=?", (pid,))
    db.execute("DELETE FROM category_members WHERE page_id=?", (pid,))
    db.execute("""INSERT INTO pages(page_id,ns,title,url,revid,fetched_at,rendered_text,html,wikitext,categories_json,tables_json,links_json,images_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(page_id) DO UPDATE SET
        ns=excluded.ns,title=excluded.title,url=excluded.url,revid=excluded.revid,
        fetched_at=excluded.fetched_at,rendered_text=excluded.rendered_text,
        html=excluded.html,wikitext=excluded.wikitext,categories_json=excluded.categories_json,
        tables_json=excluded.tables_json,links_json=excluded.links_json,images_json=excluded.images_json""", (
        pid, page["ns"], page["title"], page_url(page["title"]), obj["revid"], utc_now(),
        obj["rendered_text"], obj["html"], obj["wikitext"],
        json.dumps(obj["categories"], ensure_ascii=False),
        json.dumps(obj["tables"], ensure_ascii=False),
        json.dumps(obj["links"], ensure_ascii=False),
        json.dumps(obj["images"], ensure_ascii=False),
    ))
    for section, anchor, content in obj["sections"]:
        cur = db.execute("INSERT INTO chunks(page_id,section,anchor,content) VALUES(?,?,?,?)", (pid, section, anchor, content))
        db.execute("INSERT INTO chunk_search(page_title,section,content,page_id,chunk_id) VALUES(?,?,?,?,?)",
                   (page["title"], section, content, pid, cur.lastrowid))
    for cat in obj["categories"]:
        db.execute("INSERT OR IGNORE INTO category_members(category,page_id) VALUES(?,?)", (cat, pid))
    db.execute("DELETE FROM failed_pages WHERE page_id=?", (pid,))


def sync() -> dict[str, Any]:
    db = connect()
    run = uuid.uuid4().hex
    errors = []
    with WikiClient() as wiki:
        endpoint, site = wiki.probe()
        namespaces = sorted(int(k) for k in site["namespaces"].keys() if int(k) >= 0)
        set_meta(db, "api_endpoint", endpoint)
        set_meta(db, "last_sync_started", utc_now())
        set_meta(db, "inventory_complete", False)
        db.commit()
        # Enumerate the entire API-visible public page inventory.
        for ns in namespaces:
            try:
                n = 0
                for page in wiki.allpages(ns):
                    db.execute("INSERT INTO inventory(page_id,ns,title,seen_run) VALUES (?,?,?,?) "
                               "ON CONFLICT(page_id) DO UPDATE SET ns=excluded.ns,title=excluded.title,seen_run=excluded.seen_run",
                               (page["page_id"], ns, page["title"], run))
                    n += 1
                    if n % 500 == 0:
                        db.commit()
                db.commit()
                print(f"namespace {ns}: {n} pages", flush=True)
            except Exception as exc:
                errors.append({"namespace": ns, "error": str(exc)})
                print(f"namespace {ns} inventory failed: {exc}", file=sys.stderr)
        inventory_complete = not errors
        if inventory_complete:
            stale_ids = [r[0] for r in db.execute("SELECT page_id FROM inventory WHERE seen_run != ?", (run,))]
            if stale_ids:
                for old_id in stale_ids:
                    db.execute("DELETE FROM chunk_search WHERE page_id=?", (old_id,))
                    db.execute("DELETE FROM inventory WHERE page_id=?", (old_id,))
                db.commit()
        set_meta(db, "inventory_complete", inventory_complete)
        set_meta(db, "last_inventory_error", errors)
        db.commit()

        # Revision-check batches so repeated syncs download only changed pages.
        to_fetch = db.execute("SELECT page_id,ns,title FROM inventory WHERE seen_run=? ORDER BY page_id", (run,)).fetchall()
        processed = 0
        for start in range(0, len(to_fetch), 50):
            batch = to_fetch[start:start + 50]
            ids = [int(p["page_id"]) for p in batch]
            try:
                revisions = wiki.lastrevids(ids)
            except Exception as exc:
                print(f"revision-check failure ({ids[0]}...): {exc}", file=sys.stderr)
                revisions = {}
            for page in batch:
                pid = page["page_id"]
                prior = db.execute("SELECT revid FROM pages WHERE page_id=?", (pid,)).fetchone()
                remote_revision = revisions.get(pid)
                if prior and remote_revision and prior["revid"] == remote_revision:
                    db.execute("DELETE FROM failed_pages WHERE page_id=?", (pid,))
                    processed += 1
                    continue
                try:
                    parsed = wiki.parse(page["title"])
                    save_page(db, dict(page), parsed)
                except Exception as exc:
                    db.execute("INSERT INTO failed_pages(page_id,title,error,failed_at) VALUES(?,?,?,?) "
                               "ON CONFLICT(page_id) DO UPDATE SET error=excluded.error,failed_at=excluded.failed_at,title=excluded.title",
                               (pid, page["title"], str(exc), utc_now()))
                    print(f"FAIL page {page['title']}: {exc}", file=sys.stderr)
                processed += 1
                if processed % 25 == 0:
                    db.commit()
                    print(f"processed {processed}/{len(to_fetch)}", flush=True)
            db.commit()

        set_meta(db, "last_sync_finished", utc_now())
        db.commit()
    result = coverage(db)
    db.close()
    return result


def coverage(db: sqlite3.Connection) -> dict[str, Any]:
    discovered = db.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    indexed = db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    failures = db.execute("SELECT COUNT(*) FROM failed_pages").fetchone()[0]
    with_chunks = db.execute("SELECT COUNT(DISTINCT page_id) FROM chunks").fetchone()[0]
    inventory_complete = bool(get_meta(db, "inventory_complete"))
    return {
        "source": BASE, "discovered": discovered, "indexed": indexed,
        "index_coverage": round(indexed / discovered, 6) if discovered else 0,
        "pages_with_searchable_text": with_chunks,
        "failed_pages": failures,
        "inventory_complete": inventory_complete,
        "complete": bool(discovered and inventory_complete and indexed == discovered and failures == 0),
        "last_sync_started": get_meta(db, "last_sync_started"),
        "last_sync_finished": get_meta(db, "last_sync_finished"),
        "api_endpoint": get_meta(db, "api_endpoint"),
        "inventory_errors": get_meta(db, "last_inventory_error"),
        "note": "complete means all enumerated API-visible pages are indexed, not every dynamic/hidden website resource",
    }


app = FastAPI(title="Fisch Wiki Evidence API", version="1.0.0", description="Read-only full-wiki index; never fills unknown fields with guesses.")


@app.get("/api/status")
def get_status():
    db = connect()
    try:
        return coverage(db)
    finally:
        db.close()


@app.get("/api/pages")
def list_pages(namespace: int | None = None, prefix: str = "", limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    db = connect()
    try:
        where = "WHERE 1=1"
        args = []
        if namespace is not None:
            where += " AND ns=?"
            args.append(namespace)
        if prefix:
            where += " AND title LIKE ? ESCAPE '\\'"
            args.append(prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        total = db.execute("SELECT COUNT(*) FROM inventory " + where, args).fetchone()[0]
        items = [dict(r) for r in db.execute("SELECT page_id,ns,title FROM inventory " + where + " ORDER BY title LIMIT ? OFFSET ?", (*args, limit, offset))]
        return {"total": total, "offset": offset, "limit": limit,
                "results": [{**r, "url": page_url(r["title"])} for r in items]}
    finally:
        db.close()


@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    tokens = re.findall(r"[^\W_]+", q, flags=re.UNICODE)
    if not tokens:
        return {"query": q, "total": 0, "results": [], "note": "No indexable terms"}
    match = " OR ".join('"' + tok.replace('"', '""') + '"' for tok in tokens[:15])
    db = connect()
    try:
        total = db.execute("SELECT COUNT(*) FROM chunk_search WHERE chunk_search MATCH ?", (match,)).fetchone()[0]
        rows = db.execute("""SELECT p.title, p.url, p.revid, c.section, c.anchor,
                     c.content, bm25(chunk_search) AS rank
                     FROM chunk_search JOIN chunks AS c ON c.id = CAST(chunk_search.chunk_id AS INTEGER)
                     JOIN pages AS p ON p.page_id=c.page_id
                     WHERE chunk_search MATCH ? ORDER BY rank LIMIT ? OFFSET ?""", (match, limit, offset)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["source_url"] = d.pop("url") + ("#" + quote(d["anchor"]) if d["anchor"] else "")
            d["excerpt"] = d.pop("content")[:1900]
            d.pop("anchor")
            out.append(d)
        return {"query": q, "match_mode": "OR of query terms; filter results for relevance", "total": total,
                "offset": offset, "limit": limit, "results": out}
    except sqlite3.OperationalError as exc:
        raise HTTPException(503, detail=f"Search index error: {exc}") from exc
    finally:
        db.close()


@app.get("/api/category")
def category(name: str, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    name = name.removeprefix("Category:").replace("_", " ")
    db = connect()
    try:
        total = db.execute("SELECT COUNT(*) FROM category_members WHERE category=? COLLATE NOCASE", (name,)).fetchone()[0]
        rows = db.execute("""SELECT p.title,p.url,p.ns,p.revid FROM category_members AS cm
                 JOIN pages p ON p.page_id=cm.page_id
                 WHERE cm.category=? COLLATE NOCASE ORDER BY p.title LIMIT ? OFFSET ?""", (name,limit,offset)).fetchall()
        return {"category": name, "total": total, "offset": offset, "limit": limit, "results": [dict(r) for r in rows]}
    finally:
        db.close()


@app.get("/api/page")
def get_page(title: str, offset: int = Query(0, ge=0), max_chars: int = Query(12000, ge=1, le=100000),
             include_tables: bool = True, include_links: bool = False, include_images: bool = False, include_raw: bool = False):
    db = connect()
    try:
        r = db.execute("SELECT * FROM pages WHERE title=? COLLATE NOCASE", (title.replace("_", " "),)).fetchone()
        if not r:
            raise HTTPException(404, "Page not found in local index (check status and exact title)")
        raw = dict(r)
        result = {
            "title": raw["title"], "url": raw["url"], "namespace": raw["ns"],
            "revid": raw["revid"], "fetched_at": raw["fetched_at"],
            "text_offset": offset, "text_total_chars": len(raw["rendered_text"]),
            "text": raw["rendered_text"][offset:offset + max_chars],
            "text_has_more": offset + max_chars < len(raw["rendered_text"]),
            "categories": json.loads(raw["categories_json"]),
            "source": raw["url"],
        }
        if include_tables:
            result["tables"] = json.loads(raw["tables_json"])
        if include_links:
            result["links"] = json.loads(raw["links_json"])
        if include_images:
            result["images"] = json.loads(raw["images_json"])
        if include_raw:
            result["html"] = raw["html"]
            result["wikitext"] = raw["wikitext"]
        return result
    finally:
        db.close()


@app.get("/api/table")
def get_table(title: str, index: int = Query(0, ge=0)):
    db = connect()
    try:
        r = db.execute("SELECT title,url,tables_json FROM pages WHERE title=? COLLATE NOCASE", (title.replace("_", " "),)).fetchone()
        if not r:
            raise HTTPException(404, "Page not found")
        tables = json.loads(r["tables_json"])
        if index >= len(tables):
            raise HTTPException(404, "Table index out of range")
        return {"title": r["title"], "source_url": r["url"], "table": tables[index]}
    finally:
        db.close()


@app.get("/api/failed")
def failures(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    db = connect()
    try:
        total = db.execute("SELECT COUNT(*) FROM failed_pages").fetchone()[0]
        rows = db.execute("SELECT page_id,title,error,failed_at FROM failed_pages ORDER BY title LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return {"total": total, "results": [dict(r) for r in rows]}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["probe", "sync", "serve", "status"])
    args = parser.parse_args()
    if args.command == "probe":
        with WikiClient() as wiki:
            ep, info = wiki.probe()
            print(json.dumps({"endpoint": ep, "sitename": info.get("general", {}).get("sitename"),
                              "namespaces": len(info.get("namespaces", {}))}, indent=2, ensure_ascii=False))
    elif args.command == "sync":
        print(json.dumps(sync(), indent=2, ensure_ascii=False))
    elif args.command == "status":
        db = connect()
        try:
            print(json.dumps(coverage(db), indent=2, ensure_ascii=False))
        finally:
            db.close()
    else:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8765)
