"""Document merging and deduplication utilities."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from document_analyzer.core import get_best_match_seq, is_similar, split_sections

logger = logging.getLogger(__name__)


def merge_documents(
    source_text: str,
    target_text: str,
    *,
    section_min_len: int = 20,
    similarity_threshold: int = 85,
    annotate: bool = True,
    source_label: str = "Merged from source",
) -> str:
    """Merge source into target by appending non-duplicate sections.

    Args:
        source_text: Content to merge from
        target_text: Content to merge into
        section_min_len: Minimum section length to consider
        similarity_threshold: Fuzzy matching threshold (0-100)
        annotate: Whether to add merge annotations
        source_label: Label for merge annotations

    Returns:
        Merged document content
    """
    source_sections = split_sections(source_text, section_min_len)
    target_sections = split_sections(target_text, section_min_len)

    merged_text = target_text.strip()
    merged_text += "\n\n---\n\n"

    added_count = 0

    for section in source_sections:
        if not any(is_similar(section, tgt, similarity_threshold) for tgt in target_sections):
            # Debug: Check fallback matching for curiosity
            _, ratio = get_best_match_seq(section, target_sections)
            if ratio > 0.6:
                logger.debug("🧐 Closest fallback match: %.2f", ratio)

            if annotate:
                merged_text += f"\n<!-- {source_label} -->\n"
            merged_text += section + "\n\n"
            added_count += 1

    logger.info("✅ Merged %d unique sections from source into target", added_count)
    return merged_text.strip()


def merge_similar_documents(
    similarity_df: pd.DataFrame,
    root_dir: Path,
    merge_threshold: float = 0.9,
    dry_run: bool = True,
    backup: bool = True,
) -> dict[str, Any]:
    """Merge documents that are highly similar to reduce duplication.

    Args:
        similarity_df: DataFrame with similarity analysis results
        root_dir: Root directory containing documents
        merge_threshold: Minimum similarity to consider for merging (0.9 = 90%)
        dry_run: If True, only show what would be merged without doing it
        backup: Whether to create backups before merging

    Returns:
        Dictionary with merge results and statistics
    """
    logger.info("🔗 DOCUMENT MERGING ANALYSIS")
    logger.info("Merge threshold: %.1f%%", merge_threshold * 100)

    # Filter high-similarity pairs
    merge_candidates = similarity_df[similarity_df["similarity"] >= merge_threshold].copy()

    if merge_candidates.empty:
        logger.info("No documents meet the merge threshold of %.1f%%", merge_threshold * 100)
        return {"merged": [], "skipped": [], "errors": []}

    logger.info("Found %d document pairs for potential merging", len(merge_candidates))

    merge_results: dict[str, list[dict[str, Any]]] = {"merged": [], "skipped": [], "errors": []}

    for _, row in merge_candidates.iterrows():
        doc1_path = root_dir / row["doc1"]
        doc2_path = root_dir / row["doc2"]
        similarity = row["similarity"]

        # Determine merge direction (merge smaller into larger)
        try:
            doc1_size = doc1_path.stat().st_size
            doc2_size = doc2_path.stat().st_size

            if doc1_size > doc2_size:
                target_path, source_path = doc1_path, doc2_path
                target_name, source_name = row["doc1"], row["doc2"]
            else:
                target_path, source_path = doc2_path, doc1_path
                target_name, source_name = row["doc2"], row["doc1"]

            logger.info("📋 Merge candidate: %s → %s (%.1f%% similar)", source_name, target_name, similarity * 100)

            if dry_run:
                logger.info("   [DRY RUN] Would merge %s into %s", source_name, target_name)
                merge_results["skipped"].append(
                    {"source": source_name, "target": target_name, "similarity": similarity, "reason": "dry_run"}
                )
                continue

            # Read documents
            source_text = source_path.read_text(encoding="utf-8", errors="ignore")
            target_text = target_path.read_text(encoding="utf-8", errors="ignore")

            # Create backup if requested
            if backup:
                backup_path = target_path.with_suffix(f".backup{target_path.suffix}")
                backup_path.write_text(target_text, encoding="utf-8")
                logger.info("   💾 Created backup: %s", backup_path.name)

            # Perform merge
            merged_content = merge_documents(
                source_text, target_text, source_label=f"Merged from {source_name} (similarity: {similarity:.1%})"
            )

            # Write merged result
            target_path.write_text(merged_content, encoding="utf-8")
            logger.info("   ✅ Merged %s into %s", source_name, target_name)

            # Remove source file
            source_path.unlink()
            logger.info("   🗑️  Removed source file: %s", source_name)

            merge_results["merged"].append(
                {"source": source_name, "target": target_name, "similarity": similarity, "backup_created": backup}
            )

        except Exception as e:
            logger.error("   ❌ Failed to merge %s and %s: %s", row["doc1"], row["doc2"], e)
            merge_results["errors"].append({"doc1": row["doc1"], "doc2": row["doc2"], "error": str(e)})

    # Summary
    logger.info("🔗 MERGE SUMMARY:")
    logger.info("   Merged: %d pairs", len(merge_results["merged"]))
    logger.info("   Skipped: %d pairs", len(merge_results["skipped"]))
    logger.info("   Errors: %d pairs", len(merge_results["errors"]))

    return merge_results


def create_merge_backup(documents: list[Path], backup_name: str | None = None) -> Path:
    """Create a backup directory with copies of documents before merging.

    Args:
        documents: List of document paths to backup
        backup_name: Custom backup directory name (optional)

    Returns:
        Path to created backup directory
    """
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"merge_backup_{timestamp}"

    # Find common root directory
    if documents:
        common_root = documents[0].parent
        for doc in documents[1:]:
            # Find common ancestor
            try:
                common_root = Path(
                    *Path.resolve(common_root).parts[
                        : len([p for p in Path.resolve(common_root).parts if p in Path.resolve(doc.parent).parts])
                    ]
                )
            except (ValueError, IndexError):
                common_root = Path.cwd()
    else:
        common_root = Path.cwd()

    backup_dir = common_root / backup_name
    backup_dir.mkdir(exist_ok=True)

    logger.info("📦 Creating backup in %s", backup_dir)

    backed_up = 0
    for doc_path in documents:
        if doc_path.exists():
            try:
                # Preserve relative structure
                rel_path = doc_path.relative_to(common_root)
                backup_path = backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                backup_path.write_text(doc_path.read_text(encoding="utf-8"), encoding="utf-8")
                backed_up += 1
                logger.debug("   📋 Backed up: %s", rel_path)

            except Exception as e:
                logger.warning("   ⚠️  Failed to backup %s: %s", doc_path, e)

    logger.info("✅ Backed up %d/%d documents to %s", backed_up, len(documents), backup_dir)
    return backup_dir


def merge_document_list(
    document_paths: list[Path],
    output_path: Path,
    section_min_len: int = 20,
    similarity_threshold: int = 85,
    create_backup: bool = True,
) -> dict[str, Any]:
    """Merge multiple documents into a single output document.

    Args:
        document_paths: List of documents to merge
        output_path: Path for merged output document
        section_min_len: Minimum section length to consider
        similarity_threshold: Fuzzy matching threshold (0-100)
        create_backup: Whether to create backup before merging

    Returns:
        Dictionary with merge statistics
    """
    if not document_paths:
        return {"error": "No documents provided"}

    if len(document_paths) < 2:
        return {"error": "Need at least 2 documents to merge"}

    logger.info("🔗 Merging %d documents → %s", len(document_paths), output_path)

    # Create backup if requested
    if create_backup:
        backup_dir = create_merge_backup(document_paths)

    try:
        # Start with first document as base
        base_doc = document_paths[0]
        merged_content = base_doc.read_text(encoding="utf-8", errors="ignore")

        total_sections_added = 0

        # Merge each subsequent document
        for i, doc_path in enumerate(document_paths[1:], 1):
            if not doc_path.exists():
                logger.warning("⚠️  Document not found: %s", doc_path)
                continue

            logger.info("   📋 Merging document %d/%d: %s", i + 1, len(document_paths), doc_path.name)

            source_content = doc_path.read_text(encoding="utf-8", errors="ignore")

            # Count sections before merge
            before_sections = len(split_sections(merged_content, section_min_len))

            merged_content = merge_documents(
                source_content,
                merged_content,
                section_min_len=section_min_len,
                similarity_threshold=similarity_threshold,
                source_label=f"Merged from {doc_path.name}",
            )

            # Count sections after merge
            after_sections = len(split_sections(merged_content, section_min_len))
            sections_added = after_sections - before_sections
            total_sections_added += sections_added

            logger.info("   + Added %d unique sections", sections_added)

        # Write merged output
        output_path.write_text(merged_content, encoding="utf-8")

        result = {
            "success": True,
            "input_documents": len(document_paths),
            "output_path": str(output_path),
            "total_sections_added": total_sections_added,
        }

        if create_backup:
            result["backup_dir"] = str(backup_dir)

        logger.info(
            "✅ Successfully merged %d documents with %d unique sections added", len(document_paths), total_sections_added
        )

        return result

    except Exception as e:
        logger.error("❌ Failed to merge documents: %s", e)
        return {"error": str(e)}
