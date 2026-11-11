"""
Unit tests for Notion Second Brain Engine.
"""

import unittest
from unittest.mock import patch, MagicMock
import io
import json
import urllib.error

from src.feedback_router import FeedbackRouterAgent
from src.data_scout import DataScoutAgent
from src.agent_kanban import AgentKanbanEngine
from src.notion_client import NotionClient


class TestFeedbackRouter(unittest.TestCase):
    def setUp(self):
        self.router = FeedbackRouterAgent()

    def test_classify_bug(self):
        res = self.router.classify("Production database connection failed with timeout crash")
        self.assertEqual(res["category"], "Bug / Urgent")
        self.assertEqual(res["priority"], "P1 - High")
        self.assertGreaterEqual(res["confidence"], 0.90)

    def test_classify_feature(self):
        res = self.router.classify("Could you add support for webhook notifications?")
        self.assertEqual(res["category"], "Feature Request")
        self.assertEqual(res["priority"], "P2 - Standard")

    def test_classify_billing(self):
        res = self.router.classify("Need invoice copy and subscription refund details")
        self.assertEqual(res["category"], "Billing / Contract")
        self.assertEqual(res["priority"], "P1 - High")

    def test_classify_performance(self):
        res = self.router.classify("Agent latency is very slow due to token limit context")
        self.assertEqual(res["category"], "Agent Performance")
        self.assertEqual(res["priority"], "P2 - Standard")

    def test_classify_general(self):
        res = self.router.classify("Hello there, just checking in")
        self.assertEqual(res["category"], "General Inquiry")
        self.assertEqual(res["priority"], "P2 - Standard")
        self.assertEqual(res["confidence"], 0.50)

    def test_learn_new_rule(self):
        self.router.learn_new_rule("Security Alert", "cve-2026")
        res = self.router.classify("Found possible cve-2026 exploit in dependency")
        self.assertEqual(res["category"], "Security Alert")


class TestDataScout(unittest.TestCase):
    def setUp(self):
        self.scout = DataScoutAgent(db_path=":memory:")

    def tearDown(self):
        self.scout.close()

    def test_top_query(self):
        res = self.scout.query("show top active accounts")
        self.assertEqual(res["row_count"], 5)
        self.assertTrue(len(res["results"]) > 0)
        self.assertIn("Reliance Retail Digital", res["results"][0]["customer_name"])

    def test_churn_query(self):
        res = self.scout.query("accounts at high risk of churn")
        self.assertTrue(res["row_count"] > 0)
        for r in res["results"]:
            self.assertGreater(r["churn_risk_score"], 0.10)

    def test_summary_query(self):
        res = self.scout.query("give me aggregate summary statistics")
        self.assertEqual(res["row_count"], 1)
        self.assertIn("total_accounts", res["results"][0])
        self.assertEqual(res["results"][0]["total_accounts"], 8)

    def test_generate_blocks(self):
        res = self.scout.query("top")
        blocks = self.scout.generate_notion_blocks(res)
        self.assertTrue(len(blocks) > 1)
        self.assertEqual(blocks[0]["type"], "callout")
        self.assertEqual(blocks[1]["type"], "bulleted_list_item")


class TestAgentKanban(unittest.TestCase):
    def setUp(self):
        self.engine = AgentKanbanEngine(repo_dir=".")

    def test_plan_ticket(self):
        criteria = ["Test criteria A", "Test criteria B"]
        plan = self.engine.plan_ticket("Sync Notion Blocks with PR", criteria)
        self.assertEqual(plan["title"], "Sync Notion Blocks with PR")
        self.assertTrue(plan["branch"].startswith("agent-feat/sync-notion-blocks-with-pr"))
        self.assertEqual(len(plan["subtasks"]), 3)
        self.assertEqual(plan["acceptance_criteria"], criteria)

    def test_check_gh_cli(self):
        status = self.engine.check_gh_cli()
        self.assertIn("installed", status)
        self.assertIn("authenticated", status)


class TestNotionClient(unittest.TestCase):
    def test_headers_and_token(self):
        client = NotionClient(token="secret_test_token_123")
        headers = client._headers()
        self.assertEqual(headers["Authorization"], "Bearer secret_test_token_123")
        self.assertEqual(headers["Notion-Version"], "2022-06-28")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("urllib.request.urlopen")
    def test_request_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"object": "list", "results": []}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = NotionClient(token="secret_test")
        res = client.request("GET", "users")
        self.assertEqual(res["object"], "list")

    @patch("urllib.request.urlopen")
    def test_append_blocks_batching(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = NotionClient(token="secret_test")
        # 250 blocks should result in 3 batches (100 + 100 + 50)
        dummy_blocks = [{"type": "paragraph", "paragraph": {"text": []}} for _ in range(250)]
        res = client.append_blocks("block_id_xyz", dummy_blocks)
        self.assertEqual(res["batches"], 3)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("urllib.request.urlopen")
    def test_query_database_pagination(self, mock_urlopen):
        # Page 1 returns has_more=True, Page 2 returns has_more=False
        page1 = {"results": [{"id": "page_1"}], "has_more": True, "next_cursor": "cur_1"}
        page2 = {"results": [{"id": "page_2"}], "has_more": False, "next_cursor": None}

        mock_resp1 = MagicMock()
        mock_resp1.read.return_value = json.dumps(page1).encode("utf-8")
        mock_resp2 = MagicMock()
        mock_resp2.read.return_value = json.dumps(page2).encode("utf-8")

        mock_urlopen.return_value.__enter__.side_effect = [mock_resp1, mock_resp2]

        client = NotionClient(token="secret_test")
        results = client.query_database("db_xyz")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "page_1")
        self.assertEqual(results[1]["id"], "page_2")


if __name__ == "__main__":
    unittest.main()
