"""
Self-Optimizing Feedback & Triage Router
Classifies incoming customer feedback, issues, or tickets and dynamically updates classification heuristics.
"""

from typing import Dict, Any, List

class FeedbackRouterAgent:
    def __init__(self):
        self.rules = {
            "Bug / Urgent": ["crash", "error", "failed", "down", "broken", "critical", "bug", "timeout"],
            "Feature Request": ["wish", "could you add", "support for", "feature", "enhancement", "integrate"],
            "Billing / Contract": ["invoice", "pricing", "charge", "refund", "subscription", "contract", "mrr", "upgrade"],
            "Agent Performance": ["slow", "latency", "hallucination", "accuracy", "context", "token limit"]
        }

    def classify(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        scores = {}
        for category, keywords in self.rules.items():
            matched = [k for k in keywords if k in text_lower]
            scores[category] = len(matched)

        best_category = max(scores.keys(), key=lambda k: scores[k])
        has_match = scores[best_category] > 0
        if not has_match:
            best_category = "General Inquiry"

        priority = "P1 - High" if best_category in ["Bug / Urgent", "Billing / Contract"] else "P2 - Standard"

        return {
            "text": text,
            "category": best_category,
            "priority": priority,
            "confidence": 0.92 if has_match else 0.50
        }

    def learn_new_rule(self, category: str, keyword: str):
        if category not in self.rules:
            self.rules[category] = []
        if keyword.lower() not in self.rules[category]:
            self.rules[category].append(keyword.lower())
        return {"status": "updated", "category": category, "keywords_count": len(self.rules[category])}
