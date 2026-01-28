import json
from pathlib import Path

class BudgetTracker:
    """Tracks and limits Gemini API token usage and costs."""
    
    def __init__(self, max_cost=None, log_path=".chillvibe_logs.jsonl"):
        self.max_cost = max_cost
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.candidate_tokens = 0
        self.total_cost = 0.0 # Placeholder for cost calculation if needed
        self.log_path = Path(log_path)

    def update_from_response(self, response):
        """Extract usage metadata from a Gemini API response and update totals."""
        if not hasattr(response, 'usage_metadata') or response.usage_metadata is None:
            return
            
        usage = response.usage_metadata
        # google-genai response object has these fields
        self.total_tokens += getattr(usage, 'total_token_count', 0)
        self.prompt_tokens += getattr(usage, 'prompt_token_count', 0)
        self.candidate_tokens += getattr(usage, 'candidates_token_count', 0)
        
        # Simple cost estimation (approximate, e.g., for Gemini 2.0 Flash)
        # In a real app, this would be model-specific
        # Assuming $0.10 per 1M tokens as a rough average for Flash/Pro
        self.total_cost = (self.total_tokens / 1_000_000) * 0.10

    def is_over_budget(self):
        """Check if the cumulative cost has exceeded the limit."""
        if self.max_cost is None:
            return False
        return self.total_cost > self.max_cost

    def get_usage_report(self):
        """Return a dictionary of the current usage."""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "candidate_tokens": self.candidate_tokens,
            "total_cost": round(self.total_cost, 6)
        }
