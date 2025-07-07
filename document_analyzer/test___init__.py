#!/usr/bin/env python3
"""
Test suite for Document analyzer package initialization.

Tests package imports, version, and __all__ exports according to CLAUDE.md standards.
"""
import pytest
from typing import List, Any
import importlib
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDocumentAnalyzerInit:
    """Test cases for __init__.py module."""
    
    def test_package_imports_successfully(self) -> None:
        """Test that the package can be imported without errors."""
        try:
            import Document_analyzer
            assert Document_analyzer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Document_analyzer: {e}")
    
    def test_version_defined(self) -> None:
        """Test that __version__ is defined and formatted correctly."""
        from document_analyzer import __version__
        
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__.split('.')) == 3  # Major.Minor.Patch
        
        # Verify each part is a number
        parts = __version__.split('.')
        for part in parts:
            assert part.isdigit()
    
    def test_all_exports_defined(self) -> None:
        """Test that __all__ is properly defined with expected exports."""
        from document_analyzer import __all__
        
        assert __all__ is not None
        assert isinstance(__all__, list)
        assert len(__all__) > 0
        
        # Expected exports
        expected_exports = [
            # Analyzers
            "find_active_documents",
            "find_not_in_use_documents",
            "load_markdown_files",
            # Core
            "get_best_match_seq",
            "is_similar",
            "split_sections",
            # Embeddings
            "analyze_active_document_similarities",
            "analyze_semantic_similarity",
            # Merging
            "merge_documents",
            "merge_similar_documents",
            # Reports
            "check_content_embedding",
            "export_similarity_report",
            "generate_comprehensive_similarity_report",
            # Version
            "__version__"
        ]
        
        for export in expected_exports:
            assert export in __all__, f"Missing export: {export}"
    
    def test_all_exports_are_importable(self) -> None:
        """Test that all items in __all__ can be imported."""
        import Document_analyzer
        
        for item_name in Document_analyzer.__all__:
            try:
                item = getattr(Document_analyzer, item_name)
                assert item is not None
            except AttributeError:
                pytest.fail(f"Cannot import {item_name} from __all__")
    
    def test_no_unexpected_exports(self) -> None:
        """Test that there are no unexpected public exports."""
        import Document_analyzer
        
        # Get all public attributes
        public_attrs = [
            attr for attr in dir(Document_analyzer)
            if not attr.startswith('_')
        ]
        
        # All public attributes should be in __all__
        for attr in public_attrs:
            if attr not in ['__all__', '__version__']:  # These are meta-exports
                assert attr in Document_analyzer.__all__, \
                    f"Public attribute {attr} not in __all__"
    
    def test_module_docstring(self) -> None:
        """Test that the module has a proper docstring."""
        import Document_analyzer
        
        assert Document_analyzer.__doc__ is not None
        assert len(Document_analyzer.__doc__) > 50  # Reasonable docstring length
        assert "Document matching and analysis utilities" in Document_analyzer.__doc__
    
    def test_submodule_imports(self) -> None:
        """Test that submodules are importable."""
        submodules = [
            'analyzers',
            'core',
            'embeddings',
            'merging',
            'reports',
            'config',
            'validation'
        ]
        
        for submodule in submodules:
            try:
                module = importlib.import_module(f'Document_analyzer.{submodule}')
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Cannot import submodule {submodule}: {e}")
    
    def test_no_circular_imports(self) -> None:
        """Test that there are no circular import issues."""
        # This is tested implicitly by successful imports above
        # but we can be more explicit
        import Document_analyzer.analyzers
        import Document_analyzer.core
        import Document_analyzer.embeddings
        import Document_analyzer.merging
        import Document_analyzer.reports
        
        # If we get here without ImportError, there are no circular imports
        assert True
    
    def test_type_hints_present(self) -> None:
        """Test that type hints are properly defined."""
        import Document_analyzer
        import inspect
        
        # Check __all__ has type annotation
        annotations = Document_analyzer.__annotations__
        assert '__all__' in annotations
        assert annotations['__all__'] == List[str]


class TestImportErrorHandling:
    """Test error handling for import issues."""
    
    def test_handles_missing_dependency_gracefully(self, monkeypatch: Any) -> None:
        """Test that missing dependencies are handled appropriately."""
        # This would test what happens if a dependency is missing
        # For now we assume all dependencies are available
        pass
    
    def test_provides_helpful_error_messages(self) -> None:
        """Test that import errors provide helpful messages."""
        # This would test custom ImportError messages
        # Current implementation uses standard imports
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
