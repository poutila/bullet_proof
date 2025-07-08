#!/usr/bin/env python3
"""Test runner for docpipe package."""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run the test suite."""
    # Add current directory to Python path
    root_dir = Path(__file__).parent
    sys.path.insert(0, str(root_dir))
    
    print("Running docpipe test suite...")
    print("=" * 60)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=docpipe",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-x",  # Stop on first failure
    ]
    
    try:
        result = subprocess.run(cmd, cwd=root_dir)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("\nCoverage report generated in htmlcov/index.html")
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()