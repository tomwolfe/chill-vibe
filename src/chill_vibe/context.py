import sys
from pathlib import Path

try:
    import git_dump
except ImportError:
    git_dump = None

def run_git_dump(repo_path, output_file, exclude_patterns=None, depth=None, include_ext=None):
    """Phase A: Context Extraction"""
    repo_path_obj = Path(repo_path)
    git_dir = repo_path_obj / ".git"
    
    if not git_dir.exists() or not git_dir.is_dir():
        print(f"[!] Warning: {repo_path} is not a valid git repository. Falling back to standard folder processing.")
    
    print(f"[*] Extracting codebase context from {repo_path}...")
    try:
        from git_dump.core import RepoProcessor
        
        include_patterns = None
        if include_ext:
            include_patterns = [f"*.{ext.strip()}" for ext in include_ext.split(",")]
            
        processor = RepoProcessor(
            str(repo_path_obj), 
            output_file, 
            ignore_patterns=exclude_patterns,
            include_patterns=include_patterns
        )
        
        processor.process()
    except Exception as e:
        print(f"Error running git-dump: {e}")
        sys.exit(1)
