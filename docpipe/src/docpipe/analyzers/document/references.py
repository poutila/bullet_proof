"""Reference validation analyzer for checking document links and references."""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urlparse
import logging

from ...models import (
    ReferenceResults,
    ReferenceInfo,
    Issue,
    Severity,
    IssueCategory,
)
from ..base import FileAnalyzer

logger = logging.getLogger(__name__)


class ReferenceValidator(FileAnalyzer):
    """Analyzer for validating references and links in markdown documents."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize validator."""
        super().__init__(config)
        
        # Configuration
        self.check_external_links = config.get("check_external_links", False) if config else False
        self.check_images = config.get("check_images", True) if config else True
        self.check_anchors = config.get("check_anchors", True) if config else True
        
        # Track all documents for orphan detection
        self.all_documents: Set[Path] = set()
        self.referenced_documents: Set[Path] = set()
    
    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "ReferenceValidator"
    
    @property
    def description(self) -> str:
        """Get analyzer description."""
        return "Validates references and links in markdown documents"
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Only process markdown files."""
        return file_path.suffix.lower() in ['.md', '.markdown']
    
    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single markdown file for references."""
        self.all_documents.add(file_path)
        
        references = []
        issues = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract all references
            markdown_refs = self._extract_markdown_references(content)
            image_refs = self._extract_image_references(content) if self.check_images else []
            
            # Validate each reference
            for ref_text, target, line_num in markdown_refs + image_refs:
                ref_info = self._validate_reference(
                    file_path, target, line_num, ref_text
                )
                references.append(ref_info)
                
                if not ref_info.is_valid:
                    issues.append(Issue(
                        severity=Severity.ERROR,
                        category=IssueCategory.BROKEN_REFERENCE,
                        message=f"Broken reference: {ref_text}",
                        file_path=file_path,
                        line_number=line_num,
                        suggestion=ref_info.error_message,
                        code_snippet=ref_text
                    ))
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            issues.append(Issue(
                severity=Severity.ERROR,
                category=IssueCategory.PARSE_ERROR,
                message=f"Failed to analyze file: {e}",
                file_path=file_path
            ))
        
        return {
            "references": references,
            "issues": issues
        }
    
    def _extract_markdown_references(self, content: str) -> List[Tuple[str, str, int]]:
        """Extract markdown link references from content."""
        references = []
        lines = content.split('\n')
        
        # Pattern for markdown links: [text](url)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        for i, line in enumerate(lines, 1):
            for match in link_pattern.finditer(line):
                text, url = match.groups()
                references.append((match.group(0), url, i))
        
        return references
    
    def _extract_image_references(self, content: str) -> List[Tuple[str, str, int]]:
        """Extract image references from content."""
        references = []
        lines = content.split('\n')
        
        # Pattern for markdown images: ![alt](url)
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        
        for i, line in enumerate(lines, 1):
            for match in img_pattern.finditer(line):
                alt_text, url = match.groups()
                references.append((match.group(0), url, i))
        
        return references
    
    def _validate_reference(
        self,
        source_file: Path,
        target: str,
        line_number: int,
        reference_text: str
    ) -> ReferenceInfo:
        """Validate a single reference."""
        # Parse the target
        parsed = urlparse(target)
        
        # External link
        if parsed.scheme in ['http', 'https']:
            if self.check_external_links:
                # Would need to implement HTTP checking here
                # For now, assume external links are valid
                return ReferenceInfo(
                    source_file=source_file,
                    target_file=Path(target),
                    line_number=line_number,
                    reference_text=reference_text,
                    is_valid=True
                )
            else:
                # Skip external link validation
                return ReferenceInfo(
                    source_file=source_file,
                    target_file=Path(target),
                    line_number=line_number,
                    reference_text=reference_text,
                    is_valid=True
                )
        
        # Anchor link
        if target.startswith('#'):
            # TODO: Implement anchor validation
            return ReferenceInfo(
                source_file=source_file,
                target_file=source_file,  # Same file
                line_number=line_number,
                reference_text=reference_text,
                is_valid=True
            )
        
        # Local file reference
        # Remove any anchor from the path
        local_path = target.split('#')[0] if '#' in target else target
        
        # Resolve relative path
        if local_path:
            target_path = (source_file.parent / local_path).resolve()
            
            # Track referenced document
            if target_path.suffix.lower() in ['.md', '.markdown']:
                self.referenced_documents.add(target_path)
            
            # Check if file exists
            if target_path.exists():
                return ReferenceInfo(
                    source_file=source_file,
                    target_file=target_path,
                    line_number=line_number,
                    reference_text=reference_text,
                    is_valid=True
                )
            else:
                return ReferenceInfo(
                    source_file=source_file,
                    target_file=target_path,
                    line_number=line_number,
                    reference_text=reference_text,
                    is_valid=False,
                    error_message=f"File not found: {target_path}"
                )
        
        # Empty reference
        return ReferenceInfo(
            source_file=source_file,
            target_file=Path(target),
            line_number=line_number,
            reference_text=reference_text,
            is_valid=False,
            error_message="Empty reference"
        )
    
    def _analyze_impl(self, path: Path) -> ReferenceResults:
        """Aggregate results into ReferenceResults."""
        # Reset tracking sets
        self.all_documents.clear()
        self.referenced_documents.clear()
        
        results = ReferenceResults()
        
        if path.is_file():
            # Single file analysis
            file_result = self._analyze_file(path)
            
            for ref in file_result["references"]:
                results.references_found += 1
                if ref.is_valid:
                    results.valid_references += 1
                else:
                    results.broken_references.append(ref)
        
        else:
            # Directory analysis
            file_results = self._analyze_directory(path)
            
            for file_path, result in file_results.items():
                if isinstance(result, dict) and "references" in result:
                    for ref in result["references"]:
                        results.references_found += 1
                        if ref.is_valid:
                            results.valid_references += 1
                        else:
                            results.broken_references.append(ref)
            
            # Find orphaned documents
            results.orphaned_documents = list(
                self.all_documents - self.referenced_documents
            )
        
        return results