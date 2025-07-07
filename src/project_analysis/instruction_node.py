"""Data model for instruction path nodes."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class InstructionNode:
    """Represents a node in the instruction path tree.
    
    Attributes:
        path: Path to the document
        title: Document title
        depth: Depth in the instruction tree
        parent: Parent node in the tree
        children: Child nodes
        references: List of document references
        instructions: List of extracted instructions
        generates: List of files this document generates
    """

    path: Path
    title: str
    depth: int
    parent: Optional["InstructionNode"] = None
    children: list["InstructionNode"] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    generates: list[str] = field(default_factory=list)