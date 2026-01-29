import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from .pricing import get_rates

class BudgetTracker:
    """Tracks and limits Gemini API token usage and costs."""
    
    def __init__(self, max_cost: Optional[float] = None, log_path: Union[str, Path] = ".chillvibe_logs.jsonl", model_id: Optional[str] = None) -> None:
        self.max_cost = max_cost
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.candidate_tokens = 0
        self.total_cost = 0.0
        self.log_path = Path(log_path)
        self.model_id = model_id
        self.rates = get_rates(model_id)

    def update_from_response(self, response: Any) -> None:
        """Extract usage metadata from a Gemini API response and update totals."""
        if not hasattr(response, 'usage_metadata') or response.usage_metadata is None:
            return
            
        usage = response.usage_metadata
        # google-genai response object has these fields
        p_tokens = getattr(usage, 'prompt_token_count', 0)
        c_tokens = getattr(usage, 'candidates_token_count', 0)
        t_tokens = getattr(usage, 'total_token_count', 0)

        self.prompt_tokens += p_tokens
        self.candidate_tokens += c_tokens
        self.total_tokens += t_tokens
        
        # Dynamic cost calculation
        self.total_cost += (p_tokens * self.rates["prompt_token_rate"])
        self.total_cost += (c_tokens * self.rates["candidate_token_rate"])

    def is_over_budget(self) -> bool:
        """Check if the cumulative cost has exceeded the limit."""
        if self.max_cost is None:
            return False
        return self.total_cost > self.max_cost

    def get_usage_report(self) -> Dict[str, Any]:
        """Return a dictionary of the current usage."""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "candidate_tokens": self.candidate_tokens,
            "total_cost": round(self.total_cost, 6)
        }
