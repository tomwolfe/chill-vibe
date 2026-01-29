import json
import re
from pathlib import Path
from typing import Set, List, Dict, Any, Optional, Union

def extract_keywords(text: str) -> Set[str]:
    """Extract significant keywords from text for ranking."""
    if not text:
        return set()
    # Extract alphanumeric words >= 3 chars, lowercase
    return set(re.findall(r'\b\w{3,}\b', text.lower()))

def calculate_keyword_score(text1: str, text2: str) -> float:
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
    """Manages mission memory by analyzing log files."""
    
    def __init__(self, log_path: Union[str, Path] = ".chillvibe_logs.jsonl") -> None:
        self.log_path = Path(log_path)

    def get_similar_missions(self, classification: Optional[str] = None, signals: Optional[Union[List[str], Set[str]]] = None, limit: int = 3, current_prompt: Optional[str] = None, success_criteria: Optional[List[str]] = None, statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Find missions ranked by keyword relevance, signals, and status."""
        if not self.log_path.exists():
            return []
            
        signals_set = set(signals or [])
        # Default to FAILED/OVER_BUDGET if no statuses provided, for backward compatibility of 'get_similar_failures' intent
        target_statuses = statuses or ["FAILED", "OVER_BUDGET", "COMPLETED"]
        missions: List[Dict[str, Any]] = []
        
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
                        entry_status = entry.get("status")
                        
                        if entry_status not in target_statuses:
                            continue
                            
                        # If classification is provided, filter by it (mainly for failure matching)
                        if classification and entry.get("classification") != classification:
                            # If we are looking for successes, we might not have a classification
                            if entry_status != "COMPLETED":
                                continue
                        
                        # Calculate relevance score
                        score = 0.0
                        
                        # Status-based weighting: Successes are valuable patterns
                        if entry_status == "COMPLETED":
                            score += 5.0
                        
                        # Signal matching
                        entry_signals = entry.get("signals") or []
                        if signals_set:
                            for s in signals_set:
                                if s in entry_signals:
                                    score += SIGNAL_WEIGHTS.get(s, 2) * 2
                        
                        # Keyword similarity ranking
                        if current_prompt:
                            prompt_similarity = calculate_keyword_score(current_prompt, entry.get("agent_prompt", ""))
                            score += prompt_similarity * 10 
                            
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
                        missions.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[!] Warning: Could not read memory logs: {e}")
            
        # Rank by relevance score (primary) and timestamp (secondary)
        ranked_missions = sorted(
            missions, 
            key=lambda x: (float(x.get("relevance_score", 0.0)), missions.index(x)), 
            reverse=True
        )
        
        return ranked_missions[:limit]

    def get_similar_failures(self, classification: str, signals: Optional[Union[List[str], Set[str]]] = None, limit: int = 3, current_prompt: Optional[str] = None, success_criteria: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Maintain backward compatibility for failure-specific lookup."""
        return self.get_similar_missions(
            classification=classification, 
            signals=signals, 
            limit=limit, 
            current_prompt=current_prompt, 
            success_criteria=success_criteria,
            statuses=["FAILED", "OVER_BUDGET"]
        )

    def get_top_lessons(self, classification: str, signals: Optional[Union[List[str], Set[str]]] = None, limit: int = 3, current_prompt: Optional[str] = None, success_criteria: Optional[List[str]] = None) -> List[str]:
        """Extract 'Lessons Learned' from previous failures, ranked by relevance."""
        failures = self.get_similar_failures(classification, signals=signals, limit=limit, current_prompt=current_prompt, success_criteria=success_criteria)
        lessons = []
        for f in failures:
            lesson = f.get("lessons_learned")
            if lesson:
                lessons.append(str(lesson))
        return lessons
