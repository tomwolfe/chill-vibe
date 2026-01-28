import os
from pathlib import Path
from chill_vibe.execution import verify_success, get_file_baseline

def test_no_clobber_passed(tmp_path):
    repo_path = tmp_path
    protected_file = repo_path / "protected.txt"
    protected_file.write_text("don't touch this")
    
    # Capture baseline
    baseline = get_file_baseline(str(repo_path))
    
    # Normal execution doesn't touch it
    (repo_path / "other.txt").write_text("hello")
    
    passed, results = verify_success([], str(repo_path), file_baseline=baseline, protected_files=["protected.txt"])
    
    assert passed
    assert any(r["criterion"] == "no_clobber" and r["passed"] for r in results)

def test_no_clobber_failed(tmp_path):
    repo_path = tmp_path
    protected_file = repo_path / "protected.txt"
    protected_file.write_text("don't touch this")
    
    # Capture baseline
    baseline = get_file_baseline(str(repo_path))
    
    # Clobber the file
    protected_file.write_text("oops, touched it")
    
    passed, results = verify_success([], str(repo_path), file_baseline=baseline, protected_files=["protected.txt"])
    
    assert not passed
    assert any(r["criterion"] == "no_clobber" and not r["passed"] for r in results)
    
def test_no_clobber_glob(tmp_path):
    repo_path = tmp_path
    (repo_path / "protected1.txt").write_text("stay")
    (repo_path / "protected2.txt").write_text("stay")
    
    # Capture baseline
    baseline = get_file_baseline(str(repo_path))
    
    # Clobber one
    (repo_path / "protected1.txt").write_text("changed")
    
    passed, results = verify_success([], str(repo_path), file_baseline=baseline, protected_files=["protected*.txt"])
    
    assert not passed
    clobber_result = next(r for r in results if r["criterion"] == "no_clobber")
    assert "protected1.txt" in clobber_result["details"]["clobbered_files"]
    assert "protected2.txt" not in clobber_result["details"]["clobbered_files"]
