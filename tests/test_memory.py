import json
import os
from pathlib import Path
from chill_vibe.memory import MemoryManager

def test_memory_manager_get_similar_failures(tmp_path):
    log_file = tmp_path / ".chillvibe_logs.jsonl"
    entries = [
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Lesson 1", "timestamp": "2023-01-01T10:00:00"},
        {"status": "SUCCESS", "classification": None, "timestamp": "2023-01-01T11:00:00"},
        {"status": "FAILED", "classification": "TOOLING", "lessons_learned": "Tool lesson", "timestamp": "2023-01-01T12:00:00"},
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Lesson 2", "timestamp": "2023-01-01T13:00:00"},
    ]
    
    with open(log_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
            
    memory = MemoryManager(log_path=str(log_file))
    
    logic_failures = memory.get_similar_failures("LOGIC")
    assert len(logic_failures) == 2
    # Should be in reverse order
    assert logic_failures[0]["lessons_learned"] == "Lesson 2"
    assert logic_failures[1]["lessons_learned"] == "Lesson 1"
    
    tooling_failures = memory.get_similar_failures("TOOLING")
    assert len(tooling_failures) == 1
    assert tooling_failures[0]["lessons_learned"] == "Tool lesson"

def test_memory_manager_get_top_lessons(tmp_path):
    log_file = tmp_path / ".chillvibe_logs.jsonl"
    entries = [
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Lesson 1"},
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Lesson 2"},
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Lesson 3"},
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Lesson 4"},
    ]
    
    with open(log_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
            
    memory = MemoryManager(log_path=str(log_file))
    
    lessons = memory.get_top_lessons("LOGIC", limit=3)
    assert len(lessons) == 3
    assert lessons == ["Lesson 4", "Lesson 3", "Lesson 2"]

def test_memory_manager_weighted_signals(tmp_path):
    log_file = tmp_path / ".chillvibe_logs.jsonl"
    entries = [
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Weak match", "signals": ["TIMEOUT"]},
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Strong match", "signals": ["TEST_FAILURE", "SYNTAX_ERROR"]},
        {"status": "FAILED", "classification": "LOGIC", "lessons_learned": "Medium match", "signals": ["COMMAND_NOT_FOUND"]},
    ]
    
    with open(log_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
            
    memory = MemoryManager(log_path=str(log_file))
    
    # Searching for signals that should favor "Strong match"
    failures = memory.get_similar_failures("LOGIC", signals=["TEST_FAILURE", "TIMEOUT"])
    
    # "Strong match" has TEST_FAILURE (weight 5) -> score 5
    # "Weak match" has TIMEOUT (weight 1) -> score 1
    # "Medium match" has nothing -> score 0
    
    assert failures[0]["lessons_learned"] == "Strong match"
    assert failures[1]["lessons_learned"] == "Weak match"
    assert failures[2]["lessons_learned"] == "Medium match"
    
    # Test SYNTAX_ERROR weighting
    failures2 = memory.get_similar_failures("LOGIC", signals=["SYNTAX_ERROR", "COMMAND_NOT_FOUND"])
    # "Strong match" has SYNTAX_ERROR (5) -> 5
    # "Medium match" has COMMAND_NOT_FOUND (2) -> 2
    # "Weak match" -> 0
    assert failures2[0]["lessons_learned"] == "Strong match"
    assert failures2[1]["lessons_learned"] == "Medium match"

