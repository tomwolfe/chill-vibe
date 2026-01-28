import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import importlib.util

# Load chill-vibe.py as a module
file_path = os.path.abspath("chill-vibe.py")
module_name = "chill_vibe"

# Mock the genai and git_dump imports before executing the module
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai
sys.modules["google.genai.types"] = MagicMock()
mock_git_dump = MagicMock()
sys.modules["git_dump"] = mock_git_dump

spec = importlib.util.spec_from_file_location(module_name, file_path)
chill_vibe = importlib.util.module_from_spec(spec)
sys.modules[module_name] = chill_vibe
spec.loader.exec_module(chill_vibe)

class TestChillVibe(unittest.TestCase):

    @patch('chill_vibe.git_dump.dump')
    def test_run_git_dump_success(self, mock_dump):
        chill_vibe.run_git_dump("repo/path", "output.txt")
        mock_dump.assert_called_once_with("repo/path", "output.txt")

    @patch('builtins.open', new_callable=mock_open, read_data="code context")
    @patch('os.path.exists')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    def test_get_strategic_reasoning_success(self, mock_exists, mock_file):
        mock_exists.return_value = True
        
        # Patch the Client directly in the chill_vibe module
        with patch.object(chill_vibe.genai, 'Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_response = MagicMock()
            mock_response.text = "Analysis... <agent_prompt>Work on this project</agent_prompt> Goals..."
            mock_client.models.generate_content.return_value = mock_response
            
            prompt = chill_vibe.get_strategic_reasoning("context.txt", "model-id", "HIGH")
            
            self.assertEqual(prompt, "Work on this project")
            mock_client.models.generate_content.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data="code context")
    @patch('os.path.exists')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    def test_get_strategic_reasoning_no_tags(self, mock_exists, mock_file):
        mock_exists.return_value = True
        
        with patch.object(chill_vibe.genai, 'Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_response = MagicMock()
            mock_response.text = "Full response without tags"
            mock_client.models.generate_content.return_value = mock_response
            
            prompt = chill_vibe.get_strategic_reasoning("context.txt", "model-id", "HIGH")
            
            self.assertEqual(prompt, "Full response without tags")

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_run_coding_agent_gemini(self, mock_thread, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdin = MagicMock()
        
        chill_vibe.run_coding_agent("gemini-cli", "Start mission")
        
        args, kwargs = mock_popen.call_args
        self.assertIn("npx", args[0])
        self.assertIn("@google/gemini-cli", args[0])
        self.assertIn("--yolo", args[0])
        mock_process.stdin.write.assert_called_with("Start mission\n")

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_run_coding_agent_qwen(self, mock_thread, mock_popen):
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdin = MagicMock()
        
        chill_vibe.run_coding_agent("qwen", "Start mission")
        
        args, kwargs = mock_popen.call_args
        self.assertIn("qwen", args[0])

    def test_forward_stdin(self):
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        
        # Mock sys.stdin.read to return a string then an empty string to break the loop
        with patch('sys.stdin.read', side_effect=['a', 'b', '']):
            chill_vibe.forward_stdin(mock_process)
            
        # Check if characters were written to process stdin
        self.assertEqual(mock_process.stdin.write.call_count, 2)
        mock_process.stdin.write.assert_any_call('a')
        mock_process.stdin.write.assert_any_call('b')
        mock_process.stdin.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
