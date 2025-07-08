"""Document similarity analyzers with optional NLP support."""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
import logging

from ...models import (
    SimilarityResults,
    SimilarDocumentPair,
    DocumentInfo,
)
from ..base import BaseAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class SimilarityConfig:
    """Configuration for similarity analysis."""
    
    # Method selection
    method: str = "string"  # "string", "semantic", or "both"
    
    # Thresholds
    similarity_threshold: float = 0.75
    duplicate_threshold: float = 0.95
    
    # String similarity settings
    string_algorithm: str = "token_sort"  # rapidfuzz algorithm
    
    # Semantic similarity settings (if available)
    semantic_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    
    # Performance settings
    enable_caching: bool = True
    max_file_size_mb: float = 5.0
    
    # Clustering
    enable_clustering: bool = True
    min_cluster_size: int = 2


class StringSimilarityAnalyzer(BaseAnalyzer):
    """Analyzer for string-based document similarity using rapidfuzz."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize analyzer."""
        super().__init__(config)
        sim_config = config.get("similarity", {}) if config else {}
        self.sim_config = SimilarityConfig(**sim_config)
        
        # Check if rapidfuzz is available
        try:
            import rapidfuzz
            self.rapidfuzz = rapidfuzz
        except ImportError:
            raise ImportError(
                "rapidfuzz is required for similarity analysis. "
                "Install with: pip install docpipe"
            )
    
    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "StringSimilarityAnalyzer"
    
    @property
    def description(self) -> str:
        """Get analyzer description."""
        return "Analyzes document similarity using string matching algorithms"
    
    def _analyze_impl(self, path: Path) -> SimilarityResults:
        """Analyze documents for similarity."""
        # Discover and load documents
        documents = self._discover_documents(path)
        contents = self._load_documents(documents)
        
        # Calculate similarity
        results = SimilarityResults(documents_analyzed=len(documents))
        
        if len(documents) < 2:
            return results
        
        # Compare all document pairs
        doc_paths = list(contents.keys())
        for i in range(len(doc_paths)):
            for j in range(i + 1, len(doc_paths)):
                path1, path2 = doc_paths[i], doc_paths[j]
                content1, content2 = contents[path1], contents[path2]
                
                # Calculate similarity
                score = self._calculate_string_similarity(content1, content2)
                
                if score >= self.sim_config.similarity_threshold:
                    results.similar_pairs.append(SimilarDocumentPair(
                        source=Path(path1),
                        target=Path(path2),
                        similarity_score=score,
                        similarity_method="string",
                        metadata={"algorithm": self.sim_config.string_algorithm}
                    ))
        
        # Find duplicate groups if clustering enabled
        if self.sim_config.enable_clustering:
            results.duplicate_groups = self._find_duplicate_groups(results.similar_pairs)
        
        return results
    
    def _discover_documents(self, path: Path) -> List[Path]:
        """Discover markdown documents."""
        documents = []
        
        if path.is_file() and path.suffix in ['.md', '.markdown']:
            documents.append(path)
        elif path.is_dir():
            for pattern in ['*.md', '*.markdown']:
                documents.extend(path.rglob(pattern))
        
        # Filter out excluded paths
        exclude_patterns = self.config.get("exclude_patterns", [])
        documents = [
            doc for doc in documents 
            if not self._should_exclude(doc, exclude_patterns)
        ]
        
        return sorted(documents)
    
    def _load_documents(self, documents: List[Path]) -> Dict[str, str]:
        """Load document contents."""
        contents = {}
        
        for doc in documents:
            try:
                # Check file size
                size_mb = doc.stat().st_size / (1024 * 1024)
                if size_mb > self.sim_config.max_file_size_mb:
                    logger.warning(f"Skipping large file: {doc} ({size_mb:.1f} MB)")
                    continue
                
                # Load content
                content = doc.read_text(encoding='utf-8')
                contents[str(doc)] = content
                
            except Exception as e:
                logger.error(f"Error loading {doc}: {e}")
        
        return contents
    
    def _calculate_string_similarity(self, text1: str, text2: str) -> float:
        """Calculate string similarity score."""
        if not text1 or not text2:
            return 0.0
        
        # Use rapidfuzz for similarity calculation
        if self.sim_config.string_algorithm == "token_sort":
            score = self.rapidfuzz.fuzz.token_sort_ratio(text1, text2) / 100.0
        elif self.sim_config.string_algorithm == "token_set":
            score = self.rapidfuzz.fuzz.token_set_ratio(text1, text2) / 100.0
        elif self.sim_config.string_algorithm == "partial":
            score = self.rapidfuzz.fuzz.partial_ratio(text1, text2) / 100.0
        else:
            # Default to simple ratio
            score = self.rapidfuzz.fuzz.ratio(text1, text2) / 100.0
        
        return score
    
    def _find_duplicate_groups(self, similar_pairs: List[SimilarDocumentPair]) -> List[List[Path]]:
        """Find groups of duplicate documents."""
        # Build adjacency list for documents with high similarity
        adjacency: Dict[Path, Set[Path]] = {}
        
        for pair in similar_pairs:
            if pair.similarity_score >= self.sim_config.duplicate_threshold:
                if pair.source not in adjacency:
                    adjacency[pair.source] = set()
                if pair.target not in adjacency:
                    adjacency[pair.target] = set()
                
                adjacency[pair.source].add(pair.target)
                adjacency[pair.target].add(pair.source)
        
        # Find connected components (duplicate groups)
        visited = set()
        groups = []
        
        for doc in adjacency:
            if doc not in visited:
                group = self._dfs_group(doc, adjacency, visited)
                if len(group) >= self.sim_config.min_cluster_size:
                    groups.append(sorted(group))
        
        return groups
    
    def _dfs_group(self, start: Path, adjacency: Dict[Path, Set[Path]], visited: Set[Path]) -> List[Path]:
        """Depth-first search to find connected component."""
        stack = [start]
        group = []
        
        while stack:
            doc = stack.pop()
            if doc not in visited:
                visited.add(doc)
                group.append(doc)
                
                if doc in adjacency:
                    stack.extend(adjacency[doc] - visited)
        
        return group


class SemanticSimilarityAnalyzer(BaseAnalyzer):
    """Analyzer for semantic document similarity using embeddings."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize analyzer."""
        super().__init__(config)
        sim_config = config.get("similarity", {}) if config else {}
        self.sim_config = SimilarityConfig(**sim_config)
        
        # Check if sentence-transformers is available
        self.sentence_transformers = None
        try:
            import sentence_transformers
            self.sentence_transformers = sentence_transformers
            self.model = None  # Lazy load
        except ImportError:
            logger.info(
                "sentence-transformers not available. "
                "Install with: pip install docpipe[nlp]"
            )
    
    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "SemanticSimilarityAnalyzer"
    
    @property
    def description(self) -> str:
        """Get analyzer description."""
        return "Analyzes document similarity using semantic embeddings"
    
    def validate_config(self) -> List[str]:
        """Validate configuration."""
        warnings = []
        
        if not self.sentence_transformers:
            warnings.append(
                "Semantic similarity requested but sentence-transformers not installed. "
                "Install with: pip install docpipe[nlp]"
            )
        
        return warnings
    
    def _analyze_impl(self, path: Path) -> SimilarityResults:
        """Analyze documents for semantic similarity."""
        # Check if semantic analysis is available
        if not self.sentence_transformers:
            logger.warning("Semantic similarity not available, returning empty results")
            return SimilarityResults()
        
        # Lazy load model
        if self.model is None:
            logger.info(f"Loading semantic model: {self.sim_config.semantic_model}")
            self.model = self.sentence_transformers.SentenceTransformer(
                self.sim_config.semantic_model
            )
        
        # Discover and load documents
        documents = self._discover_documents(path)
        contents = self._load_documents(documents)
        
        if len(documents) < 2:
            return SimilarityResults(documents_analyzed=len(documents))
        
        # Generate embeddings
        doc_paths = list(contents.keys())
        texts = [contents[p] for p in doc_paths]
        
        logger.info(f"Generating embeddings for {len(texts)} documents...")
        embeddings = self.model.encode(
            texts,
            batch_size=self.sim_config.batch_size,
            show_progress_bar=False
        )
        
        # Calculate cosine similarity
        results = SimilarityResults(documents_analyzed=len(documents))
        
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarity_matrix = cosine_similarity(embeddings)
        
        # Extract similar pairs
        for i in range(len(doc_paths)):
            for j in range(i + 1, len(doc_paths)):
                score = float(similarity_matrix[i, j])
                
                if score >= self.sim_config.similarity_threshold:
                    results.similar_pairs.append(SimilarDocumentPair(
                        source=Path(doc_paths[i]),
                        target=Path(doc_paths[j]),
                        similarity_score=score,
                        similarity_method="semantic",
                        metadata={"model": self.sim_config.semantic_model}
                    ))
        
        # Find duplicate groups if clustering enabled
        if self.sim_config.enable_clustering:
            # Reuse the same clustering logic from string analyzer
            string_analyzer = StringSimilarityAnalyzer(self.config)
            results.duplicate_groups = string_analyzer._find_duplicate_groups(
                results.similar_pairs
            )
        
        return results
    
    def _discover_documents(self, path: Path) -> List[Path]:
        """Discover markdown documents (same as string analyzer)."""
        string_analyzer = StringSimilarityAnalyzer(self.config)
        return string_analyzer._discover_documents(path)
    
    def _load_documents(self, documents: List[Path]) -> Dict[str, str]:
        """Load document contents (same as string analyzer)."""
        string_analyzer = StringSimilarityAnalyzer(self.config)
        return string_analyzer._load_documents(documents)


class CombinedSimilarityAnalyzer(BaseAnalyzer):
    """Analyzer that combines string and semantic similarity."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize analyzer."""
        super().__init__(config)
        self.string_analyzer = StringSimilarityAnalyzer(config)
        self.semantic_analyzer = SemanticSimilarityAnalyzer(config)
        
        sim_config = config.get("similarity", {}) if config else {}
        self.sim_config = SimilarityConfig(**sim_config)
    
    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "CombinedSimilarityAnalyzer"
    
    @property
    def description(self) -> str:
        """Get analyzer description."""
        return "Analyzes document similarity using both string and semantic methods"
    
    def validate_config(self) -> List[str]:
        """Validate configuration."""
        warnings = []
        warnings.extend(self.string_analyzer.validate_config())
        warnings.extend(self.semantic_analyzer.validate_config())
        return warnings
    
    def _analyze_impl(self, path: Path) -> SimilarityResults:
        """Analyze with both methods and combine results."""
        # Run both analyzers
        string_results = self.string_analyzer._analyze_impl(path)
        semantic_results = self.semantic_analyzer._analyze_impl(path)
        
        # Combine results
        combined = SimilarityResults(
            documents_analyzed=max(
                string_results.documents_analyzed,
                semantic_results.documents_analyzed
            )
        )
        
        # Merge similar pairs, keeping highest score
        pair_scores: Dict[Tuple[str, str], SimilarDocumentPair] = {}
        
        for pair in string_results.similar_pairs + semantic_results.similar_pairs:
            key = (str(pair.source), str(pair.target))
            if key[0] > key[1]:  # Normalize order
                key = (key[1], key[0])
            
            if key not in pair_scores or pair.similarity_score > pair_scores[key].similarity_score:
                pair_scores[key] = pair
        
        combined.similar_pairs = list(pair_scores.values())
        
        # Combine duplicate groups
        all_groups = string_results.duplicate_groups + semantic_results.duplicate_groups
        if all_groups:
            # Merge overlapping groups
            combined.duplicate_groups = self._merge_duplicate_groups(all_groups)
        
        return combined
    
    def _merge_duplicate_groups(self, groups: List[List[Path]]) -> List[List[Path]]:
        """Merge overlapping duplicate groups."""
        # Convert to sets for easier merging
        group_sets = [set(group) for group in groups]
        merged = []
        
        while group_sets:
            current = group_sets.pop(0)
            merged_any = True
            
            while merged_any:
                merged_any = False
                for i in range(len(group_sets) - 1, -1, -1):
                    if current & group_sets[i]:  # Overlap found
                        current |= group_sets.pop(i)
                        merged_any = True
            
            merged.append(sorted(list(current)))
        
        return merged


def create_similarity_analyzer(config: Optional[Dict[str, Any]] = None) -> BaseAnalyzer:
    """Factory function to create appropriate similarity analyzer based on config."""
    sim_config = config.get("similarity", {}) if config else {}
    method = sim_config.get("method", "string")
    
    if method == "string":
        return StringSimilarityAnalyzer(config)
    elif method == "semantic":
        # Check if semantic is available
        analyzer = SemanticSimilarityAnalyzer(config)
        if analyzer.validate_config():
            # Fall back to string if semantic not available
            logger.warning("Semantic similarity not available, using string similarity")
            return StringSimilarityAnalyzer(config)
        return analyzer
    elif method == "both":
        return CombinedSimilarityAnalyzer(config)
    else:
        raise ValueError(f"Unknown similarity method: {method}")