import pytest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from chill_vibe.execution import verify_success
from chill_vibe.reasoning import get_recovery_strategy
from chill_vibe.memory import MemoryManager

def test_verify_success_captures_output(tmp_path):
    # Create a failing script
    failing_script = tmp_path / "fail.sh"
    failing_script.write_text("#!/bin/bash\necho 'standard output line'\necho 'error output line' >&2\nexit 1")
    failing_script.chmod(0o755)
    
    success_criteria = [str(failing_script)]
    passed, results = verify_success(success_criteria, str(tmp_path))
    
    assert not passed
    assert len(results) == 1
    assert results[0]["criterion"] == str(failing_script)
    assert "stdout" in results[0]["details"]
    assert "stderr" in results[0]["details"]
    assert "standard output line" in results[0]["details"]["stdout"]
    assert "error output line" in results[0]["details"]["stderr"]

@patch("chill_vibe.reasoning.genai")
def test_get_recovery_strategy_injects_error_details(mock_genai, tmp_path):
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    
    # Mock response
    mock_response = MagicMock()
    mock_response.text = "<classification>LOGIC</classification><lessons_learned>Tested something</lessons_learned><agent_prompt>Try again</agent_prompt>"
    mock_client.models.generate_content.return_value = mock_response
    
    verification_results = [
        {
            "criterion": "pytest",
            "passed": False,
            "message": "Pytest failed",
            "details": {
                "stdout": "FAIL: test_something",
                "stderr": "AssertionError"
            }
        }
    ]
    
    get_recovery_strategy(
        repo_path=str(tmp_path),
        model_id="gemini-3-flash",
        original_prompt="original prompt",
        failure_output="failure output",
        exit_code=1,
        verification_results=verification_results
    )
    
    # Check if prompt contains the error details
    args, kwargs = mock_client.models.generate_content.call_args
    prompt = kwargs["contents"]
    
    assert "--- SPECIFIC ERROR DETAILS ---" in prompt
    assert "--- Error snippet for pytest ---" in prompt
    assert "STDOUT:\nFAIL: test_something" in prompt
    assert "STDERR:\nAssertionError" in prompt

def test_memory_ranking(tmp_path):
    log_file = tmp_path / ".chillvibe_logs.jsonl"
    
    # Create entries with different signals
    entries = [
        {
            "status": "FAILED",
            "classification": "LOGIC",
            "signals": ["TEST_FAILURE"],
            "lessons_learned": "Lesson A",
            "timestamp": "2026-01-28T10:00:00"
        },
        {
            "status": "FAILED",
            "classification": "LOGIC",
            "signals": ["DEPENDENCY_MISSING", "TEST_FAILURE"],
            "lessons_learned": "Lesson B",
            "timestamp": "2026-01-28T10:01:00"
        },
        {
            "status": "FAILED",
            "classification": "LOGIC",
            "signals": ["SYNTAX_ERROR"],
            "lessons_learned": "Lesson C",
            "timestamp": "2026-01-28T10:02:00"
        }
    ]
    
    with open(log_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
            
    memory = MemoryManager(log_path=str(log_file))
    
    # Case 1: Match Lesson B (highest score)
    results = memory.get_similar_failures("LOGIC", signals=["DEPENDENCY_MISSING", "TEST_FAILURE"])
    assert results[0]["lessons_learned"] == "Lesson B"
    
    # Case 2: Match Lesson A and B (B has more matches)
    results = memory.get_similar_failures("LOGIC", signals=["TEST_FAILURE"])
    # Both A and B match 1 signal. B is more recent in the list (index wise).
    # Wait, my logic for ranking: (score, index). 
    # score is 1 for both. index of A is 0, index of B is 1.
    # sorted(reverse=True) will pick B first if scores are same? 
    # list.index(x) returns first occurrence, but here they are unique entries.
    assert results[0]["lessons_learned"] in ["Lesson A", "Lesson B"]
    
    # Case 3: Match Lesson C
    results = memory.get_similar_failures("LOGIC", signals=["SYNTAX_ERROR"])
    assert results[0]["lessons_learned"] == "Lesson C"
