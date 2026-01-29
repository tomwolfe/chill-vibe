import os
from unittest.mock import MagicMock, patch
from chill_vibe.doctor import check_api_connectivity, check_api_quota, run_doctor, check_thinking_capability

@patch("chill_vibe.doctor.genai")
def test_check_api_connectivity(mock_genai):
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "connected"
    mock_client.models.generate_content.return_value = mock_response
    
    success, msg = check_api_connectivity("AIzaTestKey")
    assert success is True
    assert msg == "Connected successfully"

@patch("chill_vibe.doctor.genai")
def test_check_api_quota(mock_genai):
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_model = MagicMock()
    mock_model.name = "models/gemini-1.5-flash"
    mock_client.models.get.return_value = mock_model
    
    success, msg = check_api_quota("AIzaTestKey")
    assert success is True
    assert "Healthy" in msg

@patch("chill_vibe.doctor.genai")
def test_check_thinking_capability(mock_genai):
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    
    # Mock successful model access
    mock_client.models.get.return_value = MagicMock()
    
    with patch("google.genai.types.ThinkingConfig", return_value=MagicMock()):
        success, msg = check_thinking_capability("AIzaTestKey")
        assert success is True
        assert "Available" in msg
        assert "Supported by SDK" in msg

@patch("chill_vibe.doctor.genai")
@patch("chill_vibe.doctor.check_api_connectivity")
@patch("chill_vibe.doctor.check_api_quota")
@patch("shutil.which")
@patch("subprocess.check_output")
@patch("builtins.input", return_value="n")
def test_run_doctor(mock_input, mock_subprocess, mock_which, mock_quota, mock_connectivity, mock_genai):
    mock_connectivity.return_value = (True, "Connected")
    mock_quota.return_value = (True, "API Quota/Health: Healthy")
    mock_which.return_value = "/usr/bin/git"
    mock_subprocess.return_value = "git version 2.39.2"
    
    # Mock environment
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaTestKey"}):
        registry = {}
        run_doctor(registry)
        
    mock_connectivity.assert_called_once()
    mock_quota.assert_called_once()
