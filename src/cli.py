"""
Command-line interface for Notion Second Brain Engine.
"""

import argparse
import json
import sys
from .notion_client import NotionClient
from .agent_kanban import AgentKanbanEngine
from .data_scout import DataScoutAgent
from .feedback_router import FeedbackRouterAgent

def main():
    parser = argparse.ArgumentParser(
        prog="notion-second-brain",
        description="Autonomous AI second-brain engine bridging Notion databases, Kanban PR workflows, and analytical SQL telemetry."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Triage command
    triage_parser = subparsers.add_parser("triage", help="Classify incoming feedback or ticket")
    triage_parser.add_argument("text", help="Feedback text to classify")
    triage_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Scout command
    scout_parser = subparsers.add_parser("scout", help="Run SQL analytics query and format Notion blocks")
    scout_parser.add_argument("query", help="Natural language or keyword query")
    scout_parser.add_argument("--blocks", action="store_true", help="Format output as Notion block objects")
    scout_parser.add_argument("--db", default=None, help="Path to SQLite database")

    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Generate an architectural execution plan for a ticket")
    plan_parser.add_argument("title", help="Ticket title")
    plan_parser.add_argument("criteria", nargs="*", help="Acceptance criteria items")

    # Check command
    subparsers.add_parser("check", help="Check local environment and CLI prerequisites")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "triage":
        router = FeedbackRouterAgent()
        result = router.classify(args.text)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Category:   {result['category']}")
            print(f"Priority:   {result['priority']}")
            print(f"Confidence: {result['confidence']:.2f}")

    elif args.command == "scout":
        scout = DataScoutAgent(db_path=args.db or ":memory:")
        res = scout.query(args.query)
        if args.blocks:
            blocks = scout.generate_notion_blocks(res)
            print(json.dumps(blocks, indent=2))
        else:
            print(f"Query: {res['prompt']}")
            print(f"SQL:   {res['sql']}")
            print(f"Rows:  {res['row_count']}")
            print(json.dumps(res["results"], indent=2))

    elif args.command == "plan":
        criteria = args.criteria or ["Implementation meets specifications", "Unit tests pass 100%"]
        kanban = AgentKanbanEngine()
        plan = kanban.plan_ticket(args.title, criteria)
        print(json.dumps(plan, indent=2))

    elif args.command == "check":
        kanban = AgentKanbanEngine()
        gh_status = kanban.check_gh_cli()
        client = NotionClient()
        token_found = bool(client.token)
        print(f"GitHub CLI:    {'OK' if gh_status.get('installed') else 'Missing'}")
        print(f"GitHub Auth:   {'Authenticated' if gh_status.get('authenticated') else 'Not authenticated'}")
        print(f"Notion Token:  {'Configured' if token_found else 'Not found'}")

if __name__ == "__main__":
    main()
