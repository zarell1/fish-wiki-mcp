import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fischwiki_api as wiki
from fischwiki_mcp import mcp
from fastapi.testclient import TestClient


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.db_patch = patch.object(wiki, "DB", self.db_path)
        self.db_patch.start()
        db = wiki.connect()
        wiki.set_meta(db, "inventory_complete", True)
        db.execute("INSERT INTO inventory VALUES (1,0,'Rod','test')")
        db.execute("""INSERT INTO pages(page_id,ns,title,url,revid,fetched_at,rendered_text,html,wikitext,
                     categories_json,tables_json,links_json,images_json)
                     VALUES(1,0,'Rod','https://fischipedia.org/wiki/Rod',2,'now','Test rod page','',
                     '',?,?,?,?)""", (json.dumps(["Fishing rods"]), json.dumps([]), json.dumps([]), json.dumps([])))
        chunk = db.execute("INSERT INTO chunks(page_id,section,anchor,content) VALUES(1,'Overview','','Test rod page')").lastrowid
        db.execute("INSERT INTO chunk_search(page_title,section,content,page_id,chunk_id) VALUES('Rod','Overview','Test rod page',1,?)", (chunk,))
        db.execute("INSERT INTO category_members VALUES('Fishing rods',1)")
        db.commit()
        db.close()
        self.client = TestClient(wiki.app)

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_status_search_page_and_category(self):
        self.assertTrue(self.client.get("/api/status").json()["complete"])
        self.assertEqual(self.client.get("/api/search", params={"q": "rod"}).json()["total"], 1)
        self.assertEqual(self.client.get("/api/page", params={"title": "Rod"}).json()["source"], "https://fischipedia.org/wiki/Rod")
        self.assertEqual(self.client.get("/api/category", params={"name": "Fishing rods"}).json()["total"], 1)

    def test_mcp_tools_are_registered(self):
        names = {tool.name for tool in mcp._tool_manager.list_tools()}
        self.assertEqual(names, {"wiki_status", "wiki_search", "wiki_page", "wiki_table", "wiki_category", "wiki_pages", "wiki_failed"})


if __name__ == "__main__":
    unittest.main()
