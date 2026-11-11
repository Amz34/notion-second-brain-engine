"""
Enterprise Notion API Client with Production Resilience, Block Batching, and Real-time Synced Second Brain.
"""

import os
import json
import urllib.request
import urllib.error
import time
from typing import Dict, Any, List, Optional

NOTION_VERSION = "2022-06-28"

class NotionClient:
    def __init__(self, token: Optional[str] = None):
        if not token:
            token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN") or ""
            if not token:
                token_file = os.path.expanduser("~/.config/notion/token")
                if os.path.exists(token_file):
                    try:
                        with open(token_file, "r", encoding="utf-8") as f:
                            token = f.read().strip()
                    except OSError:
                        pass
        self.token = token
        self.base_url = "https://api.notion.com/v1"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }

    def request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, retries: int = 3) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        
        for attempt in range(retries):
            req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err_content = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    wait_time = float(e.headers.get("Retry-After", 2.0))
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"Notion API {e.code} Error on {method} {url}: {err_content}")
            except Exception as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"Network error on {method} {url}: {str(e)}")
                time.sleep(1.5)
        raise RuntimeError(f"Exceeded max retries for {method} {url}")

    def append_blocks(self, block_id: str, children: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Notion accepts at most 100 blocks per call
        results = []
        for i in range(0, len(children), 100):
            batch = children[i:i+100]
            resp = self.request("PATCH", f"blocks/{block_id}/children", {"children": batch})
            results.append(resp)
        return {"batches": len(results), "status": "success"}

    def query_database(self, database_id: str, filter_dict: Optional[Dict[str, Any]] = None, sorts: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        payload = {}
        if filter_dict:
            payload["filter"] = filter_dict
        if sorts:
            payload["sorts"] = sorts
        
        results = []
        has_more = True
        next_cursor = None
        while has_more:
            if next_cursor:
                payload["start_cursor"] = next_cursor
            resp = self.request("POST", f"databases/{database_id}/query", payload)
            results.extend(resp.get("results", []))
            has_more = resp.get("has_more", False)
            next_cursor = resp.get("next_cursor")
        return results

    def create_page(self, parent: Dict[str, Any], properties: Dict[str, Any], children: Optional[List[Dict[str, Any]]] = None, icon: Optional[Dict[str, Any]] = None, cover: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"parent": parent, "properties": properties}
        if children:
            payload["children"] = children[:100] # initial batch
        if icon:
            payload["icon"] = icon
        if cover:
            payload["cover"] = cover
        created = self.request("POST", "pages", payload)
        if children and len(children) > 100:
            self.append_blocks(created["id"], children[100:])
        return created

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("PATCH", f"pages/{page_id}", {"properties": properties})
