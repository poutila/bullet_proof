#!/usr/bin/env python3
"""Document matching and analysis utilities.

This module provides tools for:
- Finding and analyzing document similarities
- Semantic embedding-based comparison
- Fuzzy text matching and merging
- Content embedding verification
- Document deduplication workflows

Main modules:
- similarity: Unified similarity analysis interfaces and implementations
  - string_similarity: String-based fuzzy matching algorithms
  - semantic_similarity: Embedding-based semantic comparison
- analyzers: Document discovery and content loading
- merging: Document merging and deduplication
- reports: Analysis reporting and export
- config: Configuration constants and settings
- validation: Input validation and security
"""

from .analyzers import find_active_documents, find_not_in_use_documents, load_markdown_files
from .merging import merge_documents, merge_similar_documents
from .reports import (
    check_content_embedding,
    export_similarity_report,
    generate_comprehensive_similarity_report,
)
from .similarity.semantic_similarity import analyze_active_document_similarities, analyze_semantic_similarity
from .similarity.string_similarity import get_best_match_seq, is_similar, split_sections

__version__ = "1.0.0"

__all__: list[str] = [
    # Version
    "__version__",
    # Embeddings
    "analyze_active_document_similarities",
    "analyze_semantic_similarity",
    # Reports
    "check_content_embedding",
    "export_similarity_report",
    # Analyzers
    "find_active_documents",
    "find_not_in_use_documents",
    "generate_comprehensive_similarity_report",
    # Core
    "get_best_match_seq",
    "is_similar",
    "load_markdown_files",
    # Merging
    "merge_documents",
    "merge_similar_documents",
    "split_sections",
]
