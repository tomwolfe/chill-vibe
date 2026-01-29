
PRICING = {
    "gemini-2.0-flash": {
        "prompt_token_rate": 0.10 / 1_000_000,
        "candidate_token_rate": 0.40 / 1_000_000,
    },
    "gemini-2.0-pro": {
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

DEFAULT_RATE = {
    "prompt_token_rate": 0.10 / 1_000_000,
    "candidate_token_rate": 0.40 / 1_000_000,
}

def get_rates(model_id):
    """Return the input and output token rates for a given model ID."""
    if not model_id:
        return DEFAULT_RATE
        
    model_id = model_id.lower()
    
    if "gemini-2.0-flash" in model_id:
        return PRICING["gemini-2.0-flash"]
    if "gemini-2.0-pro" in model_id:
        return PRICING["gemini-2.0-pro"]
    if "gemini-1.5-flash" in model_id:
        return PRICING["gemini-1.5-flash"]
    if "gemini-1.5-pro" in model_id:
        return PRICING["gemini-1.5-pro"]
        
    return DEFAULT_RATE
