"""Semantic similarity calculation using sentence transformers.

This module implements similarity calculation using SentenceTransformer
for deep semantic understanding and vector-based similarity analysis.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sentence_transformers import SentenceTransformer, util

from ..analyzers import load_markdown_files
from ..config import DEFAULT_MODEL_NAME, SIMILARITY_THRESHOLD_HIGH, SIMILARITY_THRESHOLD_LOW, SIMILARITY_THRESHOLD_MEDIUM
from ..validation import ValidationError, validate_file_path, validate_list_input, validate_threshold
from .base import BaseSimilarityCalculator, ClusteringMixin, SimilarityResult

logger = logging.getLogger(__name__)


class SemanticSimilarityCalculator(BaseSimilarityCalculator, ClusteringMixin):
    """Semantic similarity calculator using sentence transformers.

    Uses SentenceTransformer models to create embeddings and calculate
    cosine similarity for deep semantic understanding.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, **kwargs: Any) -> None:
        """Initialize semantic similarity calculator.

        Args:
            model_name: Name of the SentenceTransformer model to use
            **kwargs: Additional configuration parameters
        """
        super().__init__("SemanticSimilarity", model_name=model_name, **kwargs)
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

        logger.debug(f"Configured semantic similarity with model: {model_name}")

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the SentenceTransformer model."""
        if self._model is None:
            try:
                logger.info(f"Loading SentenceTransformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise RuntimeError(f"Failed to load model {self.model_name}") from e
        return self._model

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using embeddings.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Generate embeddings
            embeddings = self.model.encode([text1, text2], convert_to_tensor=True, show_progress_bar=False)

            # Calculate cosine similarity
            cosine_scores = util.pytorch_cos_sim(embeddings[0:1], embeddings[1:2])
            score = float(cosine_scores[0][0])

            return max(0.0, min(1.0, score))  # Clamp to [0.0, 1.0]

        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.0

    def calculate_matrix(self, texts: list[str], threshold: float = 0.0) -> pd.DataFrame:
        """Calculate pairwise similarity matrix using embeddings.

        Args:
            texts: List of texts to compare
            threshold: Minimum similarity score to include in results

        Returns:
            Pandas DataFrame with similarity matrix

        Raises:
            ValidationError: If input validation fails
            ValueError: If texts list is empty
        """
        # Validate inputs
        if not texts:
            raise ValueError("Text list cannot be empty")

        if not 0.0 <= threshold <= 1.0:
            raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        for i, text in enumerate(texts):
            self._validate_text_input(text, f"texts[{i}]")

        try:
            # Generate embeddings for all texts
            embeddings = self.model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

            # Calculate full similarity matrix
            cosine_scores = util.pytorch_cos_sim(embeddings, embeddings)

            # Convert to numpy and apply threshold
            matrix = cosine_scores.cpu().numpy()
            matrix[matrix < threshold] = 0.0

            # Create DataFrame with text indices as labels
            text_labels = [f"text_{i}" for i in range(len(texts))]
            return pd.DataFrame(matrix, index=text_labels, columns=text_labels)

        except Exception as e:
            logger.error(f"Failed to calculate semantic similarity matrix: {e}")
            raise RuntimeError("Failed to calculate similarity matrix") from e

    def find_similar_documents(
        self, query_docs: list[Path], candidate_docs: list[Path], root_dir: Path, threshold: float = 0.5
    ) -> list[SimilarityResult]:
        """Find documents similar to query documents using semantic embeddings.

        Args:
            query_docs: Documents to find similarities for
            candidate_docs: Documents to search within
            root_dir: Root directory for file loading
            threshold: Minimum similarity score to include

        Returns:
            List of similarity results above threshold

        Raises:
            ValidationError: If input validation fails
            FileNotFoundError: If documents cannot be loaded
        """
        # Validate inputs
        if not query_docs:
            raise ValidationError("Query documents list cannot be empty")
        if not candidate_docs:
            raise ValidationError("Candidate documents list cannot be empty")

        try:
            root_dir = validate_file_path(root_dir, must_exist=True)
        except ValidationError as e:
            raise ValidationError(f"Invalid root directory: {e}") from e

        if not 0.0 <= threshold <= 1.0:
            raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        # Load documents
        try:
            query_files = load_markdown_files(query_docs, root_dir)
            candidate_files = load_markdown_files(candidate_docs, root_dir)
        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
            raise FileNotFoundError("Could not load documents") from e

        if not query_files or not candidate_files:
            logger.warning("No files to analyze after loading")
            return []

        try:
            # Generate embeddings
            logger.debug("Generating embeddings for similarity search...")
            query_embeddings = self.model.encode(list(query_files.values()), convert_to_tensor=True, show_progress_bar=False)
            candidate_embeddings = self.model.encode(
                list(candidate_files.values()), convert_to_tensor=True, show_progress_bar=False
            )

            # Calculate similarities
            cosine_scores = util.pytorch_cos_sim(query_embeddings, candidate_embeddings)

        except Exception as e:
            logger.error(f"Failed to generate embeddings or calculate similarities: {e}")
            raise RuntimeError("Failed to process documents for similarity") from e

        results = []
        query_paths = list(query_files.keys())
        candidate_paths = list(candidate_files.keys())

        # Extract results above threshold
        for i, query_path in enumerate(query_paths):
            for j, candidate_path in enumerate(candidate_paths):
                # Skip self-comparison
                if query_path == candidate_path:
                    continue

                score = float(cosine_scores[i][j])

                if score >= threshold:
                    result = SimilarityResult(
                        source=query_path,
                        target=candidate_path,
                        score=score,
                        technique="semantic_embedding",
                        metadata={
                            "model": self.model_name,
                            "query_length": len(query_files[query_path]),
                            "candidate_length": len(candidate_files[candidate_path]),
                        },
                    )
                    results.append(result)

        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(results)} semantically similar document pairs above threshold {threshold}")
        return results


def analyze_semantic_similarity(
    not_in_use_docs: list[Path],
    active_docs: list[Path],
    root_dir: Path,
    threshold: float | None = None,
    model: SentenceTransformer | None = None,
) -> pd.DataFrame:
    """Analyze semantic similarity between not_in_use and active documents.

    Legacy function for backward compatibility. Consider using
    SemanticSimilarityCalculator.find_similar_documents() instead.

    Args:
        not_in_use_docs: List of not_in_use document paths
        active_docs: List of active document paths
        root_dir: Root directory for relative path calculation
        threshold: Minimum similarity score to consider
        model: Pre-loaded SentenceTransformer model (optional)

    Returns:
        DataFrame with columns: not_in_use, matched_file, similarity

    Raises:
        ValidationError: If input validation fails
        RuntimeError: If model loading or encoding fails
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_LOW

    # Use calculator for consistent behavior
    calculator = SemanticSimilarityCalculator()
    if model is not None:
        calculator._model = model

    try:
        results = calculator.find_similar_documents(not_in_use_docs, active_docs, root_dir, threshold)
    except Exception as e:
        logger.error(f"Semantic similarity analysis failed: {e}")
        raise

    # Convert to legacy DataFrame format
    data = []
    for result in results:
        data.append({"not_in_use": result.source, "matched_file": result.target, "similarity": result.score})

    return pd.DataFrame(data)


def create_similarity_matrix(
    documents: list[Path],
    root_dir: Path,
    model: SentenceTransformer | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Create a full similarity matrix for a set of documents.

    Legacy function for backward compatibility. Consider using
    SemanticSimilarityCalculator.calculate_matrix() instead.

    Args:
        documents: List of document paths
        root_dir: Root directory for relative path calculation
        model: Pre-loaded SentenceTransformer model (optional)

    Returns:
        Tuple of (similarity_matrix_df, document_names)

    Raises:
        ValidationError: If input validation fails
        RuntimeError: If model operations fail
    """
    logger.info(f"Creating similarity matrix for {len(documents)} documents")

    # Validate inputs
    try:
        documents = validate_list_input(
            documents, "documents", min_length=1, item_validator=lambda p: validate_file_path(p, must_exist=True)
        )
    except ValidationError as e:
        logger.error(f"Document validation failed: {e}")
        raise

    # Load documents
    try:
        files = load_markdown_files(documents, root_dir)
    except Exception as e:
        logger.error(f"Failed to load files: {e}")
        raise RuntimeError("Failed to load document files") from e

    file_names = list(files.keys())

    if len(files) < 2:
        logger.warning("Need at least 2 documents for similarity matrix")
        return pd.DataFrame(), []

    # Use calculator
    calculator = SemanticSimilarityCalculator()
    if model is not None:
        calculator._model = model

    try:
        # Calculate matrix using document contents
        texts = list(files.values())
        matrix_df = calculator.calculate_matrix(texts, threshold=0.0)

        # Update DataFrame with actual file names
        matrix_df.index = file_names
        matrix_df.columns = file_names

        return matrix_df, file_names

    except Exception as e:
        logger.error(f"Failed to create similarity matrix: {e}")
        raise RuntimeError("Failed to create similarity matrix") from e


def find_embeddings_clusters(similarity_matrix: pd.DataFrame, threshold: float | None = None) -> list[list[str]]:
    """Find clusters of similar items in similarity matrix.

    Legacy function for backward compatibility. Consider using
    SemanticSimilarityCalculator with ClusteringMixin instead.

    Args:
        similarity_matrix: Similarity matrix DataFrame
        threshold: Minimum similarity for clustering

    Returns:
        List of clusters, where each cluster is a list of document names

    Raises:
        ValidationError: If threshold validation fails
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_MEDIUM

    try:
        threshold = validate_threshold(threshold, "clustering_threshold")
    except ValidationError as e:
        logger.error(f"Invalid threshold: {e}")
        raise

    calculator = SemanticSimilarityCalculator()

    # Get cluster indices
    index_clusters = calculator.find_clusters(similarity_matrix, threshold)

    # Convert indices to document names
    document_names = list(similarity_matrix.index)
    name_clusters = []

    for cluster in index_clusters:
        name_cluster = [document_names[i] for i in cluster]
        name_clusters.append(name_cluster)

    logger.info(f"Found {len(name_clusters)} semantic clusters with threshold {threshold}")
    return name_clusters


def analyze_active_document_similarities(
    active_docs: list[Path],
    root_dir: str | Path,
    threshold: float | None = None,
    exclude_self: bool = True,
    model: SentenceTransformer | None = None,
) -> pd.DataFrame:
    """Analyze semantic similarity among active documents to find potential duplicates.

    This helps identify remaining overlaps and duplications among the "good" documents.

    Args:
        active_docs: List of active document paths
        root_dir: Root directory for relative path calculation
        threshold: Minimum similarity score to consider (defaults to SIMILARITY_THRESHOLD_LOW)
        exclude_self: Whether to exclude self-comparisons (default: True)
        model: Pre-loaded SentenceTransformer model (optional)

    Returns:
        DataFrame with columns: doc1, doc2, similarity, relationship_type

    Raises:
        ValidationError: If input validation fails
        RuntimeError: If model operations fail

    Example:
        >>> df = analyze_active_document_similarities(
        ...     [Path("doc1.md"), Path("doc2.md")],
        ...     Path(".")
        ... )
        >>> 'relationship_type' in df.columns
        True
    """
    # Validate inputs
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_LOW
    else:
        try:
            threshold = validate_threshold(threshold, "similarity_threshold")
        except ValidationError as e:
            logger.error(f"Invalid threshold: {e}")
            raise

    logger.info(f"Analyzing similarities among {len(active_docs)} active documents...")

    if len(active_docs) < 2:
        logger.warning("Need at least 2 documents to compare")
        return pd.DataFrame(columns=["doc1", "doc2", "similarity", "relationship_type"])

    # Validate document paths
    try:
        active_docs = validate_list_input(
            active_docs, "active_docs", min_length=2, item_validator=lambda p: validate_file_path(p, must_exist=True)
        )
    except ValidationError as e:
        logger.error(f"Document validation failed: {e}")
        raise

    # Load file contents
    try:
        active_files = load_markdown_files(active_docs, root_dir)
    except Exception as e:
        logger.error(f"Failed to load files: {e}")
        raise RuntimeError("Failed to load document files") from e

    if len(active_files) < 2:
        logger.warning("Insufficient files to analyze after loading")
        return pd.DataFrame(columns=["doc1", "doc2", "similarity", "relationship_type"])

    # Create embeddings
    if model is None:
        logger.info(f"Loading SentenceTransformer model: {DEFAULT_MODEL_NAME}")
        try:
            model = SentenceTransformer(DEFAULT_MODEL_NAME)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load model {DEFAULT_MODEL_NAME}") from e

    file_names = list(active_files.keys())
    logger.info(f"Generating embeddings for {len(file_names)} documents...")

    try:
        embeddings = model.encode(list(active_files.values()), convert_to_tensor=True, show_progress_bar=False)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise RuntimeError("Failed to generate document embeddings") from e

    # Calculate pairwise similarities efficiently
    logger.info("Computing similarity matrix...")
    try:
        cosine_scores = util.pytorch_cos_sim(embeddings, embeddings)
    except Exception as e:
        logger.error(f"Failed to compute similarities: {e}")
        raise RuntimeError("Failed to compute similarity matrix") from e

    results: list[dict[str, Any]] = []
    n_docs = len(file_names)

    logger.info(f"Comparing {n_docs * (n_docs - 1) // 2} document pairs...")

    for i in range(n_docs):
        for j in range(i + 1 if exclude_self else i, n_docs):
            if exclude_self and i == j:
                continue

            score = float(cosine_scores[i][j])
            if score >= threshold:
                doc1, doc2 = file_names[i], file_names[j]

                # Classify relationship type based on similarity score
                if score >= SIMILARITY_THRESHOLD_HIGH:
                    relationship_type = "NEAR_DUPLICATE"
                elif score >= SIMILARITY_THRESHOLD_MEDIUM:
                    relationship_type = "HIGH_OVERLAP"
                elif score >= SIMILARITY_THRESHOLD_LOW:
                    relationship_type = "MODERATE_OVERLAP"
                else:
                    relationship_type = "LOW_SIMILARITY"

                results.append({"doc1": doc1, "doc2": doc2, "similarity": score, "relationship_type": relationship_type})

    # Sort by similarity score (highest first)
    results.sort(key=lambda x: x["similarity"], reverse=True)

    logger.info(f"Found {len(results)} similar document pairs")
    return pd.DataFrame(results)
