
import pytest
from chill_vibe.budget import BudgetTracker

class MockResponse:
    def __init__(self, prompt_tokens, candidate_tokens):
        class Usage:
            def __init__(self, p, c):
                self.prompt_token_count = p
                self.candidates_token_count = c
                self.total_token_count = p + c
        self.usage_metadata = Usage(prompt_tokens, candidate_tokens)

def test_budget_tracker_dynamic_pricing_flash():
    # Gemini 3 Flash Preview: $0.10/1M input, $0.40/1M output
    tracker = BudgetTracker(model_id="gemini-3-flash-preview")
    
    # 1M prompt tokens -> $0.10
    # 1M candidate tokens -> $0.40
    response = MockResponse(1_000_000, 1_000_000)
    tracker.update_from_response(response)
    
    assert tracker.total_cost == pytest.approx(0.50)
    assert tracker.total_tokens == 2_000_000

def test_budget_tracker_dynamic_pricing_pro():
    # Gemini 3 Pro Preview: $1.25/1M input, $5.00/1M output
    tracker = BudgetTracker(model_id="gemini-3-pro-preview")
    
    response = MockResponse(1_000_000, 1_000_000)
    tracker.update_from_response(response)
    
    assert tracker.total_cost == pytest.approx(6.25)

def test_budget_tracker_default_pricing():
    tracker = BudgetTracker(model_id="unknown-model")
    # Default is $0.10/1M prompt, $0.40/1M candidate
    response = MockResponse(1_000_000, 1_000_000)
    tracker.update_from_response(response)
    
    assert tracker.total_cost == pytest.approx(0.50)
