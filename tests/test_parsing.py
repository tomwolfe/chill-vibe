import sys
import os
import pytest

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from chill_vibe.models import MissionContract

def test_parsing_standard_json():
    json_str = '{"objectives": ["obj1"], "success_criteria": ["crit1"], "agent_prompt": "prompt1", "summary": "sum1"}'
    mission = MissionContract.from_json(json_str)
    assert mission.objectives == ["obj1"]
    assert mission.success_criteria == ["crit1"]
    assert mission.agent_prompt == "prompt1"
    assert mission.summary == "sum1"

def test_parsing_markdown_fences():
    json_str = '```json\n{"objectives": ["obj1"], "success_criteria": ["crit1"], "agent_prompt": "prompt1", "summary": "sum1"}\n```'
    mission = MissionContract.from_json(json_str)
    assert mission.objectives == ["obj1"]
    assert mission.agent_prompt == "prompt1"

def test_parsing_extra_noise():
    json_str = 'Here is the contract: {"objectives": ["obj1"], "success_criteria": ["crit1"], "agent_prompt": "prompt1", "summary": "sum1"} Hope this helps!'
    mission = MissionContract.from_json(json_str)
    assert mission.objectives == ["obj1"]
    assert mission.agent_prompt == "prompt1"

def test_parsing_whitespace_and_newlines():
    json_str = ' \n\n  {"objectives": ["obj1"], "success_criteria": ["crit1"], "agent_prompt": "prompt1", "summary": "sum1"}  \n '
    mission = MissionContract.from_json(json_str)
    assert mission.objectives == ["obj1"]
    assert mission.agent_prompt == "prompt1"

def test_parsing_escaped_quotes():
    json_str = r'{"objectives": ["obj1"], "success_criteria": ["crit1"], "agent_prompt": "He said \"Hello\"", "summary": "sum1"}'
    mission = MissionContract.from_json(json_str)
    assert mission.agent_prompt == 'He said "Hello"'

def test_parsing_fallback_prompt():
    json_str = '{"objectives": ["obj1"], "success_criteria": ["crit1"], "summary": "sum1"}'
    mission = MissionContract.from_json(json_str, agent_prompt="fallback")
    assert mission.agent_prompt == "fallback"

def test_parsing_invalid_json():
    json_str = '{"objectives": ["obj1"]' # Missing closing brace
    with pytest.raises(ValueError, match="Invalid mission JSON"):
        MissionContract.from_json(json_str)
