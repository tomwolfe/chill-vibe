import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.chill_vibe.execution import git_rollback, get_git_head, verify_success
import os

class TestRollback(unittest.TestCase):
    @patch('subprocess.run')
    def test_get_git_head(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="mock_sha\n")
        head = get_git_head("/tmp")
        self.assertEqual(head, "mock_sha")
        mock_run.assert_called_with("git rev-parse HEAD", shell=True, cwd="/tmp", capture_output=True, text=True)

    @patch('subprocess.run')
    def test_git_rollback(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        success = git_rollback("/tmp", "mock_sha")
        self.assertTrue(success)
        # Should call reset --hard twice (one general, one specific)
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call("git reset --hard mock_sha", shell=True, cwd="/tmp", capture_output=True, text=True)

    def test_verify_success_eval(self):
        # Test eval criterion
        criteria = ["eval: 1 + 1 == 2"]
        passed, results = verify_success(criteria, os.getcwd())
        self.assertTrue(passed)
        self.assertEqual(results[0]["message"], "Eval '1 + 1 == 2' returned True")

        criteria = ["eval: 1 + 1 == 3"]
        passed, results = verify_success(criteria, os.getcwd())
        self.assertFalse(passed)
        self.assertEqual(results[0]["message"], "Eval '1 + 1 == 3' returned False")

    @patch('subprocess.run')
    def test_verify_success_coverage(self, mock_run):
        # Mock pytest --cov output
        mock_output = """
---------- coverage: platform darwin, python 3.9.10-final-0 -----------
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
src/chill_vibe/cli.py       100     20    80%
-------------------------------------------------------
TOTAL                       100     20    80%
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
        
        criteria = ["coverage: 75"]
        passed, results = verify_success(criteria, os.getcwd())
        self.assertTrue(passed)
        self.assertIn("Coverage 80%", results[0]["message"])

        criteria = ["coverage: 85"]
        passed, results = verify_success(criteria, os.getcwd())
        self.assertFalse(passed)
        self.assertIn("Coverage 80%", results[0]["message"])

if __name__ == '__main__':
    unittest.main()
