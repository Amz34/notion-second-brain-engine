import pytest
from src.notion_client import NotionClient
from src.data_scout import DataScoutAgent
from src.feedback_router import FeedbackRouterAgent

def test_data_scout():
    ds = DataScoutAgent()
    res = ds.query("GrowthSchool")
    assert res["row_count"] >= 1
    assert "GrowthSchool Inc" in res["results"][0]["customer_name"]

def test_feedback_router():
    router = FeedbackRouterAgent()
    c = router.classify("The database query timed out and crashed")
    assert c["category"] == "Bug / Urgent"
    assert c["priority"] == "P1 - High"

if __name__ == "__main__":
    test_data_scout()
    test_feedback_router()
    print("All deterministic agent tests passed successfully!")
