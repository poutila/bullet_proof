#!/usr/bin/env python3
"""Semantic similarity analysis using sentence transformers.

This module provides document embedding and similarity analysis capabilities
using sentence transformers, following CLAUDE.md security and quality standards.
"""

import logging
from pathlib import Path
from typing import Any, cast

import pandas as pd
from sentence_transformers import SentenceTransformer, util

from document_analysis.analyzers import load_markdown_files
from document_analysis.config import (
    DEFAULT_MODEL_NAME,
    SIMILARITY_THRESHOLD_HIGH,
    SIMILARITY_THRESHOLD_LOW,
    SIMILARITY_THRESHOLD_MEDIUM,
)
from src.validation.validation import ValidationError, validate_file_path, validate_list_input, validate_threshold

logger = logging.getLogger(__name__)


def analyze_semantic_similarity(
    not_in_use_docs: list[Path],
    active_docs: list[Path],
    root_dir: str | Path,
    threshold: float | None = None,
    model: SentenceTransformer | None = None,
) -> pd.DataFrame:
    """Analyze semantic similarity between not_in_use and active documents.

    Compares documents in not_in_use folders against active documents to find
    potential duplicates or highly similar content.

    Args:
        not_in_use_docs: List of not_in_use document paths
        active_docs: List of active document paths
        root_dir: Root directory for relative path calculation
        threshold: Minimum similarity score to consider (defaults to SIMILARITY_THRESHOLD_LOW)
        model: Pre-loaded SentenceTransformer model (optional)

    Returns:
        DataFrame with columns: not_in_use, matched_file, similarity

    Raises:
        ValidationError: If input validation fails
        RuntimeError: If model loading or encoding fails

    Example:
        >>> df = analyze_semantic_similarity(
        ...     [Path("not_in_use/old.md")],
        ...     [Path("active.md")],
        ...     Path(".")
        ... )
        >>> 'similarity' in df.columns
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

    # Validate document lists
    try:
        not_in_use_docs = validate_list_input(
            not_in_use_docs, "not_in_use_docs", min_length=1, item_validator=lambda p: validate_file_path(p, must_exist=True)
        )
        active_docs = validate_list_input(
            active_docs, "active_docs", min_length=1, item_validator=lambda p: validate_file_path(p, must_exist=True)
        )
    except ValidationError as e:
        logger.error(f"Document list validation failed: {e}")
        raise

    logger.info(f"Analyzing semantic similarity: {len(not_in_use_docs)} not_in_use vs {len(active_docs)} active docs")

    # Load file contents
    try:
        not_in_use_files = load_markdown_files(not_in_use_docs, root_dir)
        reference_files = load_markdown_files(active_docs, root_dir)
    except Exception as e:
        logger.error(f"Failed to load files: {e}")
        raise RuntimeError("Failed to load document files") from e

    if not not_in_use_files or not reference_files:
        logger.warning("No files to analyze after loading")
        return pd.DataFrame(columns=["not_in_use", "matched_file", "similarity"])

    # Create embeddings
    if model is None:
        logger.info(f"Loading SentenceTransformer model: {DEFAULT_MODEL_NAME}")
        try:
            model = SentenceTransformer(DEFAULT_MODEL_NAME)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load model {DEFAULT_MODEL_NAME}") from e

    logger.info("Generating embeddings...")
    try:
        not_in_use_emb = model.encode(list(not_in_use_files.values()), convert_to_tensor=True, show_progress_bar=False)
        ref_emb = model.encode(list(reference_files.values()), convert_to_tensor=True, show_progress_bar=False)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise RuntimeError("Failed to generate document embeddings") from e

    # Calculate similarities
    logger.info("Calculating cosine similarities...")
    try:
        cosine_scores = util.pytorch_cos_sim(not_in_use_emb, ref_emb)
    except Exception as e:
        logger.error(f"Failed to calculate similarities: {e}")
        raise RuntimeError("Failed to calculate cosine similarities") from e

    # Find matches above threshold
    results: list[dict[str, Any]] = []
    ni_names = list(not_in_use_files.keys())
    ref_names = list(reference_files.keys())

    for i, ni in enumerate(ni_names):
        best_score = 0.0
        best_match = ""

        for j, ref in enumerate(ref_names):
            score = float(cosine_scores[i][j])
            if score > best_score:
                best_score = score
                best_match = ref

        if best_score >= threshold:
            results.append({"not_in_use": ni, "matched_file": best_match, "similarity": best_score})

    logger.info(f"Found {len(results)} matches above threshold {threshold:.2f}")
    return pd.DataFrame(results)


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
    results.sort(key=lambda x: cast("float", x["similarity"]), reverse=True)

    logger.info(f"Found {len(results)} similar document pairs")
    return pd.DataFrame(results)


def create_similarity_matrix(
    documents: list[Path],
    root_dir: str | Path,
    model: SentenceTransformer | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Create a full similarity matrix for a set of documents.

    Args:
        documents: List of document paths
        root_dir: Root directory for relative path calculation
        model: Pre-loaded SentenceTransformer model (optional)

    Returns:
        Tuple of (similarity_matrix_df, document_names)

    Raises:
        ValidationError: If input validation fails
        RuntimeError: If model operations fail

    Example:
        >>> matrix, names = create_similarity_matrix(
        ...     [Path("doc1.md"), Path("doc2.md")],
        ...     Path(".")
        ... )
        >>> matrix.shape[0] == matrix.shape[1]
        True
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

    # Create embeddings
    if model is None:
        logger.info(f"Loading SentenceTransformer model: {DEFAULT_MODEL_NAME}")
        try:
            model = SentenceTransformer(DEFAULT_MODEL_NAME)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Failed to load model {DEFAULT_MODEL_NAME}") from e

    try:
        embeddings = model.encode(list(files.values()), convert_to_tensor=True, show_progress_bar=False)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise RuntimeError("Failed to generate document embeddings") from e

    # Calculate full similarity matrix
    try:
        cosine_scores = util.pytorch_cos_sim(embeddings, embeddings)
    except Exception as e:
        logger.error(f"Failed to compute similarities: {e}")
        raise RuntimeError("Failed to compute similarity matrix") from e

    # Convert to pandas DataFrame
    try:
        similarity_matrix = pd.DataFrame(cosine_scores.cpu().numpy(), index=file_names, columns=file_names)
    except Exception as e:
        logger.error(f"Failed to create DataFrame: {e}")
        raise RuntimeError("Failed to create similarity DataFrame") from e

    return similarity_matrix, file_names


def find_embeddings_clusters(similarity_matrix: pd.DataFrame, threshold: float | None = None) -> list[list[str]]:
    """Find clusters of similar documents from similarity matrix.

    Uses a greedy clustering approach to group documents with similarity
    scores above the threshold.

    Args:
        similarity_matrix: Square similarity matrix DataFrame
        threshold: Minimum similarity to consider as cluster members (defaults to SIMILARITY_THRESHOLD_MEDIUM)

    Returns:
        List of document name clusters

    Raises:
        ValidationError: If inputs are invalid
        ValueError: If matrix is not square or empty

    Example:
        >>> matrix = pd.DataFrame([[1.0, 0.9], [0.9, 1.0]])
        >>> clusters = find_embeddings_clusters(matrix, 0.85)
        >>> len(clusters) > 0
        True
    """
    if similarity_matrix.empty:
        raise ValueError("Similarity matrix cannot be empty")

    if similarity_matrix.shape[0] != similarity_matrix.shape[1]:
        raise ValueError(f"Matrix must be square. Got shape {similarity_matrix.shape}")

    # Validate threshold
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_MEDIUM
    else:
        try:
            threshold = validate_threshold(threshold, "cluster_threshold")
        except ValidationError as e:
            logger.error(f"Invalid threshold: {e}")
            raise

    document_names = similarity_matrix.index.tolist()
    visited: set[str] = set()
    clusters: list[list[str]] = []

    for doc in document_names:
        if doc in visited:
            continue

        # Find all documents similar to this one
        try:
            similar_docs = similarity_matrix[doc]
        except KeyError as e:
            logger.error(f"Document {doc} not found in matrix")
            raise ValueError(f"Document {doc} not found in matrix") from e

        cluster_members = [doc]

        for other_doc in document_names:
            if other_doc != doc and similar_docs[other_doc] >= threshold:
                cluster_members.append(other_doc)
                visited.add(other_doc)

        if len(cluster_members) > 1:
            clusters.append(cluster_members)
            visited.update(cluster_members)
            logger.debug(f"Found cluster with {len(cluster_members)} members")
        else:
            visited.add(doc)

    logger.info(f"Found {len(clusters)} clusters with threshold {threshold:.2f}")
    return clusters
