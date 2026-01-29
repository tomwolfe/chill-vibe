import json
import re
from pathlib import Path

def extract_keywords(text):
    """Extract significant keywords from text for ranking."""
    if not text:
        return set()
    # Extract alphanumeric words >= 3 chars, lowercase
    return set(re.findall(r'\b\w{3,}\b', text.lower()))

def calculate_keyword_score(text1, text2):
    """Calculate overlap score between two texts based on keywords."""
    if not text1 or not text2:
        return 0.0
    kw1 = extract_keywords(text1)
    kw2 = extract_keywords(text2)
    if not kw1:
        return 0.0
    overlap = kw1.intersection(kw2)
    # Return Jaccard-like similarity focused on the first set
    return len(overlap) / len(kw1)

class MemoryManager:
    """Manages failure memory by analyzing log files."""
    
    def __init__(self, log_path=".chillvibe_logs.jsonl"):
        self.log_path = Path(log_path)

    def get_similar_failures(self, classification, signals=None, limit=3, current_prompt=None, success_criteria=None):
        """Find recent failures with the same classification, ranked by keyword relevance and signals."""
        if not self.log_path.exists():
            return []
            
        signals = set(signals or [])
        failures = []
        
        # Define signal weights
        SIGNAL_WEIGHTS = {
            "TEST_FAILURE": 10,
            "SYNTAX_ERROR": 10,
            "COMMAND_NOT_FOUND": 5,
            "DEPENDENCY_MISSING": 8,
            "PERMISSION_DENIED": 5,
            "TIMEOUT": 3
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
                                        # High priority: matching signals are strong indicators
                                        score += SIGNAL_WEIGHTS.get(s, 2) * 2
                            
                            # Keyword similarity ranking
                            if current_prompt:
                                # Match against agent prompt
                                prompt_similarity = calculate_keyword_score(current_prompt, entry.get("agent_prompt", ""))
                                score += prompt_similarity * 10 
                                
                                # Match against objectives for better context
                                objectives = entry.get("objectives") or []
                                if objectives:
                                    obj_text = " ".join(objectives)
                                    obj_similarity = calculate_keyword_score(current_prompt, obj_text)
                                    score += obj_similarity * 5

                            # Success criteria similarity weighting
                            if success_criteria:
                                entry_success_criteria = entry.get("success_criteria") or []
                                if isinstance(entry_success_criteria, list) and entry_success_criteria:
                                    sc_text1 = " ".join(success_criteria)
                                    sc_text2 = " ".join(entry_success_criteria)
                                    sc_similarity = calculate_keyword_score(sc_text1, sc_text2)
                                    score += sc_similarity * 8
                            
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

    def get_top_lessons(self, classification, signals=None, limit=3, current_prompt=None, success_criteria=None):
        """Extract 'Lessons Learned' from previous failures of the same classification, ranked by relevance."""
        failures = self.get_similar_failures(classification, signals=signals, limit=limit, current_prompt=current_prompt, success_criteria=success_criteria)
        lessons = []
        for f in failures:
            lesson = f.get("lessons_learned")
            if lesson:
                lessons.append(lesson)
        return lessons
