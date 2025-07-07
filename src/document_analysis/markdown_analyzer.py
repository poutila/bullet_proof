"""Markdown-aware content analysis utilities."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import mistune


class BlockType(Enum):
    """Types of markdown blocks for semantic comparison."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST_ITEM = "list_item"
    BLOCKQUOTE = "blockquote"
    TABLE = "table"
    LINK = "link"
    IMAGE = "image"


@dataclass
class MarkdownBlock:
    """Represents a semantic block in markdown."""

    type: BlockType
    content: str
    level: int | None = None  # For headings
    language: str | None = None  # For code blocks
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}


class MarkdownAnalyzer:
    """Analyzes markdown content by semantic blocks using mistune v3."""

    def __init__(self) -> None:
        """Initialize the markdown analyzer with mistune parser."""
        # Create a markdown parser
        self.markdown = mistune.create_markdown(renderer=None)

    def extract_blocks(self, content: str) -> list[MarkdownBlock]:
        """Extract semantic blocks from markdown content."""
        blocks = []

        # Parse markdown to AST
        tokens = self.markdown.parse(content)

        for token in tokens:
            if isinstance(token, dict):
                element_type = token.get("type", "")
            else:
                continue  # Skip non-dict tokens

            if element_type == "heading" and isinstance(token, dict):
                children = token.get("children", [])
                attrs = token.get("attrs", {})
                level = attrs.get("level", 1) if isinstance(attrs, dict) else 1
                blocks.append(MarkdownBlock(type=BlockType.HEADING, content=self._extract_text(children), level=level))

            elif element_type == "paragraph" and isinstance(token, dict):
                children = token.get("children", [])
                text = self._extract_text(children)
                if text.strip():
                    blocks.append(MarkdownBlock(type=BlockType.PARAGRAPH, content=text.strip()))

            elif element_type == "block_code" and isinstance(token, dict):
                raw_content = token.get("raw", "")
                attrs = token.get("attrs", {})
                language = attrs.get("info") if isinstance(attrs, dict) else None
                blocks.append(
                    MarkdownBlock(
                        type=BlockType.CODE_BLOCK,
                        content=raw_content.strip() if isinstance(raw_content, str) else "",
                        language=language,
                    )
                )

            elif element_type == "list" and isinstance(token, dict):
                # Extract list items
                self._extract_list_items(token, blocks)

            elif element_type == "block_quote" and isinstance(token, dict):
                children = token.get("children", [])
                quote_content = self._extract_from_children(children)
                if quote_content:
                    blocks.append(MarkdownBlock(type=BlockType.BLOCKQUOTE, content=quote_content))

            elif element_type == "table" and isinstance(token, dict):
                # Simplified table extraction
                table_text = self._extract_table_text(token)
                if table_text:
                    blocks.append(MarkdownBlock(type=BlockType.TABLE, content=table_text))

        return blocks

    def _extract_text(self, children: list[dict[str, Any]]) -> str:
        """Extract text from token children."""
        text_parts = []

        for child in children:
            if isinstance(child, dict):
                child_type = child.get("type", "")

                if child_type in ("text", "code_span"):
                    text_parts.append(child.get("raw", ""))
                elif child_type == "link":
                    # Get link text
                    link_text = self._extract_text(child.get("children", []))
                    text_parts.append(link_text)
                elif child_type in ["strong", "emphasis"]:
                    text_parts.append(self._extract_text(child.get("children", [])))
                else:
                    # Recursively extract from other types
                    text_parts.append(self._extract_text(child.get("children", [])))

        return " ".join(text_parts).strip()

    def _extract_list_items(self, list_token: dict[str, Any], blocks: list[MarkdownBlock]) -> None:
        """Extract individual list items."""
        for item in list_token.get("children", []):
            if item.get("type") == "list_item":
                item_text = self._extract_from_children(item.get("children", []))
                if item_text:
                    blocks.append(
                        MarkdownBlock(
                            type=BlockType.LIST_ITEM, content=item_text, level=list_token.get("attrs", {}).get("depth", 0)
                        )
                    )

    def _extract_from_children(self, children: list[dict[str, Any]]) -> str:
        """Extract text from nested children."""
        text_parts = []

        for child in children:
            if isinstance(child, dict):
                if child.get("type") == "paragraph":
                    text_parts.append(self._extract_text(child.get("children", [])))
                else:
                    # Handle other block types
                    text_parts.append(self._extract_text([child]))

        return " ".join(text_parts).strip()

    def _extract_table_text(self, table_token: dict[str, Any]) -> str:
        """Extract table content as text."""
        rows = []

        # Extract header
        thead = table_token.get("children", [{}])[0]
        if thead.get("type") == "table_head":
            for row in thead.get("children", []):
                if row.get("type") == "table_row":
                    cells = [self._extract_text(cell.get("children", [])) for cell in row.get("children", [])]
                    rows.append(" | ".join(cells))

        # Extract body
        tbody = table_token.get("children", [{}])[1] if len(table_token.get("children", [])) > 1 else None
        if tbody and tbody.get("type") == "table_body":
            for row in tbody.get("children", []):
                if row.get("type") == "table_row":
                    cells = [self._extract_text(cell.get("children", [])) for cell in row.get("children", [])]
                    rows.append(" | ".join(cells))

        return "\n".join(rows)

    def normalize_block(self, block: MarkdownBlock) -> str:
        """Normalize block content for comparison."""
        text = block.content

        # Normalize whitespace
        text = " ".join(text.split())

        # Normalize based on block type
        if block.type == BlockType.CODE_BLOCK:
            # Don't normalize code blocks too much
            return text
        if block.type == BlockType.LIST_ITEM:
            # Remove common list prefixes
            text = re.sub(r"^[-*+•]\s*", "", text)
            text = re.sub(r"^\d+\.\s*", "", text)

        return text.lower().strip()

    def get_block_signature(self, block: MarkdownBlock) -> str:
        """Get a signature for the block that captures its semantic meaning."""
        sig_parts = [block.type.value]

        if block.level is not None:
            sig_parts.append(f"L{block.level}")

        if block.language:
            sig_parts.append(block.language)

        # Add normalized content preview
        normalized = self.normalize_block(block)
        if len(normalized) > 50:
            sig_parts.append(normalized[:50] + "...")
        else:
            sig_parts.append(normalized)

        return "|".join(sig_parts)

    def group_blocks_by_section(self, blocks: list[MarkdownBlock]) -> list[list[MarkdownBlock]]:
        """Group blocks by their parent heading."""
        sections = []
        current_section: list[MarkdownBlock] = []

        for block in blocks:
            if block.type == BlockType.HEADING:
                if current_section:
                    sections.append(current_section)
                current_section = [block]
            else:
                current_section.append(block)

        if current_section:
            sections.append(current_section)

        return sections


def compare_markdown_blocks(
    source_blocks: list[MarkdownBlock], target_blocks: list[MarkdownBlock], fuzzy_threshold: float = 0.8
) -> dict[str, Any]:
    """Compare two sets of markdown blocks semantically."""
    from rapidfuzz import fuzz

    # results = {"exact_matches": [], "fuzzy_matches": [], "missing_blocks": [], "match_rate": 0.0}
    results: dict[str, Any] = {"exact_matches": [], "fuzzy_matches": [], "missing_blocks": []}
    analyzer = MarkdownAnalyzer()
    matched_count = 0

    for source_block in source_blocks:
        source_norm = analyzer.normalize_block(source_block)

        best_score: float = 0.0
        best_match = None

        for target_block in target_blocks:
            # Skip different block types
            if source_block.type != target_block.type:
                continue

            target_norm = analyzer.normalize_block(target_block)

            # Check exact match first
            if source_norm == target_norm:
                results["exact_matches"].append({"source": source_block, "target": target_block, "score": 1.0})
                matched_count += 1
                break

            # Fuzzy match
            score = fuzz.token_set_ratio(source_norm, target_norm) / 100.0
            if score > best_score:
                best_score = score
                best_match = target_block

        else:  # No exact match found
            if best_score >= fuzzy_threshold:
                results["fuzzy_matches"].append({"source": source_block, "target": best_match, "score": best_score})
                matched_count += 1
            else:
                results["missing_blocks"].append({"block": source_block, "best_score": best_score})

    total_blocks = len(source_blocks)
    results["match_rate"] = matched_count / total_blocks if total_blocks > 0 else 0.0

    return results
