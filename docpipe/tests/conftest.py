"""Pytest configuration and shared fixtures for docpipe tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, List, Dict, Any
import textwrap

from docpipe import AnalysisConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_project(temp_dir: Path) -> Path:
    """Create a sample project structure for testing."""
    # Create directories
    (temp_dir / "src").mkdir()
    (temp_dir / "docs").mkdir()
    (temp_dir / "tests").mkdir()
    
    # Create sample markdown files
    readme_content = textwrap.dedent("""
    # Sample Project
    
    This is a sample project for testing.
    
    See [Contributing Guide](docs/CONTRIBUTING.md) for details.
    See [Planning](docs/PLANNING.md) for project plans.
    """).strip()
    
    contributing_content = textwrap.dedent("""
    # Contributing Guide
    
    Please follow these guidelines:
    1. Write tests
    2. Follow code style
    3. Update documentation
    
    See [Code of Conduct](CODE_OF_CONDUCT.md) for behavior guidelines.
    """).strip()
    
    planning_content = textwrap.dedent("""
    # Project Planning
    
    This document outlines our project plans.
    
    ## Phase 1
    Initial implementation
    
    ## Phase 2
    Feature expansion
    """).strip()
    
    # Write files
    (temp_dir / "README.md").write_text(readme_content)
    (temp_dir / "docs" / "CONTRIBUTING.md").write_text(contributing_content)
    (temp_dir / "docs" / "PLANNING.md").write_text(planning_content)
    
    # Create a Python file for compliance testing
    python_content = textwrap.dedent('''
    """Sample Python module for testing."""
    
    def greet(name: str) -> str:
        """Greet a person by name."""
        return f"Hello, {name}!"
    
    def calculate_sum(a: int, b: int) -> int:
        """Calculate sum of two numbers."""
        return a + b
    
    class Calculator:
        """Simple calculator class."""
        
        def add(self, x: float, y: float) -> float:
            """Add two numbers."""
            return x + y
    ''').strip()
    
    (temp_dir / "src" / "sample.py").write_text(python_content)
    
    # Create a test file
    test_content = textwrap.dedent('''
    """Tests for sample module."""
    
    from sample import greet, calculate_sum
    
    def test_greet():
        """Test greeting function."""
        assert greet("World") == "Hello, World!"
    
    def test_calculate_sum():
        """Test sum calculation."""
        assert calculate_sum(2, 3) == 5
    ''').strip()
    
    (temp_dir / "tests" / "test_sample.py").write_text(test_content)
    
    return temp_dir


@pytest.fixture
def sample_config() -> AnalysisConfig:
    """Create a sample configuration for testing."""
    return AnalysisConfig(
        check_compliance=True,
        analyze_similarity=True,
        validate_references=True,
        trace_instructions=False,
        check_structure=False,
        similarity_threshold=0.75,
        min_test_coverage=80.0,
        max_file_lines=500,
    )


@pytest.fixture
def markdown_files(temp_dir: Path) -> Dict[str, Path]:
    """Create various markdown files for testing."""
    files = {}
    
    # Similar documents
    doc1_content = """
    # Installation Guide
    
    To install this package, run:
    ```bash
    pip install mypackage
    ```
    
    Then import it:
    ```python
    import mypackage
    ```
    """
    
    doc2_content = """
    # Setup Guide
    
    To install this package, execute:
    ```bash
    pip install mypackage
    ```
    
    Then import the package:
    ```python
    import mypackage
    ```
    """
    
    # Different document
    doc3_content = """
    # API Reference
    
    ## Classes
    
    ### MyClass
    Main class for the package.
    
    ### HelperClass
    Helper utilities.
    """
    
    # Write files
    files['doc1'] = temp_dir / "doc1.md"
    files['doc1'].write_text(doc1_content)
    
    files['doc2'] = temp_dir / "doc2.md"
    files['doc2'].write_text(doc2_content)
    
    files['doc3'] = temp_dir / "doc3.md"
    files['doc3'].write_text(doc3_content)
    
    return files


@pytest.fixture
def python_files(temp_dir: Path) -> Dict[str, Path]:
    """Create Python files with various compliance issues."""
    files = {}
    
    # Good file
    good_content = textwrap.dedent('''
    """Well-documented module with proper type hints."""
    
    from typing import List, Optional
    
    
    def process_data(items: List[str], prefix: Optional[str] = None) -> List[str]:
        """Process a list of items with optional prefix.
        
        Args:
            items: List of items to process
            prefix: Optional prefix to add
            
        Returns:
            Processed list of items
        """
        if prefix:
            return [f"{prefix}_{item}" for item in items]
        return items.copy()
    
    
    class DataProcessor:
        """Class for processing data."""
        
        def __init__(self, name: str) -> None:
            """Initialize processor."""
            self.name = name
    ''').strip()
    
    # Bad file with issues
    bad_content = textwrap.dedent('''
    # Missing docstrings and type hints
    
    def process_data(items, prefix=None):
        print("Processing data")  # Forbidden pattern
        try:
            result = []
            for item in items:
                result.append(prefix + item)
        except:  # Bare except
            pass
        return result
    
    def unsafe_operation():
        password = "secret123"  # Security issue
        eval("1+1")  # Dangerous function
    
    # Very long function to trigger complexity warning
    def complex_function(a, b, c, d, e):
        if a:
            if b:
                if c:
                    if d:
                        if e:
                            return 1
                        else:
                            return 2
                    else:
                        return 3
                else:
                    return 4
            else:
                return 5
        else:
            return 6
    ''').strip()
    
    files['good'] = temp_dir / "good_module.py"
    files['good'].write_text(good_content)
    
    files['bad'] = temp_dir / "bad_module.py"
    files['bad'].write_text(bad_content)
    
    return files


@pytest.fixture
def mock_sentence_transformers(monkeypatch):
    """Mock sentence_transformers for testing without the dependency."""
    import sys
    from unittest.mock import MagicMock
    
    # Create mock module
    mock_st = MagicMock()
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.5, 0.6, 0.7]]
    mock_st.SentenceTransformer.return_value = mock_model
    
    # Inject into sys.modules
    monkeypatch.setitem(sys.modules, 'sentence_transformers', mock_st)
    
    return mock_st