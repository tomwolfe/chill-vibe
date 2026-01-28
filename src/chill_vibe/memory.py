import json
from pathlib import Path

class MemoryManager:
    """Manages failure memory by analyzing log files."""
    
    def __init__(self, log_path=".chillvibe_logs.jsonl"):
        self.log_path = Path(log_path)

    def get_similar_failures(self, classification, limit=3):
        """Find recent failures with the same classification."""
        if not self.log_path.exists():
            return []
            
        failures = []
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if (entry.get("status") == "FAILED" and 
                            entry.get("classification") == classification):
                            failures.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[!] Warning: Could not read memory logs: {e}")
            
        # Return most recent failures first
        return failures[::-1][:limit]

    def get_top_lessons(self, classification, limit=3):
        """Extract 'Lessons Learned' from previous failures of the same classification."""
        failures = self.get_similar_failures(classification, limit=limit)
        lessons = []
        for f in failures:
            lesson = f.get("lessons_learned")
            if lesson:
                lessons.append(lesson)
        return lessons
