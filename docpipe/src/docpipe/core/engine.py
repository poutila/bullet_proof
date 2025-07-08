"""Core analysis engine for docpipe."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
import os

from ..models import (
    AnalysisConfig,
    ComplianceResults,
    SimilarityResults,
    ReferenceResults,
    InstructionResults,
    DocumentInfo,
    Issue,
    Severity,
    IssueCategory,
)
from .exceptions import AnalysisError

logger = logging.getLogger(__name__)


class AnalysisEngine:
    """
    Core engine that orchestrates all analysis operations.
    
    This class serves as the bridge between the high-level API and the
    individual analyzer implementations.
    """
    
    def __init__(self, config: AnalysisConfig):
        """Initialize engine with configuration."""
        self.config = config
        self._analyzers = {}
        self._init_analyzers()
    
    def _init_analyzers(self) -> None:
        """Initialize analyzer instances based on configuration."""
        # Analyzers will be initialized lazily when needed
        # This allows us to avoid importing heavy dependencies until required
        pass
    
    def discover_documents(self, path: Path) -> List[DocumentInfo]:
        """
        Discover all documents in the project.
        
        Args:
            path: Root path to search
            
        Returns:
            List of document information
        """
        documents = []
        
        # Define markdown extensions to look for
        markdown_extensions = {'.md', '.markdown', '.mdown', '.mkd'}
        
        # Walk through directory
        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(root_path / d)]
            
            # Process files
            for file in files:
                file_path = root_path / file
                
                # Skip if should be excluded
                if self._should_exclude(file_path):
                    continue
                
                # Check if it's a markdown file
                if file_path.suffix.lower() in markdown_extensions:
                    # Skip if in 'not_in_use' and not configured to include
                    if not self.config.include_not_in_use and 'not_in_use' in file_path.parts:
                        continue
                    
                    try:
                        stat = file_path.stat()
                        
                        # Skip if file is too large
                        size_mb = stat.st_size / (1024 * 1024)
                        if size_mb > self.config.max_file_size_mb:
                            logger.warning(f"Skipping large file: {file_path} ({size_mb:.1f} MB)")
                            continue
                        
                        # Determine document type
                        doc_type = self._determine_doc_type(file_path)
                        
                        # Count lines
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = sum(1 for _ in f)
                        except Exception:
                            lines = 0
                        
                        documents.append(DocumentInfo(
                            path=file_path,
                            size_bytes=stat.st_size,
                            lines=lines,
                            type=doc_type,
                            last_modified=datetime.fromtimestamp(stat.st_mtime),
                            encoding='utf-8'
                        ))
                    
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
        
        return sorted(documents, key=lambda d: d.path)
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded based on patterns."""
        import fnmatch
        
        path_str = str(path)
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Also check individual path components
            for part in path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False
    
    def _determine_doc_type(self, path: Path) -> str:
        """Determine document type from path and name."""
        name_lower = path.name.lower()
        
        if 'claude' in name_lower:
            return 'claude'
        elif 'readme' in name_lower:
            return 'readme'
        elif 'changelog' in name_lower:
            return 'changelog'
        elif 'contributing' in name_lower:
            return 'contributing'
        elif 'license' in name_lower:
            return 'license'
        elif 'todo' in name_lower or 'task' in name_lower:
            return 'task'
        elif 'planning' in name_lower or 'plan' in name_lower:
            return 'planning'
        elif 'glossary' in name_lower:
            return 'glossary'
        else:
            return 'markdown'
    
    def analyze_compliance(self, path: Path) -> ComplianceResults:
        """Run compliance analysis."""
        from ..analyzers import ComplianceAnalyzer
        
        # Create analyzer with config
        compliance_config = {
            "compliance": {
                "min_type_hint_coverage": self.config.min_type_hint_coverage,
                "min_docstring_coverage": 70.0,  # Default
                "max_file_lines": self.config.max_file_lines,
                "max_complexity": self.config.max_complexity,
            },
            "exclude_patterns": self.config.exclude_patterns,
        }
        
        analyzer = ComplianceAnalyzer(compliance_config)
        result = analyzer.analyze(path)
        
        if result.success and isinstance(result.data, ComplianceResults):
            return result.data
        else:
            # Return empty results on failure
            results = ComplianceResults()
            results.issues.extend(result.issues)
            return results
    
    def analyze_similarity(self, path: Path) -> SimilarityResults:
        """Run similarity analysis."""
        from ..analyzers import create_similarity_analyzer
        
        # Create analyzer with config
        similarity_config = {
            "similarity": {
                "method": self.config.similarity_method,
                "similarity_threshold": self.config.similarity_threshold,
                "enable_clustering": self.config.enable_clustering,
            },
            "exclude_patterns": self.config.exclude_patterns,
        }
        
        analyzer = create_similarity_analyzer(similarity_config)
        result = analyzer.analyze(path)
        
        if result.success and isinstance(result.data, SimilarityResults):
            return result.data
        else:
            # Return empty results on failure
            results = SimilarityResults()
            return results
    
    def analyze_references(self, path: Path) -> ReferenceResults:
        """Run reference validation."""
        from ..analyzers import ReferenceValidator
        
        # Create analyzer with config
        ref_config = {
            "check_external_links": self.config.check_external_links,
            "check_images": self.config.check_images,
            "check_anchors": self.config.check_anchors,
            "exclude_patterns": self.config.exclude_patterns,
        }
        
        analyzer = ReferenceValidator(ref_config)
        result = analyzer.analyze(path)
        
        if result.success and isinstance(result.data, ReferenceResults):
            return result.data
        else:
            # Return empty results on failure
            results = ReferenceResults()
            return results
    
    def analyze_instructions(self, path: Path) -> InstructionResults:
        """
        Run instruction path tracing.
        
        For now, returns a placeholder. Will be implemented when we
        refactor the instruction tracer.
        """
        # TODO: Import and use actual instruction tracer
        results = InstructionResults()
        
        logger.info("Instruction tracing placeholder")
        
        return results
    
    def check_structure(self, path: Path) -> List[Issue]:
        """
        Check structural soundness of documents.
        
        For now, returns empty list. Will be implemented when we
        refactor the structure checker.
        """
        # TODO: Import and use actual structure checker
        issues = []
        
        logger.info("Structure check placeholder")
        
        return issues