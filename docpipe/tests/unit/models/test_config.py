"""Tests for configuration models."""

import pytest
from pathlib import Path
import tempfile
import json

from docpipe.models import AnalysisConfig


class TestAnalysisConfig:
    """Test AnalysisConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AnalysisConfig()
        
        # Check defaults
        assert config.root_path is None
        assert config.check_compliance is True
        assert config.analyze_similarity is True
        assert config.similarity_threshold == 0.75
        assert config.max_file_lines == 500
        assert config.min_test_coverage == 90.0
        
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AnalysisConfig(
            root_path=Path("/test"),
            check_compliance=False,
            similarity_threshold=0.85,
            output_format="csv"
        )
        
        assert config.root_path == Path("/test")
        assert config.check_compliance is False
        assert config.similarity_threshold == 0.85
        assert config.output_format == "csv"
        
    def test_validation(self):
        """Test configuration validation."""
        # Invalid similarity threshold
        with pytest.raises(ValueError, match="similarity_threshold must be between"):
            AnalysisConfig(similarity_threshold=1.5)
            
        with pytest.raises(ValueError, match="similarity_threshold must be between"):
            AnalysisConfig(similarity_threshold=-0.1)
            
        # Invalid test coverage
        with pytest.raises(ValueError, match="min_test_coverage must be between"):
            AnalysisConfig(min_test_coverage=150.0)
            
        # Invalid output format
        with pytest.raises(ValueError, match="output_format must be one of"):
            AnalysisConfig(output_format="invalid")
            
        # Invalid similarity method
        with pytest.raises(ValueError, match="similarity_method must be one of"):
            AnalysisConfig(similarity_method="invalid")
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = AnalysisConfig(
            check_compliance=False,
            similarity_threshold=0.8
        )
        
        data = config.to_dict()
        assert isinstance(data, dict)
        assert data["check_compliance"] is False
        assert data["similarity_threshold"] == 0.8
        
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "check_compliance": False,
            "similarity_threshold": 0.9,
            "output_format": "excel"
        }
        
        config = AnalysisConfig.from_dict(data)
        assert config.check_compliance is False
        assert config.similarity_threshold == 0.9
        assert config.output_format == "excel"
        
    def test_save_and_load_json(self):
        """Test saving and loading configuration from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            
            # Save config
            config = AnalysisConfig(
                similarity_threshold=0.85,
                check_compliance=False
            )
            config.save(config_path)
            
            # Load config
            loaded_config = AnalysisConfig.from_file(config_path)
            assert loaded_config.similarity_threshold == 0.85
            assert loaded_config.check_compliance is False
            
    def test_exclude_patterns(self):
        """Test exclude patterns configuration."""
        config = AnalysisConfig()
        
        # Check default patterns
        assert "*.venv*" in config.exclude_patterns
        assert "*__pycache__*" in config.exclude_patterns
        assert "*.git*" in config.exclude_patterns
        
        # Custom patterns
        custom_config = AnalysisConfig(
            exclude_patterns=["*.tmp", "build/"]
        )
        assert "*.tmp" in custom_config.exclude_patterns
        assert "build/" in custom_config.exclude_patterns
        
    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValueError):
            AnalysisConfig(unknown_field="value")