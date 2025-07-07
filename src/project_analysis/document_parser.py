"""Document parsing functionality for instruction path tracer."""

import logging
import re
from pathlib import Path

from .instruction_node import InstructionNode
from .patterns import FILE_GENERATION_PATTERNS, INSTRUCTION_PATTERNS

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parses documents to extract instructions and references."""

    def extract_document_info(self, doc_path: Path) -> InstructionNode | None:
        """Extract instructions and references from a document.
        
        Args:
            doc_path: Path to the document to parse
            
        Returns:
            InstructionNode with extracted information or None if file doesn't exist
        """
        if not doc_path.exists():
            return None

        content = doc_path.read_text()
        
        # Extract title
        title = self._extract_title(doc_path, content)
        
        node = InstructionNode(path=doc_path, title=title, depth=0)
        
        # Extract various elements
        node.references = self._extract_references(content)
        node.instructions = self._extract_instructions(content)
        node.generates = self._extract_file_generations(content)
        
        return node

    def _extract_title(self, doc_path: Path, content: str) -> str:
        """Extract title from document content.
        
        Args:
            doc_path: Path to document (used as fallback)
            content: Document content
            
        Returns:
            Document title
        """
        lines = content.split("\n")
        
        # Check first 10 lines for markdown title
        for line in lines[:10]:
            if line.startswith("# "):
                return line[2:].strip()
                
        # Fallback to filename
        return doc_path.name

    def _extract_references(self, content: str) -> list[str]:
        """Extract markdown link references from content.
        
        Args:
            content: Document content
            
        Returns:
            List of referenced .md files
        """
        references = []
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        
        for match in re.finditer(link_pattern, content):
            link_path = match.group(2)
            if link_path.endswith(".md"):
                references.append(link_path)
                
        return references

    def _extract_instructions(self, content: str) -> list[str]:
        """Extract instruction patterns from content.
        
        Args:
            content: Document content
            
        Returns:
            List of found instructions
        """
        instructions = []
        
        for pattern in INSTRUCTION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                instruction = match.group(0)
                instructions.append(instruction)
                
        return instructions

    def _extract_file_generations(self, content: str) -> list[str]:
        """Extract file generation mentions from content.
        
        Args:
            content: Document content
            
        Returns:
            List of files mentioned for generation
        """
        generates = []
        
        for pattern in FILE_GENERATION_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                file_mention = match.group(1)
                if file_mention and not file_mention.startswith("$"):
                    generates.append(file_mention)
                    
        return generates