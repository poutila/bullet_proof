"""Document analysis reporting and content embedding verification."""

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
from rapidfuzz import fuzz

from .embeddings import analyze_active_document_similarities, analyze_semantic_similarity

# Import markdown analyzer if available
from .markdown_analyzer import MarkdownAnalyzer, compare_markdown_blocks

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def _analyze_markdown_content(
    not_in_use_content: str,
    matched_content: str,
    *,
    not_in_use_path: str,
    matched_path: str,
    similarity: float,
) -> dict[str, Any]:
    """Analyze content using markdown-aware comparison."""
    analyzer = MarkdownAnalyzer()

    # Extract markdown blocks
    source_blocks = analyzer.extract_blocks(not_in_use_content)
    target_blocks = analyzer.extract_blocks(matched_content)

    # Compare blocks
    block_comparison = compare_markdown_blocks(source_blocks, target_blocks, fuzzy_threshold=0.8)

    # Use markdown-aware results
    total_blocks = len(source_blocks)
    exact_matches = len(block_comparison["exact_matches"])
    fuzzy_matches_md = len(block_comparison["fuzzy_matches"])

    weighted_score = block_comparison["match_rate"]

    result = {
        "not_in_use": not_in_use_path,
        "matched": matched_path,
        "similarity": similarity,
        "embedded_sections": exact_matches,
        "fuzzy_matches": fuzzy_matches_md,
        "partial_matches": 0,  # Not used in markdown mode
        "total_sections": total_blocks,
        "embedding_ratio": exact_matches / total_blocks if total_blocks > 0 else 0,
        "weighted_score": weighted_score,
        "recommendation": "SAFE TO DELETE" if weighted_score > 0.7 else "REVIEW NEEDED",
        "analysis_mode": "markdown-aware",
    }

    # Log markdown-aware results
    logger.info("📄 %s → %s [Markdown-aware]", not_in_use_path, matched_path)
    logger.info("   Similarity: %.2f", similarity)
    logger.info("   Blocks matched: %d/%d", exact_matches + fuzzy_matches_md, total_blocks)
    logger.info("   Match rate: %.1f%%", weighted_score * 100)
    logger.info("   💡 Recommendation: %s", result["recommendation"])

    return result


def _calculate_section_matches(
    sections: list[str], matched_content: str, matched_sections: list[str], min_length: int
) -> tuple[int, list[tuple[str, float]], list[tuple[str, float]]]:
    """Calculate exact, fuzzy, and partial matches for sections."""
    embedded_sections = 0
    fuzzy_matches: list[tuple[str, float]] = []
    partial_matches: list[tuple[str, float]] = []

    # Matching thresholds
    thresholds = {"exact": 95, "fuzzy": 80, "partial": 70}

    for section in sections:
        if len(section) >= min_length:
            if section in matched_content:
                embedded_sections += 1
            else:
                best_score = (
                    max(
                        max(fuzz.token_set_ratio(section, target), fuzz.token_sort_ratio(section, target))
                        for target in matched_sections
                    )
                    if matched_sections
                    else 0
                )

                if best_score >= thresholds["exact"]:
                    embedded_sections += 1
                elif best_score >= thresholds["fuzzy"]:
                    fuzzy_matches.append((section[:50] + "...", best_score))
                elif best_score >= thresholds["partial"]:
                    partial_matches.append((section[:50] + "...", best_score))

    return embedded_sections, fuzzy_matches, partial_matches


def _analyze_traditional_content(
    not_in_use_content: str,
    matched_content: str,
    *,
    not_in_use_path: str,
    matched_path: str,
    similarity: float,
    min_section_length: int,
) -> dict[str, Any]:
    """Analyze content using traditional section-based comparison."""
    # Split into sections
    not_in_use_sections = [s.strip() for s in re.split(r"\n\s*\n", not_in_use_content) if s.strip()]
    matched_sections = [
        s.strip() for s in re.split(r"\n\s*\n", matched_content) if s.strip() and len(s.strip()) >= min_section_length
    ]

    # Calculate matches using helper function
    embedded_sections, fuzzy_matches, partial_matches = _calculate_section_matches(
        not_in_use_sections, matched_content, matched_sections, min_section_length
    )

    total_sections = len([s for s in not_in_use_sections if len(s) >= min_section_length])

    # Calculate ratios
    embedding_ratio = embedded_sections / total_sections if total_sections > 0 else 0
    weighted_score = (
        (embedded_sections + len(fuzzy_matches) * 0.7 + len(partial_matches) * 0.3) / total_sections
        if total_sections > 0
        else 0
    )

    result = {
        "not_in_use": not_in_use_path,
        "matched": matched_path,
        "similarity": similarity,
        "embedded_sections": embedded_sections,
        "fuzzy_matches": len(fuzzy_matches),
        "partial_matches": len(partial_matches),
        "total_sections": total_sections,
        "embedding_ratio": embedding_ratio,
        "weighted_score": weighted_score,
        "recommendation": "SAFE TO DELETE" if weighted_score > 0.7 else "REVIEW NEEDED",
        "analysis_mode": "traditional",
    }

    # Log results
    logger.info("📄 %s → %s", not_in_use_path, matched_path)
    logger.info("   Similarity: %.2f", similarity)
    logger.info("   Exact/Near-exact: %d/%d sections (%.0f%%)", embedded_sections, total_sections, embedding_ratio * 100)
    logger.info("   Fuzzy matches: %d (80-95%% similar)", len(fuzzy_matches))
    logger.info("   Partial matches: %d (70-80%% similar)", len(partial_matches))
    logger.info("   Weighted score: %.2f", weighted_score)
    logger.info("   💡 Recommendation: %s", result["recommendation"])

    return result


def check_content_embedding(
    similarity_df: pd.DataFrame,
    root_dir: Path | None = None,
    similarity_threshold: float = 0.75,
    min_section_length: int = 20,
    use_markdown_aware: bool = True,
) -> pd.DataFrame:
    """Check if content from not_in_use documents is actually embedded in their similar candidates.

    This helps determine if the not_in_use file can be safely deleted.

    Args:
        similarity_df: DataFrame with similarity results
        root_dir: Root directory (defaults to current working directory)
        similarity_threshold: Minimum similarity to check embedding for
        min_section_length: Minimum section length to consider (default: 20 chars)
        use_markdown_aware: Use markdown-aware block comparison if available (default: True)

    Returns:
        DataFrame with embedding analysis results
    """
    if root_dir is None:
        root_dir = Path.cwd()

    logger.info("=== CONTENT EMBEDDING ANALYSIS ===")
    logger.info("Checking if not_in_use content exists in matched files...")
    logger.info("Minimum section length: %d characters", min_section_length)

    # Filter by similarity threshold
    filtered_df = similarity_df[similarity_df["similarity"] >= similarity_threshold].copy()

    results = []
    for _, row in filtered_df.iterrows():
        not_in_use_path = row["not_in_use"]
        matched_path = row["matched_file"]
        similarity = row["similarity"]

        # Read both files
        not_in_use_full_path = root_dir / not_in_use_path
        matched_full_path = root_dir / matched_path

        if not not_in_use_full_path.exists() or not matched_full_path.exists():
            logger.warning("⚠️  File not found: %s or %s", not_in_use_path, matched_path)
            continue

        not_in_use_content = not_in_use_full_path.read_text(encoding="utf-8", errors="ignore")
        matched_content = matched_full_path.read_text(encoding="utf-8", errors="ignore")

        # Try markdown-aware analysis first if available
        if use_markdown_aware and not_in_use_path.endswith(".md") and matched_path.endswith(".md"):
            try:
                result = _analyze_markdown_content(
                    not_in_use_content,
                    matched_content,
                    not_in_use_path=not_in_use_path,
                    matched_path=matched_path,
                    similarity=similarity,
                )
                results.append(result)
                continue  # Skip traditional analysis
            except Exception as e:
                # Fall back to traditional analysis
                logger.warning("⚠️  Markdown analysis failed, using traditional method: %s", e)

        # Traditional section-based analysis
        result = _analyze_traditional_content(
            not_in_use_content,
            matched_content,
            not_in_use_path=not_in_use_path,
            matched_path=matched_path,
            similarity=similarity,
            min_section_length=min_section_length,
        )
        results.append(result)

    # Create DataFrame from results
    result_df = pd.DataFrame(results)

    if len(result_df) > 0:
        # Save detailed report with all columns
        result_df.to_csv("content_embedding_report.tsv", sep="\t", index=False)
        logger.info("✅ Detailed report saved to: content_embedding_report.tsv")

        # Summary
        safe_to_delete = (result_df["recommendation"] == "SAFE TO DELETE").sum()
        logger.info("📊 Summary:")
        logger.info("   - Safe to delete: %d", safe_to_delete)
        logger.info("   - Need review: %d", len(result_df) - safe_to_delete)

        # Show fuzzy matching effectiveness
        total_fuzzy = result_df["fuzzy_matches"].sum()
        total_partial = result_df["partial_matches"].sum()
        if total_fuzzy > 0 or total_partial > 0:
            logger.info("🔍 Fuzzy Matching Results:")
            logger.info("   - Fuzzy matches found: %d sections", total_fuzzy)
            logger.info("   - Partial matches found: %d sections", total_partial)
            logger.info("   INFO: These would have been missed with exact string matching!")

    return result_df


def generate_comprehensive_similarity_report(
    active_docs: list[Path],
    not_in_use_docs: list[Path],
    root_dir: Path,
    threshold: float = 0.75,
    model: Optional["SentenceTransformer"] = None,
) -> dict[str, pd.DataFrame]:
    """Generate a comprehensive similarity report covering all document relationships.

    Args:
        active_docs: List of active document paths
        not_in_use_docs: List of not_in_use document paths
        root_dir: Root directory for relative path calculation
        threshold: Minimum similarity score to consider
        model: Pre-loaded SentenceTransformer model (optional)

    Returns:
        Dictionary containing different types of similarity analyses
    """
    logger.info("📋 GENERATING COMPREHENSIVE SIMILARITY REPORT")
    logger.info("=" * 60)

    # Import here to avoid circular imports
    from sentence_transformers import SentenceTransformer

    # Create model once if not provided
    if model is None:
        logger.info("🤖 Loading SentenceTransformer model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

    report = {}

    # 1. Active-to-Active similarities (find duplicates in good docs)
    logger.info("1️⃣ Analyzing active document similarities...")
    active_similarities = analyze_active_document_similarities(active_docs, root_dir, threshold, model=model)
    report["active_to_active"] = active_similarities

    if not active_similarities.empty:
        logger.info("   Found %d potential overlaps", len(active_similarities))
        # Show most concerning cases
        high_concern = active_similarities[active_similarities["relationship_type"].isin(["NEAR_DUPLICATE", "HIGH_OVERLAP"])]
        if not high_concern.empty:
            logger.warning("   🚨 High concern cases: %d", len(high_concern))
            for _, row in high_concern.head(3).iterrows():
                logger.warning("      %s ↔ %s (%.3f)", row["doc1"], row["doc2"], row["similarity"])
    else:
        logger.info("   ✅ No significant overlaps found among active documents")

    # 2. Not-in-use to Active similarities (original analysis)
    if not_in_use_docs:
        logger.info("2️⃣ Analyzing not_in_use to active similarities...")
        not_in_use_similarities = analyze_semantic_similarity(not_in_use_docs, active_docs, root_dir, threshold, model=model)
        report["not_in_use_to_active"] = not_in_use_similarities

        if not not_in_use_similarities.empty:
            logger.info("   Found %d not_in_use documents with active matches", len(not_in_use_similarities))
        else:
            logger.info("   ✅ No not_in_use documents match active documents")

    # 3. Save comprehensive report
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    for report_type, df in report.items():
        if not df.empty:
            filename = f"similarity_report_{report_type}_{timestamp}.tsv"
            df.to_csv(filename, sep="\t", index=False)
            logger.info("   💾 Saved %s report: %s", report_type, filename)

    return report


def export_similarity_report(
    similarity_df: pd.DataFrame,
    output_path: Path,
    format_type: str = "tsv",
    include_summary: bool = True,
) -> None:
    """Export similarity report in various formats.

    Args:
        similarity_df: DataFrame with similarity results
        output_path: Output file path
        format_type: Export format ('tsv', 'csv', 'excel', 'json')
        include_summary: Whether to include summary statistics
    """
    logger.info("📄 Exporting similarity report to %s", output_path)

    if similarity_df.empty:
        logger.warning("⚠️  No data to export")
        return

    try:
        if format_type.lower() == "tsv":
            similarity_df.to_csv(output_path, sep="\t", index=False)
        elif format_type.lower() == "csv":
            similarity_df.to_csv(output_path, index=False)
        elif format_type.lower() == "excel":
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                similarity_df.to_excel(writer, sheet_name="Similarities", index=False)

                if include_summary:
                    # Create summary sheet
                    summary_data = _create_summary_stats(similarity_df)
                    summary_df = pd.DataFrame(list(summary_data.items()), columns=["Metric", "Value"])
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)

        elif format_type.lower() == "json":
            similarity_df.to_json(output_path, orient="records", indent=2)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        logger.info("✅ Report exported successfully")

    except Exception as e:
        logger.error("❌ Failed to export report: %s", e)
        raise


def _create_summary_stats(similarity_df: pd.DataFrame) -> dict[str, Any]:
    """Create summary statistics for similarity analysis."""
    stats = {
        "Total Comparisons": len(similarity_df),
        "Average Similarity": similarity_df["similarity"].mean(),
        "Max Similarity": similarity_df["similarity"].max(),
        "Min Similarity": similarity_df["similarity"].min(),
    }

    # Add relationship type counts if available
    if "relationship_type" in similarity_df.columns:
        type_counts = similarity_df["relationship_type"].value_counts()
        for rel_type, count in type_counts.items():
            stats[f"{rel_type} Count"] = count

    # Add recommendation counts if available
    if "recommendation" in similarity_df.columns:
        rec_counts = similarity_df["recommendation"].value_counts()
        for rec, count in rec_counts.items():
            stats[f"{rec} Count"] = count

    return stats


def create_overlap_heatmap(
    similarity_matrix: pd.DataFrame,
    output_path: Path | None = None,
    threshold: float = 0.75,
) -> Path | None:
    """Create a heatmap visualization of document similarities.

    Args:
        similarity_matrix: Square similarity matrix DataFrame
        output_path: Output path for heatmap image (optional)
        threshold: Minimum similarity to highlight

    Returns:
        Path to saved heatmap image if successful
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Create heatmap
        plt.figure(figsize=(12, 10))

        # Mask values below threshold
        mask = similarity_matrix < threshold

        sns.heatmap(
            similarity_matrix,
            mask=mask,
            annot=True,
            fmt=".2f",
            cmap="Reds",
            cbar_kws={"label": "Similarity Score"},
            square=True,
        )

        plt.title(f"Document Similarity Heatmap (threshold: {threshold})")
        plt.xlabel("Documents")
        plt.ylabel("Documents")
        plt.xticks(rotation=45, ha="right")
        plt.yticks(rotation=0)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info("📊 Heatmap saved to %s", output_path)
            return output_path

        plt.show()
        return None

    except ImportError:
        logger.warning("⚠️  matplotlib/seaborn not available, skipping heatmap")
        return None
    except Exception as e:
        logger.error("❌ Failed to create heatmap: %s", e)
        return None