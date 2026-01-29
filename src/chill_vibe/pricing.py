
from typing import Dict, Optional

PRICING: Dict[str, Dict[str, float]] = {
    "gemini-3-flash-preview": {
        "prompt_token_rate": 0.10 / 1_000_000,
        "candidate_token_rate": 0.40 / 1_000_000,
    },
    "gemini-3-pro-preview": {
        "prompt_token_rate": 1.25 / 1_000_000,
        "candidate_token_rate": 5.00 / 1_000_000,
    },
    "gemini-1.5-flash": {
        "prompt_token_rate": 0.075 / 1_000_000,
        "candidate_token_rate": 0.30 / 1_000_000,
    },
    "gemini-1.5-pro": {
        "prompt_token_rate": 1.25 / 1_000_000,
        "candidate_token_rate": 5.00 / 1_000_000,
    }
}

DEFAULT_RATE: Dict[str, float] = {
    "prompt_token_rate": 0.10 / 1_000_000,
    "candidate_token_rate": 0.40 / 1_000_000,
}

def get_rates(model_id: Optional[str]) -> Dict[str, float]:
    """Return the input and output token rates for a given model ID."""
    if not model_id:
        return DEFAULT_RATE
        
    model_id_lower = model_id.lower()
    
    if "gemini-3-flash-preview" in model_id_lower:
        return PRICING["gemini-3-flash-preview"]
    if "gemini-3-pro-preview" in model_id_lower:
        return PRICING["gemini-3-pro-preview"]
    if "gemini-1.5-flash" in model_id_lower:
        return PRICING["gemini-1.5-flash"]
    if "gemini-1.5-pro" in model_id_lower:
        return PRICING["gemini-1.5-pro"]
        
    return DEFAULT_RATE
