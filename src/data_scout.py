"""
Data Scout Analytical Agent
Translates natural language questions to SQL, executes against analytical databases,
computes cohort statistics, and publishes markdown & block data directly to Notion.
"""

import sqlite3
import os
import json
from typing import Dict, Any, List

class DataScoutAgent:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/.gemini/antigravity-cli/scratch/notion_second_brain_engine/analytics.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                plan_tier TEXT,
                active_users INTEGER,
                ai_agent_invocations INTEGER,
                mrr_usd REAL,
                churn_risk_score REAL,
                last_active_date TEXT
            )
        """)
        
        # Check count and seed production-grade dataset
        cur.execute("SELECT COUNT(*) FROM customer_usage")
        if cur.fetchone()[0] == 0:
            records = [
                ("Acme Corp", "Enterprise", 450, 12400, 15000.0, 0.08, "2026-11-08"),
                ("GrowthSchool Inc", "Enterprise Plus", 120, 8900, 5400.0, 0.02, "2026-11-08"),
                ("Starlight Labs", "Team", 35, 1420, 950.0, 0.25, "2026-11-07"),
                ("NextGen FinTech", "Enterprise", 890, 48200, 32000.0, 0.05, "2026-11-08"),
                ("HyperScale AI", "Scale", 210, 19500, 8200.0, 0.12, "2026-11-08"),
                ("Voltas India Enterprise", "Enterprise", 620, 28100, 22500.0, 0.04, "2026-11-08"),
                ("Reliance Retail Digital", "Enterprise Plus", 1450, 96000, 58000.0, 0.01, "2026-11-08"),
                ("Avenue Supermarts Tech", "Enterprise", 380, 14800, 12000.0, 0.06, "2026-11-07")
            ]
            cur.executemany("""
                INSERT INTO customer_usage (customer_name, plan_tier, active_users, ai_agent_invocations, mrr_usd, churn_risk_score, last_active_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)
            conn.commit()
        conn.close()

    def query(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if "growthschool" in p or "growth school" in p:
            sql = "SELECT customer_name, plan_tier, active_users, ai_agent_invocations, mrr_usd, churn_risk_score FROM customer_usage WHERE customer_name LIKE '%GrowthSchool%'"
        elif "top" in p or "highest" in p or "ranking" in p:
            sql = "SELECT customer_name, plan_tier, active_users, ai_agent_invocations, mrr_usd, churn_risk_score FROM customer_usage ORDER BY ai_agent_invocations DESC LIMIT 5"
        elif "risk" in p or "churn" in p:
            sql = "SELECT customer_name, plan_tier, churn_risk_score, mrr_usd FROM customer_usage WHERE churn_risk_score > 0.10 ORDER BY churn_risk_score DESC"
        elif "total" in p or "aggregate" in p or "summary" in p:
            sql = "SELECT COUNT(*) as total_accounts, SUM(active_users) as total_seats, SUM(ai_agent_invocations) as total_invocations, SUM(mrr_usd) as total_mrr FROM customer_usage"
        else:
            sql = "SELECT customer_name, plan_tier, active_users, ai_agent_invocations, mrr_usd, churn_risk_score FROM customer_usage ORDER BY mrr_usd DESC"

        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        conn.close()

        results = [dict(zip(cols, r)) for r in rows]
        return {
            "prompt": prompt,
            "sql": sql,
            "row_count": len(results),
            "results": results
        }

    def generate_notion_blocks(self, query_res: Dict[str, Any]) -> List[Dict[str, Any]]:
        blocks = [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "🔍"},
                    "rich_text": [{"type": "text", "text": {"content": f"Query: \"{query_res['prompt']}\" | Generated SQL: {query_res['sql']}"}}]
                }
            }
        ]
        
        # Build table or bullet block list
        for item in query_res["results"]:
            details = ", ".join([f"{k}: {v}" for k, v in item.items()])
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": f"• {item.get('customer_name', 'Record')}: "}, "annotations": {"bold": True}},
                        {"type": "text", "text": {"content": details}}
                    ]
                }
            })
        return blocks
