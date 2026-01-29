import json
from pathlib import Path
from difflib import SequenceMatcher

class MemoryManager:
    """Manages failure memory by analyzing log files."""
    
    def __init__(self, log_path=".chillvibe_logs.jsonl"):
        self.log_path = Path(log_path)

    def get_similar_failures(self, classification, signals=None, limit=3, current_prompt=None):
        """Find recent failures with the same classification, ranked by relevance to signals and prompt similarity."""
        if not self.log_path.exists():
            return []
            
        signals = set(signals or [])
        failures = []
        
        # Define signal weights
        SIGNAL_WEIGHTS = {
            "TEST_FAILURE": 5,
            "SYNTAX_ERROR": 5,
            "COMMAND_NOT_FOUND": 2,
            "DEPENDENCY_MISSING": 2,
            "PERMISSION_DENIED": 2,
            "TIMEOUT": 1
        }

        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if (entry.get("status") in ["FAILED", "OVER_BUDGET"] and 
                            entry.get("classification") == classification):
                            
                            # Calculate relevance score based on weighted signal matching
                            entry_signals = entry.get("signals") or []
                            score = 0
                            if signals:
                                # Count matches with weights
                                for s in signals:
                                    if s in entry_signals:
                                        score += SIGNAL_WEIGHTS.get(s, 1)
                            
                            # Add string similarity score if prompt is provided
                            if current_prompt and entry.get("agent_prompt"):
                                similarity = SequenceMatcher(None, current_prompt, entry.get("agent_prompt")).ratio()
                                score += similarity * 10 # Heavily weight prompt similarity
                            
                            entry["relevance_score"] = score
                            failures.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[!] Warning: Could not read memory logs: {e}")
            
        # Rank by relevance score (primary) and timestamp (secondary)
        # We sort by score descending, then by original order (which is chronological) reversed
        ranked_failures = sorted(
            failures, 
            key=lambda x: (x.get("relevance_score", 0), failures.index(x)), 
            reverse=True
        )
        
        return ranked_failures[:limit]

    def get_top_lessons(self, classification, signals=None, limit=3, current_prompt=None):
        """Extract 'Lessons Learned' from previous failures of the same classification, ranked by relevance."""
        failures = self.get_similar_failures(classification, signals=signals, limit=limit, current_prompt=current_prompt)
        lessons = []
        for f in failures:
            lesson = f.get("lessons_learned")
            if lesson:
                lessons.append(lesson)
        return lessons
