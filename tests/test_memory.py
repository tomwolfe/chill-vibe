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
