"""
Docpipe - A comprehensive tool for analyzing AI coding instructions in markdown documentation.

This package provides tools for:
- Document similarity analysis
- Reference validation
- Compliance checking
- Instruction path tracing
- Structural soundness verification

Basic usage:
    from docpipe import analyze_project
    results = analyze_project("/path/to/project")
    print(results.summary)

Advanced usage:
    from docpipe import DocPipe, AnalysisConfig
    config = AnalysisConfig(similarity_threshold=0.8)
    pipeline = DocPipe(config)
    results = pipeline.analyze("/path/to/project")
"""

from docpipe.__version__ import __version__, __author__, __email__, __description__

# Main API imports
from .api import analyze_project, DocPipe
from .models import AnalysisConfig, AnalysisResults

# Feature detection
try:
    import sentence_transformers
    HAS_SEMANTIC_SIMILARITY = True
except ImportError:
    HAS_SEMANTIC_SIMILARITY = False

try:
    import pandas
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Available features
FEATURES = {
    'semantic_similarity': HAS_SEMANTIC_SIMILARITY,
    'excel_export': HAS_PANDAS,
    'dataframe_reports': HAS_PANDAS,
}

__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__email__',
    '__description__',
    
    # Main API
    'analyze_project',
    'DocPipe',
    'AnalysisConfig',
    'AnalysisResults',
    
    # Feature detection
    'FEATURES',
]