### Phase 6: Task Validation System (3-4 hours)
#### 6.1 Create Task Validator Workflow
**File**: `.github/workflows/task-validator.yml`
```yaml
name: Task Validation
on:
  pull_request:
    paths:
      - 'planning/TASK.md'
  push:
    paths:
      - 'planning/TASK.md'
  workflow_dispatch:

jobs:
  validate-tasks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install validation dependencies
        run: |
          # Use uv for faster local development, pip for CI consistency
          if command -v uv &> /dev/null; then
            uv pip install pydantic tabulate
          else
            pip install pydantic tabulate
          fi
          
      - name: Run task validation
        run: |
          python scripts/validate_tasks.py planning/TASK.md
```

#### 6.2 Create Task Validation Script
**File**: `scripts/validate_tasks.py`
```python
#!/usr/bin/env python3
"""
Task validation script for TASK.md files.

Validates task format, uniqueness, and consistency following CLAUDE.md standards.
Includes comprehensive error handling, type hints, and structured logging.
"""
import re
import sys
import logging
import json
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# Constants
TASK_ID_PATTERN = r'^T-\d+$'
PR_LINK_PATTERN = r'\[#(\d+)\]\(\.\.\/pull\/\1\)'
MAX_TASK_TITLE_LENGTH = 100
MAX_NOTES_LENGTH = 200


class Priority(str, Enum):
    """Valid task priorities."""
    CRITICAL = 'Critical'
    HIGH = 'High'
    MEDIUM = 'Medium'
    LOW = 'Low'


class Status(str, Enum):
    """Valid task statuses."""
    NOT_STARTED = 'Not Started'
    IN_PROGRESS = 'In Progress'
    BLOCKED = 'Blocked'
    REVIEW = 'Review'
    TESTING = 'Testing'
    DONE = 'Done'


class ReviewStatus(str, Enum):
    """Valid review statuses."""
    APPROVED = '✔️'
    NOT_REVIEWED = '✖️'
    IN_REVIEW = '🔍'
    CHANGES_REQUESTED = '⚠️'
    MERGED = '🚀'


@dataclass
class Task:
    """Task data model with validation.
    
    Attributes:
        id: Task identifier (T-XXX format)
        title: Task title/description
        priority: Task priority level
        points: Story points (Fibonacci sequence)
        status: Current task status
        reviewed: Code review status
        owner: Task assignee
        pr_link: Pull request link
        eta: Estimated completion date
        depends_on: Dependency task IDs
        sprint_id: Sprint identifier
        notes: Additional notes
    """
    id: str
    title: str
    priority: str
    points: int
    status: str
    reviewed: str
    owner: str
    pr_link: str
    eta: str
    depends_on: str
    sprint_id: str
    notes: str

    def __post_init__(self) -> None:
        """Validate task data after initialization.
        
        Raises:
            ValueError: If task data is invalid
        """
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.title:
            raise ValueError(f"Task {self.id} title cannot be empty")
        if len(self.title) > MAX_TASK_TITLE_LENGTH:
            raise ValueError(f"Task {self.id} title exceeds {MAX_TASK_TITLE_LENGTH} characters")
        if len(self.notes) > MAX_NOTES_LENGTH:
            raise ValueError(f"Task {self.id} notes exceed {MAX_NOTES_LENGTH} characters")


class TaskValidator:
    """Validates TASK.md file format and consistency.
    
    Performs comprehensive validation including:
    - Task ID format and uniqueness
    - Property value validation
    - Dependency checking
    - PR link format validation
    - Sprint consistency
    """
    
    # Valid story points following Fibonacci sequence
    VALID_POINTS: Set[int] = {1, 2, 3, 5, 8, 13, 21}
    
    def __init__(self, file_path: str) -> None:
        """Initialize task validator.
        
        Args:
            file_path: Path to TASK.md file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        self.file_path: Path = Path(file_path)
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            self.content: str = self.file_path.read_text(encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to read file: {e}")
            raise IOError(f"Cannot read file {file_path}: {e}") from e
            
        self.tasks: List[Task] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse_tasks(self) -> None:
        """Parse tasks from markdown table.
        
        Extracts task data from markdown table format and creates
        Task objects with validation.
        """
        # Regex pattern for task table rows (13 columns)
        task_pattern = (
            r'\|\s*(T-\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
            r'\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
            r'\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
            r'\s*([^|]+)\s*\|'
        )
        
        matches = re.findall(task_pattern, self.content)
        
        for match in matches:
            try:
                task = Task(
                    id=match[0].strip(),
                    title=match[1].strip(),
                    priority=match[3].strip(),
                    points=int(match[4].strip()) if match[4].strip().isdigit() else 0,
                    status=match[5].strip(),
                    reviewed=match[6].strip(),
                    owner=match[7].strip(),
                    pr_link=match[8].strip(),
                    eta=match[9].strip(),
                    depends_on=match[10].strip(),
                    sprint_id=match[11].strip(),
                    notes=match[12].strip()
                )
                self.tasks.append(task)
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse task row: {e}")
                self.warnings.append(f"Failed to parse task row: {str(e)}")
    
    def validate_task_ids(self) -> None:
        """Validate task ID format and uniqueness.
        
        Ensures all task IDs follow T-XXX format and are unique.
        """
        seen_ids: Set[str] = set()
        
        for task in self.tasks:
            # Check ID format
            if not re.match(TASK_ID_PATTERN, task.id):
                self.errors.append(f"Invalid task ID format: {task.id}")
            
            # Check uniqueness
            if task.id in seen_ids:
                self.errors.append(f"Duplicate task ID: {task.id}")
            seen_ids.add(task.id)
    
    def validate_task_properties(self) -> None:
        """Validate task property values.
        
        Checks that all task properties have valid values according
        to defined enums and constraints.
        """
        valid_priorities = {p.value for p in Priority}
        valid_statuses = {s.value for s in Status}
        valid_review_statuses = {r.value for r in ReviewStatus}
        
        for task in self.tasks:
            # Priority validation
            if task.priority not in valid_priorities:
                self.errors.append(
                    f"Invalid priority '{task.priority}' for task {task.id}. "
                    f"Valid options: {', '.join(valid_priorities)}"
                )
            
            # Status validation
            if task.status not in valid_statuses:
                self.errors.append(
                    f"Invalid status '{task.status}' for task {task.id}. "
                    f"Valid options: {', '.join(valid_statuses)}"
                )
            
            # Review status validation
            if task.reviewed not in valid_review_statuses:
                self.errors.append(
                    f"Invalid review status '{task.reviewed}' for task {task.id}. "
                    f"Valid options: {', '.join(valid_review_statuses)}"
                )
            
            # Points validation
            if task.points not in self.VALID_POINTS and task.points != 0:
                self.warnings.append(
                    f"Unusual story points {task.points} for task {task.id}. "
                    f"Consider using Fibonacci sequence: {sorted(self.VALID_POINTS)}"
                )
            
            # Owner validation
            if not task.owner or task.owner == '-':
                self.warnings.append(f"No owner assigned to task {task.id}")
    
    def validate_dependencies(self) -> None:
        """Validate task dependencies exist.
        
        Ensures all task dependencies reference existing tasks.
        """
        task_ids: Set[str] = {task.id for task in self.tasks}
        
        for task in self.tasks:
            if task.depends_on and task.depends_on != '-':
                deps = [dep.strip() for dep in task.depends_on.split(',')]
                for dep in deps:
                    if dep and dep not in task_ids:
                        self.errors.append(
                            f"Task {task.id} depends on non-existent task {dep}"
                        )
    
    def validate_pr_links(self) -> None:
        """Validate PR link format.
        
        Ensures pull request links follow the expected format.
        """
        for task in self.tasks:
            if task.pr_link and task.pr_link != '-':
                if not re.match(PR_LINK_PATTERN, task.pr_link):
                    self.warnings.append(
                        f"Invalid PR link format for task {task.id}: {task.pr_link}. "
                        f"Expected format: [#123](../pull/123)"
                    )
    
    def validate_sprint_consistency(self) -> None:
        """Validate sprint ID consistency.
        
        Warns if tasks reference multiple sprint IDs.
        """
        sprint_ids: Set[str] = {
            task.sprint_id for task in self.tasks 
            if task.sprint_id and task.sprint_id != '-'
        }
        
        if len(sprint_ids) > 1:
            self.warnings.append(
                f"Multiple sprint IDs found: {', '.join(sorted(sprint_ids))}. "
                "Consider consolidating to a single sprint."
            )
    
    def validate(self) -> bool:
        """Run all validations.
        
        Returns:
            True if no errors found, False otherwise
        """
        try:
            self.parse_tasks()
            
            if not self.tasks:
                self.warnings.append("No tasks found in TASK.md")
                return True
            
            self.validate_task_ids()
            self.validate_task_properties()
            self.validate_dependencies()
            self.validate_pr_links()
            self.validate_sprint_consistency()
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.errors.append(f"Validation failed: {str(e)}")
        
        return len(self.errors) == 0
    
    def report(self) -> None:
        """Print validation report.
        
        Outputs a formatted report of validation results including
        errors, warnings, and summary statistics.
        """
        print(f"\nTask Validation Report for {self.file_path}")
        print("=" * 60)
        print(f"Tasks found: {len(self.tasks)}")
        
        if self.tasks:
            # Summary statistics
            status_counts = {}
            for task in self.tasks:
                status_counts[task.status] = status_counts.get(task.status, 0) + 1
            
            print("\nTask Status Summary:")
            for status, count in sorted(status_counts.items()):
                print(f"  {status}: {count}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        
        # Log summary
        logger.info(
            "Validation complete",
            extra={
                "file": str(self.file_path),
                "tasks": len(self.tasks),
                "errors": len(self.errors),
                "warnings": len(self.warnings)
            }
        )


def main() -> None:
    """Main entry point for task validation.
    
    Parses command line arguments and runs validation.
    """
    if len(sys.argv) != 2:
        print("Usage: python validate_tasks.py <path_to_TASK.md>")
        print("\nExample: python validate_tasks.py planning/TASK.md")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        validator = TaskValidator(file_path)
        is_valid = validator.validate()
        validator.report()
        
        # Exit with appropriate code
        sys.exit(0 if is_valid else 1)
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

#### 6.3 Add Nox Validation Session
**File**: `noxfile.py` (addition)
```python
@nox.session
def validate_tasks(session: nox.Session) -> None:
    """Validate TASK.md format and consistency.
    
    Args:
        session: The nox session object
    """
    session.install("pydantic", "tabulate")
    session.run("python", "scripts/validate_tasks.py", "planning/TASK.md")

#### 2.2 Create Sprint Configuration Management
**File**: `planning/sprint.config.json`
```json
{
  "sprint_id": "Sprint-07-2025",
  "sprint_number": 7,
  "version": "v1.1.0",
  "start_date": "2025-07-06",
  "end_date": "2025-07-20",
  "duration_days": 14,
  "target_points": 20,
  "last_sprint_velocity": 21
}
```

#### 2.3 Create Auto-Update Commit Hook (Robust Version)
**File**: `.github/workflows/auto-update-metadata.yml`
```yaml
name: Auto-Update Task Metadata
on:
  push:
    paths:
      - 'planning/TASK.md'
      - 'planning/sprint.config.json'
  schedule:
    - cron: '0 */6 * * *'  # Update every 6 hours

jobs:
  update-metadata:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
          
      - name: Load sprint configuration
        id: config
        run: |
          # Read sprint config with validation
          if [[ ! -f planning/sprint.config.json ]]; then
            echo "Error: sprint.config.json not found"
            exit 1
          fi
          
          SPRINT_ID=$(jq -r '.sprint_id' planning/sprint.config.json)
          SPRINT_NUMBER=$(jq -r '.sprint_number' planning/sprint.config.json)
          VERSION=$(jq -r '.version' planning/sprint.config.json)
          
          echo "sprint_id=$SPRINT_ID" >> $GITHUB_OUTPUT
          echo "sprint_number=$SPRINT_NUMBER" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          
      - name: Update timestamp and metrics (Safe Regex)
        run: |
          TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
          
          # Use # delimiter to avoid escaping issues
          sed -i "s#Last Updated\]: .* (\*auto-updated on commit\*)#Last Updated]: ${TIMESTAMP} (*auto-updated on commit*)#" planning/TASK.md
          
          # Update sprint metadata from config
          sed -i "s#Sprint Number\]: [0-9]*#Sprint Number]: ${{ steps.config.outputs.sprint_number }}#" planning/TASK.md
          
          # Calculate sprint metrics safely
          if grep -q "| T-" planning/TASK.md; then
            # Count task statuses with safer grep patterns
            TOTAL=$(grep -c "^| T-[0-9]" planning/TASK.md || echo "0")
            COMPLETED=$(grep -c "| Done |" planning/TASK.md || echo "0")
            IN_PROGRESS=$(grep -c "| In Progress |" planning/TASK.md || echo "0")
            BLOCKED=$(grep -c "| Blocked |" planning/TASK.md || echo "0")
            
            # Calculate progress percentage safely
            if [ "$TOTAL" -gt 0 ]; then
              PROGRESS=$((COMPLETED * 100 / TOTAL))
            else
              PROGRESS=0
            fi
            
            # Update sprint dashboard with safe replacements
            awk -v prog="$PROGRESS" '/\*\*Sprint Progress\*\*/ { gsub(/[0-9]+%/, prog"%"); print; next } 1' planning/TASK.md > tmp && mv tmp planning/TASK.md
            awk -v blocked="$BLOCKED" '/\*\*Blocked Tasks\*\*/ { gsub(/[0-9]+/, blocked); print; next } 1' planning/TASK.md > tmp && mv tmp planning/TASK.md
          fi
          
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "Auto-Update Bot"
          
          if [[ -n $(git status --porcelain) ]]; then
            git add planning/TASK.md
            git commit -m "auto: update task metadata and timestamps
            
            - Updated last modified timestamp
            - Refreshed sprint dashboard metrics  
            - Auto-calculated progress indicators"
            git push
          fi
```# 🤖 TASK.md Automation Implementation Plan

## 📋 OVERVIEW
This plan implements automated file rotation, GitHub label synchronization, document evolution tracking, and PR linking for the TASK.md governance system.

---

## 🎯 IMPLEMENTATION PHASES

### Phase 1: Document Structure Updates (1-2 hours)
#### 1.1 Update TASK.md Template
**Add Document Changelog Section**:
```markdown
## 📜 DOCUMENT CHANGELOG
- **v1.0.0** (2025-07-10) – Initial sprint file creation
- **v1.1.0** (2025-07-12) – Added review status column and PR links
- **v1.1.1** (2025-07-14) – Corrected dependency mapping for T-004
```

**Add PR Link Column to Task Table**:
```markdown
| ID | Title | Priority | Points | Status | Reviewed | Owner | PR Link | ETA | Depends On | Notes |
|----|-------|----------|--------|--------|----------|-------|---------|-----|------------|-------|
| T-001 | Auth Middleware | High | 8 | Review | 🔍 | @devA | [#123](../pulls/123) | 2025-07-15 | - | Awaiting security review |
```

#### 1.2 Create Label Configuration File
**File**: `.github/labels.yml`
```yaml
# Priority Labels
- name: "priority/critical"
  color: "d73a4a"
  description: "Production issue, security vulnerability"
- name: "priority/high"
  color: "d93f0b"
  description: "Sprint goal dependency, user-facing feature"
- name: "priority/medium"
  color: "fbca04"
  description: "Important but not sprint-critical"
- name: "priority/low"
  color: "0e8a16"
  description: "Nice-to-have, technical debt, documentation"

# Type Labels
- name: "type/feature"
  color: "1d76db"
  description: "New feature development"
- name: "type/bug"
  color: "d73a4a"
  description: "Bug fixes and hotfixes"
- name: "type/refactor"
  color: "5319e7"
  description: "Code refactoring tasks"
- name: "type/tech-debt"
  color: "fbca04"
  description: "Technical debt cleanup"

# Status Labels
- name: "status/not-started"
  color: "ffffff"
  description: "Ready to begin"
- name: "status/in-progress"
  color: "0052cc"
  description: "Actively being worked on"
- name: "status/blocked"
  color: "d73a4a"
  description: "Waiting for external dependency"
- name: "status/review"
  color: "0e8a16"
  description: "Code complete, awaiting peer review"
- name: "status/testing"
  color: "fbca04"
  description: "In QA or integration testing"

# Sprint Labels (dynamic - created per sprint)
- name: "sprint/Sprint-07-2025"
  color: "c2e0c6"
  description: "Sprint 07 July 2025"
```

---

### Phase 2: Automated File Rotation (4-6 hours)
#### 2.1 Create Task Archive GitHub Action
**File**: `.github/workflows/task-archive.yml`
```yaml
name: Task File Archive
on:
  repository_dispatch:
    types: [new-sprint]
  workflow_dispatch:
    inputs:
      sprint_id:
        description: 'New Sprint ID (e.g., Sprint-08-2025)'
        required: true
      version:
        description: 'Archive version (e.g., v1.0.0)'
        required: true
        default: 'v1.0.0'
      sprint_duration:
        description: 'Sprint duration in days'
        required: false
        default: '14'

jobs:
  archive-tasks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          
      - name: Calculate sprint metadata
        id: sprint-meta
        run: |
          # Extract sprint number from ID (Sprint-07-2025 -> 7)
          SPRINT_NUMBER=$(echo "${{ github.event.inputs.sprint_id }}" | grep -oP '(?<=Sprint-)\d+')
          
          # Calculate sprint dates
          START_DATE=$(date +%Y-%m-%d)
          DURATION=${{ github.event.inputs.sprint_duration }}
          END_DATE=$(date -d "$START_DATE + $DURATION days" +%Y-%m-%d)
          
          echo "sprint_number=$SPRINT_NUMBER" >> $GITHUB_OUTPUT
          echo "start_date=$START_DATE" >> $GITHUB_OUTPUT
          echo "end_date=$END_DATE" >> $GITHUB_OUTPUT
          
      - name: Archive current TASK.md
        run: |
          # Extract current sprint ID from TASK.md
          CURRENT_SPRINT=$(grep -oP '(?<=# 📋 TASK MANAGEMENT – ).*' planning/TASK.md)
          ARCHIVE_VERSION="${{ github.event.inputs.version || 'v1.0.0' }}"
          
          # Create archive directory
          mkdir -p "docs/sprint-archives/${CURRENT_SPRINT}"
          
          # Copy and rename TASK.md
          cp planning/TASK.md "docs/sprint-archives/${CURRENT_SPRINT}/TASK-${ARCHIVE_VERSION}.md"
          
          # Update file version reference in archived file
          sed -i "s/File Version: TASK-v.*\.md/File Version: TASK-${ARCHIVE_VERSION}.md (ARCHIVED $(date +%Y-%m-%d))/" \
            "docs/sprint-archives/${CURRENT_SPRINT}/TASK-${ARCHIVE_VERSION}.md"
            
      - name: Create new TASK.md for next sprint
        run: |
          NEW_SPRINT="${{ github.event.inputs.sprint_id }}"
          SPRINT_NUMBER="${{ steps.sprint-meta.outputs.sprint_number }}"
          START_DATE="${{ steps.sprint-meta.outputs.start_date }}"
          END_DATE="${{ steps.sprint-meta.outputs.end_date }}"
          TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
          
          # Copy template and update sprint references
          cp planning/TASK-template.md planning/TASK.md
          
          # Update all sprint metadata
          sed -i "s/Sprint-07-2025/${NEW_SPRINT}/g" planning/TASK.md
          sed -i "s/Sprint Number\]: 7/Sprint Number]: ${SPRINT_NUMBER}/" planning/TASK.md
          sed -i "s/Sprint Dates\]: .*/Sprint Dates]: ${START_DATE} to ${END_DATE} *(auto-generated via CI)*/" planning/TASK.md
          sed -i "s/Last Updated\]: .*/Last Updated]: ${TIMESTAMP} *(auto-updated on commit)*/" planning/TASK.md
          sed -i "s/File Version: TASK-v.*\.md/File Version: TASK-v1.0.0.md/" planning/TASK.md
          
          # Reset document changelog
          sed -i '/## 📜 DOCUMENT CHANGELOG/,/^$/c\
## 📜 DOCUMENT CHANGELOG\
- **v1.0.0** ('$(date +%Y-%m-%d)') – Initial sprint file creation for '${NEW_SPRINT}'\
' planning/TASK.md
          
      - name: Update sprint archives index
        run: |
          # Create or update sprint archives index
          cat > docs/sprint-archives/README.md << EOF
          # 📁 Sprint Archives
          
          Historical sprint task files for compliance and retrospective analysis.
          
          ## Available Sprints
          $(find docs/sprint-archives -name "TASK-*.md" | sort | while read file; do
            sprint=$(basename $(dirname "$file"))
            version=$(basename "$file" | grep -oP 'TASK-\K.*(?=\.md)')
            echo "- **${sprint}**: [TASK-${version}.md](./${sprint}/TASK-${version}.md)"
          done)
          
          ## Archive Structure
          \`\`\`
          docs/sprint-archives/
          ├── Sprint-07-2025/
          │   ├── TASK-v1.0.0.md
          │   └── TASK-v1.1.0.md
          └── Sprint-08-2025/
              └── TASK-v1.0.0.md
          \`\`\`
          
          Last Updated: $(date)
          EOF
          
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git commit -m "feat: archive sprint tasks and create new sprint file
          
          - Archived current sprint to docs/sprint-archives/
          - Created new TASK.md for ${{ github.event.inputs.sprint_id }}
          - Updated sprint archives index"
          git push
```

#### 2.2 Create Sprint Template File
**File**: `planning/TASK-template.md`
```markdown
# 📋 TASK MANAGEMENT – Sprint-07-2025

> **AI Assistants**: Read [PLANNING.md](PLANNING.md) first for project context, then work on tasks listed below following [CLAUDE.md](../CLAUDE.md) standards.
> **File Version**: TASK-v1.0.0.md (immutable sprint snapshot for governance/compliance)

**Sprint ID**: Sprint-07-2025  
**Sprint**: [Sprint Number] ([YYYY-MM-DD] to [YYYY-MM-DD])  
**Last Updated**: [YYYY-MM-DD HH:MM]  
**Sprint Goal**: [Brief description of sprint objective]

## 📜 DOCUMENT CHANGELOG
- **v1.0.0** (YYYY-MM-DD) – Initial sprint file creation

---

## 🧩 CURRENT SPRINT TASKS

**Sprint Status Summary**: ✅ Completed: 0 | 🔄 In Progress: 0 | 🚫 Blocked: 0 | 📋 Not Started: 0 | **Total: 0**

| ID | Title | Description | Priority | Points | Status | Reviewed | Owner | PR Link | ETA | Depends On | Sprint ID | Notes |
|----|-------|-------------|----------|--------|--------|----------|-------|---------|-----|------------|-----------|-------|
| T-001 | [Sample Task] | [Add your first task here] | Medium | 3 | Not Started | ✖️ | @dev | - | YYYY-MM-DD | - | Sprint-07-2025 | Ready for assignment |

[Rest of template content...]
```

---

### Phase 3: Label Synchronization Validation (2-3 hours)
#### 3.1 Create Label Sync Workflow
**File**: `.github/workflows/label-sync.yml`
```yaml
name: Sync GitHub Labels
on:
  push:
    paths:
      - '.github/labels.yml'
  workflow_dispatch:

jobs:
  sync-labels:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Sync labels
        uses: crazy-max/ghaction-github-labeler@v4
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          yaml-file: .github/labels.yml
          skip-delete: false
          dry-run: false
```

#### 3.2 Add Label Validation Checklist to TASK.md
```markdown
### GitHub Label Synchronization Checklist
**Verify Required Labels Exist in Repository**:
- [ ] **Priority Labels**: `priority/critical`, `priority/high`, `priority/medium`, `priority/low`
- [ ] **Type Labels**: `type/feature`, `type/bug`, `type/refactor`, `type/tech-debt`
- [ ] **Status Labels**: `status/not-started`, `status/in-progress`, `status/blocked`, `status/review`, `status/testing`
- [ ] **Sprint Labels**: `sprint/Sprint-XX-YYYY` (created per sprint)

**Setup Commands**:
```bash
# Validate label configuration
gh api repos/:owner/:repo/labels | jq '.[].name' | grep -E "(priority|type|status|sprint)/"

# Apply labels from configuration
gh workflow run label-sync.yml
```

**CI Validation**: Labels are automatically validated in `.github/workflows/label-sync.yml` on every push to `.github/labels.yml`
```

---

### Phase 4: Enhanced Task Sync Automation (6-8 hours)
#### 4.1 Update Task Sync Action
**File**: `.github/workflows/task-sync.yml`
```yaml
name: Sync Tasks with GitHub Issues
on:
  issues:
    types: [opened, closed, reopened, labeled, unlabeled]
  pull_request:
    types: [opened, closed, merged, reopened]
  workflow_dispatch:

jobs:
  sync-tasks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          
      - name: Install dependencies
        run: |
          npm install js-yaml @octokit/rest
          
      - name: Sync task status
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const yaml = require('js-yaml');
            
            // Read current TASK.md
            const taskFile = fs.readFileSync('planning/TASK.md', 'utf8');
            
            // Extract task_id from issue body with validation
            const getTaskId = (body) => {
              if (!body) return null;
              const match = body.match(/task_id:\s*(T-\d+)/i);
              return match ? match[1] : null;
            };
            
            // Validate task_id exists and is unique
            const validateTaskId = async (taskId) => {
              if (!taskId) {
                core.setFailed("Missing task_id: in PR or issue body. Cannot sync to TASK.md.");
                return false;
              }
              
              // Check if task exists in TASK.md
              const taskExists = taskFile.includes(`| ${taskId} |`);
              if (!taskExists) {
                core.warning(`Task ${taskId} not found in TASK.md. Creating new entry.`);
              }
              
              return true;
            };
            
            // Safe changelog update using anchor
            const updateChangelog = (content, changelogEntry) => {
              const anchor = '<!-- changelog-insert-point -->';
              const anchorIndex = content.indexOf(anchor);
              
              if (anchorIndex === -1) {
                core.warning("Changelog anchor not found. Skipping changelog update.");
                return content;
              }
              
              const before = content.substring(0, anchorIndex + anchor.length);
              const after = content.substring(anchorIndex + anchor.length);
              
              return before + '\n' + changelogEntry + after;
            };
            
            // Determine status from GitHub issue/PR state
            const getStatusFromGitHub = (issue, pr = null) => {
              if (pr) {
                if (pr.merged) return 'Done';
                if (pr.state === 'open') return 'Review';
                if (pr.state === 'closed') return 'Blocked';
              }
              
              if (issue.state === 'closed') return 'Done';
              
              const labels = issue.labels.map(l => l.name);
              if (labels.includes('status/in-progress')) return 'In Progress';
              if (labels.includes('status/blocked')) return 'Blocked';
              if (labels.includes('status/review')) return 'Review';
              if (labels.includes('status/testing')) return 'Testing';
              
              return 'Not Started';
            };
            
            // Get review status from PR
            const getReviewStatus = async (taskId) => {
              const prs = await github.rest.pulls.list({
                owner: context.repo.owner,
                repo: context.repo.repo,
                state: 'all'
              });
              
              const taskPR = prs.data.find(pr => 
                pr.body?.includes(`task_id: ${taskId}`) || 
                pr.title.includes(taskId)
              );
              
              if (!taskPR) return '✖️';
              if (taskPR.merged) return '✔️';
              if (taskPR.state === 'open') return '🔍';
              
              // Check for requested changes
              const reviews = await github.rest.pulls.listReviews({
                owner: context.repo.owner,
                repo: context.repo.repo,
                pull_number: taskPR.number
              });
              
              const hasChangesRequested = reviews.data.some(r => r.state === 'CHANGES_REQUESTED');
              return hasChangesRequested ? '⚠️' : '🔍';
            };
            
            // Update task in TASK.md
            const updateTask = async (taskId, newStatus, reviewStatus, prLink = null) => {
              let updatedContent = taskFile;
              
              // Find task row and update status
              const taskRegex = new RegExp(
                `(\\| ${taskId} \\|[^|]+\\|[^|]+\\|[^|]+\\|[^|]+\\|[^|]+\\|)([^|]+)(\\|[^|]+\\|)([^|]+)(\\|.*)`,
                'g'
              );
              
              updatedContent = updatedContent.replace(taskRegex, (match, p1, oldStatus, p3, oldReview, p5) => {
                const prColumn = prLink ? ` [#${prLink}](../pull/${prLink}) ` : p3;
                return `${p1} ${newStatus} ${prColumn} ${reviewStatus} ${p5}`;
              });
              
              // Update document changelog
              const now = new Date().toISOString().split('T')[0];
              const changelogUpdate = `- **v1.1.${Date.now() % 1000}** (${now}) – Auto-sync: ${taskId} status → ${newStatus}`;
              
              updatedContent = updatedContent.replace(
                /(## 📜 DOCUMENT CHANGELOG\n)/,
                `$1${changelogUpdate}\n`
              );
              
              fs.writeFileSync('planning/TASK.md', updatedContent);
            };
            
            // Process current event with validation
            if (context.eventName === 'issues') {
              const taskId = getTaskId(context.payload.issue.body);
              if (!(await validateTaskId(taskId))) return;
              
              const status = getStatusFromGitHub(context.payload.issue);
              const reviewStatus = await getReviewStatus(taskId);
              await updateTask(taskId, status, reviewStatus);
            }
            
            if (context.eventName === 'pull_request') {
              const taskId = getTaskId(context.payload.pull_request.body);
              if (!(await validateTaskId(taskId))) return;
              
              const status = getStatusFromGitHub(null, context.payload.pull_request);
              const reviewStatus = await getReviewStatus(taskId);
              const prNumber = context.payload.pull_request.number;
              await updateTask(taskId, status, reviewStatus, prNumber);
            }
            
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Task Sync"
          
          if [[ -n $(git status --porcelain) ]]; then
            git add planning/TASK.md
            git commit -m "auto: sync task status from GitHub issue/PR events
            
            - Updated task status based on issue/PR state changes
            - Synced review status from PR reviews
            - Added changelog entry for audit trail"
            git push
          fi
```

---

### Phase 5: Validation & Testing (3-4 hours)
#### 5.1 Create Test Scenarios
**File**: `tests/task-automation-tests.md`
```markdown
# Task Automation Test Scenarios

## Test 1: File Rotation
1. Trigger `task-archive.yml` workflow
2. Verify old TASK.md archived to correct location
3. Verify new TASK.md created with correct sprint ID
4. Verify document changelog reset

## Test 2: Label Sync
1. Update `.github/labels.yml`
2. Verify `label-sync.yml` runs automatically
3. Check repository labels match configuration
4. Verify validation checklist items

## Test 3: Task Status Sync
1. Create GitHub issue with `task_id: T-XXX`
2. Apply status labels to issue
3. Verify TASK.md updates automatically
4. Create PR referencing task
5. Verify review status updates

## Test 4: Document Changelog
1. Make manual update to TASK.md
2. Verify changelog entry added
3. Check version increment logic
4. Verify archive process preserves history
```

#### 5.2 Create Documentation
**File**: `docs/automation/README.md`
```markdown
# Task Management Automation

## Overview
Automated workflows for TASK.md management, GitHub synchronization, and compliance archiving.

## Workflows
- **task-archive.yml**: Automated sprint file rotation and archiving
- **task-sync.yml**: Bidirectional GitHub issue/PR synchronization
- **label-sync.yml**: GitHub label configuration management

## Setup Instructions
1. Configure `.github/labels.yml` with required labels
2. Run label sync workflow to create labels
3. Use issue templates with `task_id:` references
4. Trigger sprint archive at sprint boundaries

## Maintenance
- Review sync logs weekly for any failures
- Update label configuration as needed
- Archive old sprints before starting new ones
```

---

## 📅 IMPLEMENTATION TIMELINE

| Phase | Duration | Dependencies | Deliverables |
|-------|----------|--------------|--------------|
| **Phase 1** | 1-2 hours | None | Updated TASK.md template, label config |
| **Phase 2** | 4-6 hours | Phase 1 | File rotation automation with config management |
| **Phase 3** | 2-3 hours | Phase 1 | Label sync validation |
| **Phase 4** | 6-8 hours | Phases 1-3 | Enhanced task sync with robust error handling |
| **Phase 5** | 3-4 hours | All phases | Testing & documentation |
| **Phase 6** | 3-4 hours | Phase 1 | Task validation system |

**Total Estimated Time**: 19-27 hours

---

## 🎯 SUCCESS METRICS

### Automation Goals
- **File Rotation**: 100% automated sprint transitions
- **Status Sync**: <5 minute lag between GitHub and TASK.md updates
- **Label Compliance**: 100% label validation coverage
- **Audit Trail**: Complete change history in document changelog

### Quality Metrics
- **Zero Manual Sync**: No human intervention required for status updates
- **Compliance Ready**: All sprint files archived with proper versioning
- **Team Efficiency**: 90% reduction in task management overhead
- **Error Rate**: <1% sync failures requiring manual intervention

---

## 🚀 ROLLOUT STRATEGY

### Week 1: Foundation
- Implement Phase 1 (template updates)
- Create label configuration
- Test manual processes

### Week 2: Core Automation
- Deploy Phase 2 (file rotation)
- Deploy Phase 3 (label sync)
- Validate with test sprint

### Week 3: Advanced Features
- Deploy Phase 4 (task sync)
- Full integration testing
- Team training

### Week 4: Production
- Go-live with automation
- Monitor and tune
- Document lessons learned

---

## 🔧 MAINTENANCE PLAN

### Daily
- Monitor workflow execution logs
- Verify sync status accuracy

### Weekly
- Review failed sync attempts
- Update label configuration if needed
- Archive completed sprints

### Monthly
- Analyze automation metrics
- Optimize workflow performance
- Update documentation

---

This implementation plan creates a fully automated, compliance-ready task management system that eliminates manual overhead while maintaining audit trails and process transparency., task.id):
                self.errors.append(f"Invalid task ID format: {task.id}")
            
            # Check uniqueness
            if task.id in seen_ids:
                self.errors.append(f"Duplicate task ID: {task.id}")
            seen_ids.add(task.id)
    
    def validate_task_properties(self) -> None:
        """Validate task property values."""
        for task in self.tasks:
            # Priority validation
            if task.priority not in self.VALID_PRIORITIES:
                self.errors.append(f"Invalid priority '{task.priority}' for task {task.id}")
            
            # Status validation
            if task.status not in self.VALID_STATUSES:
                self.errors.append(f"Invalid status '{task.status}' for task {task.id}")
            
            # Review status validation
            if task.reviewed not in self.VALID_REVIEW_STATUSES:
                self.errors.append(f"Invalid review status '{task.reviewed}' for task {task.id}")
            
            # Points validation
            if task.points not in self.VALID_POINTS:
                self.warnings.append(f"Unusual story points {task.points} for task {task.id}")
            
            # Owner validation
            if not task.owner or task.owner == '-':
                self.warnings.append(f"No owner assigned to task {task.id}")
    
    def validate_dependencies(self) -> None:
        """Validate task dependencies."""
        task_ids = {task.id for task in self.tasks}
        
        for task in self.tasks:
            if task.depends_on and task.depends_on != '-':
                deps = [dep.strip() for dep in task.depends_on.split(',')]
                for dep in deps:
                    if dep not in task_ids:
                        self.errors.append(f"Task {task.id} depends on non-existent task {dep}")
    
    def validate_pr_links(self) -> None:
        """Validate PR link format."""
        pr_pattern = r'\[#(\d+)\]\(\.\.\/pull\/\1\)'
        
        for task in self.tasks:
            if task.pr_link and task.pr_link != '-':
                if not re.match(pr_pattern, task.pr_link):
                    self.warnings.append(f"Invalid PR link format for task {task.id}: {task.pr_link}")
    
    def validate_sprint_consistency(self) -> None:
        """Validate sprint ID consistency."""
        sprint_ids = {task.sprint_id for task in self.tasks if task.sprint_id}
        
        if len(sprint_ids) > 1:
            self.warnings.append(f"Multiple sprint IDs found: {sprint_ids}")
    
    def validate(self) -> bool:
        """Run all validations."""
        self.parse_tasks()
        
        if not self.tasks:
            self.warnings.append("No tasks found in TASK.md")
            return True
        
        self.validate_task_ids()
        self.validate_task_properties()
        self.validate_dependencies()
        self.validate_pr_links()
        self.validate_sprint_consistency()
        
        return len(self.errors) == 0
    
    def report(self) -> None:
        """Print validation report."""
        print(f"Task Validation Report for {self.file_path}")
        print("=" * 50)
        print(f"Tasks found: {len(self.tasks)}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")

def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_tasks.py <path_to_TASK.md>")
        sys.exit(1)
    
    validator = TaskValidator(sys.argv[1])
    is_valid = validator.validate()
    validator.report()
    
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
```

#### 6.3 Add Nox Validation Session
**File**: `noxfile.py` (addition)
```python
@nox.session
def validate_tasks(session):
    """Validate TASK.md format and consistency."""
    session.install("pydantic", "tabulate")
    session.run("python", "scripts/validate_tasks.py", "planning/TASK.md")
```#### 2.2 Create Sprint Configuration Management
**File**: `planning/sprint.config.json`
```json
{
  "sprint_id": "Sprint-07-2025",
  "sprint_number": 7,
  "version": "v1.1.0",
  "start_date": "2025-07-06",
  "end_date": "2025-07-20",
  "duration_days": 14,
  "target_points": 20,
  "last_sprint_velocity": 21
}
```

#### 2.3 Create Auto-Update Commit Hook (Robust Version)
**File**: `.github/workflows/auto-update-metadata.yml`
```yaml
name: Auto-Update Task Metadata
on:
  push:
    paths:
      - 'planning/TASK.md'
      - 'planning/sprint.config.json'
  schedule:
    - cron: '0 */6 * * *'  # Update every 6 hours

jobs:
  update-metadata:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq
          
      - name: Load sprint configuration
        id: config
        run: |
          # Read sprint config with validation
          if [[ ! -f planning/sprint.config.json ]]; then
            echo "Error: sprint.config.json not found"
            exit 1
          fi
          
          SPRINT_ID=$(jq -r '.sprint_id' planning/sprint.config.json)
          SPRINT_NUMBER=$(jq -r '.sprint_number' planning/sprint.config.json)
          VERSION=$(jq -r '.version' planning/sprint.config.json)
          
          echo "sprint_id=$SPRINT_ID" >> $GITHUB_OUTPUT
          echo "sprint_number=$SPRINT_NUMBER" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          
      - name: Update timestamp and metrics (Safe Regex)
        run: |
          TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
          
          # Use # delimiter to avoid escaping issues
          sed -i "s#Last Updated\]: .* (\*auto-updated on commit\*)#Last Updated]: ${TIMESTAMP} (*auto-updated on commit*)#" planning/TASK.md
          
          # Update sprint metadata from config
          sed -i "s#Sprint Number\]: [0-9]*#Sprint Number]: ${{ steps.config.outputs.sprint_number }}#" planning/TASK.md
          
          # Calculate sprint metrics safely
          if grep -q "| T-" planning/TASK.md; then
            # Count task statuses with safer grep patterns
            TOTAL=$(grep -c "^| T-[0-9]" planning/TASK.md || echo "0")
            COMPLETED=$(grep -c "| Done |" planning/TASK.md || echo "0")
            IN_PROGRESS=$(grep -c "| In Progress |" planning/TASK.md || echo "0")
            BLOCKED=$(grep -c "| Blocked |" planning/TASK.md || echo "0")
            
            # Calculate progress percentage safely
            if [ "$TOTAL" -gt 0 ]; then
              PROGRESS=$((COMPLETED * 100 / TOTAL))
            else
              PROGRESS=0
            fi
            
            # Update sprint dashboard with safe replacements
            awk -v prog="$PROGRESS" '/\*\*Sprint Progress\*\*/ { gsub(/[0-9]+%/, prog"%"); print; next } 1' planning/TASK.md > tmp && mv tmp planning/TASK.md
            awk -v blocked="$BLOCKED" '/\*\*Blocked Tasks\*\*/ { gsub(/[0-9]+/, blocked); print; next } 1' planning/TASK.md > tmp && mv tmp planning/TASK.md
          fi
          
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "Auto-Update Bot"
          
          if [[ -n $(git status --porcelain) ]]; then
            git add planning/TASK.md
            git commit -m "auto: update task metadata and timestamps
            
            - Updated last modified timestamp
            - Refreshed sprint dashboard metrics  
            - Auto-calculated progress indicators"
            git push
          fi
```# 🤖 TASK.md Automation Implementation Plan

## 📋 OVERVIEW
This plan implements automated file rotation, GitHub label synchronization, document evolution tracking, and PR linking for the TASK.md governance system.

---

## 🎯 IMPLEMENTATION PHASES

### Phase 1: Document Structure Updates (1-2 hours)
#### 1.1 Update TASK.md Template
**Add Document Changelog Section**:
```markdown
## 📜 DOCUMENT CHANGELOG
- **v1.0.0** (2025-07-10) – Initial sprint file creation
- **v1.1.0** (2025-07-12) – Added review status column and PR links
- **v1.1.1** (2025-07-14) – Corrected dependency mapping for T-004
```

**Add PR Link Column to Task Table**:
```markdown
| ID | Title | Priority | Points | Status | Reviewed | Owner | PR Link | ETA | Depends On | Notes |
|----|-------|----------|--------|--------|----------|-------|---------|-----|------------|-------|
| T-001 | Auth Middleware | High | 8 | Review | 🔍 | @devA | [#123](../pulls/123) | 2025-07-15 | - | Awaiting security review |
```

#### 1.2 Create Label Configuration File
**File**: `.github/labels.yml`
```yaml
# Priority Labels
- name: "priority/critical"
  color: "d73a4a"
  description: "Production issue, security vulnerability"
- name: "priority/high"
  color: "d93f0b"
  description: "Sprint goal dependency, user-facing feature"
- name: "priority/medium"
  color: "fbca04"
  description: "Important but not sprint-critical"
- name: "priority/low"
  color: "0e8a16"
  description: "Nice-to-have, technical debt, documentation"

# Type Labels
- name: "type/feature"
  color: "1d76db"
  description: "New feature development"
- name: "type/bug"
  color: "d73a4a"
  description: "Bug fixes and hotfixes"
- name: "type/refactor"
  color: "5319e7"
  description: "Code refactoring tasks"
- name: "type/tech-debt"
  color: "fbca04"
  description: "Technical debt cleanup"

# Status Labels
- name: "status/not-started"
  color: "ffffff"
  description: "Ready to begin"
- name: "status/in-progress"
  color: "0052cc"
  description: "Actively being worked on"
- name: "status/blocked"
  color: "d73a4a"
  description: "Waiting for external dependency"
- name: "status/review"
  color: "0e8a16"
  description: "Code complete, awaiting peer review"
- name: "status/testing"
  color: "fbca04"
  description: "In QA or integration testing"

# Sprint Labels (dynamic - created per sprint)
- name: "sprint/Sprint-07-2025"
  color: "c2e0c6"
  description: "Sprint 07 July 2025"
```

---

### Phase 2: Automated File Rotation (4-6 hours)
#### 2.1 Create Task Archive GitHub Action
**File**: `.github/workflows/task-archive.yml`
```yaml
name: Task File Archive
on:
  repository_dispatch:
    types: [new-sprint]
  workflow_dispatch:
    inputs:
      sprint_id:
        description: 'New Sprint ID (e.g., Sprint-08-2025)'
        required: true
      version:
        description: 'Archive version (e.g., v1.0.0)'
        required: true
        default: 'v1.0.0'
      sprint_duration:
        description: 'Sprint duration in days'
        required: false
        default: '14'

jobs:
  archive-tasks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          
      - name: Calculate sprint metadata
        id: sprint-meta
        run: |
          # Extract sprint number from ID (Sprint-07-2025 -> 7)
          SPRINT_NUMBER=$(echo "${{ github.event.inputs.sprint_id }}" | grep -oP '(?<=Sprint-)\d+')
          
          # Calculate sprint dates
          START_DATE=$(date +%Y-%m-%d)
          DURATION=${{ github.event.inputs.sprint_duration }}
          END_DATE=$(date -d "$START_DATE + $DURATION days" +%Y-%m-%d)
          
          echo "sprint_number=$SPRINT_NUMBER" >> $GITHUB_OUTPUT
          echo "start_date=$START_DATE" >> $GITHUB_OUTPUT
          echo "end_date=$END_DATE" >> $GITHUB_OUTPUT
          
      - name: Archive current TASK.md
        run: |
          # Extract current sprint ID from TASK.md
          CURRENT_SPRINT=$(grep -oP '(?<=# 📋 TASK MANAGEMENT – ).*' planning/TASK.md)
          ARCHIVE_VERSION="${{ github.event.inputs.version || 'v1.0.0' }}"
          
          # Create archive directory
          mkdir -p "docs/sprint-archives/${CURRENT_SPRINT}"
          
          # Copy and rename TASK.md
          cp planning/TASK.md "docs/sprint-archives/${CURRENT_SPRINT}/TASK-${ARCHIVE_VERSION}.md"
          
          # Update file version reference in archived file
          sed -i "s/File Version: TASK-v.*\.md/File Version: TASK-${ARCHIVE_VERSION}.md (ARCHIVED $(date +%Y-%m-%d))/" \
            "docs/sprint-archives/${CURRENT_SPRINT}/TASK-${ARCHIVE_VERSION}.md"
            
      - name: Create new TASK.md for next sprint
        run: |
          NEW_SPRINT="${{ github.event.inputs.sprint_id }}"
          SPRINT_NUMBER="${{ steps.sprint-meta.outputs.sprint_number }}"
          START_DATE="${{ steps.sprint-meta.outputs.start_date }}"
          END_DATE="${{ steps.sprint-meta.outputs.end_date }}"
          TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
          
          # Copy template and update sprint references
          cp planning/TASK-template.md planning/TASK.md
          
          # Update all sprint metadata
          sed -i "s/Sprint-07-2025/${NEW_SPRINT}/g" planning/TASK.md
          sed -i "s/Sprint Number\]: 7/Sprint Number]: ${SPRINT_NUMBER}/" planning/TASK.md
          sed -i "s/Sprint Dates\]: .*/Sprint Dates]: ${START_DATE} to ${END_DATE} *(auto-generated via CI)*/" planning/TASK.md
          sed -i "s/Last Updated\]: .*/Last Updated]: ${TIMESTAMP} *(auto-updated on commit)*/" planning/TASK.md
          sed -i "s/File Version: TASK-v.*\.md/File Version: TASK-v1.0.0.md/" planning/TASK.md
          
          # Reset document changelog
          sed -i '/## 📜 DOCUMENT CHANGELOG/,/^$/c\
## 📜 DOCUMENT CHANGELOG\
- **v1.0.0** ('$(date +%Y-%m-%d)') – Initial sprint file creation for '${NEW_SPRINT}'\
' planning/TASK.md
          
      - name: Update sprint archives index
        run: |
          # Create or update sprint archives index
          cat > docs/sprint-archives/README.md << EOF
          # 📁 Sprint Archives
          
          Historical sprint task files for compliance and retrospective analysis.
          
          ## Available Sprints
          $(find docs/sprint-archives -name "TASK-*.md" | sort | while read file; do
            sprint=$(basename $(dirname "$file"))
            version=$(basename "$file" | grep -oP 'TASK-\K.*(?=\.md)')
            echo "- **${sprint}**: [TASK-${version}.md](./${sprint}/TASK-${version}.md)"
          done)
          
          ## Archive Structure
          \`\`\`
          docs/sprint-archives/
          ├── Sprint-07-2025/
          │   ├── TASK-v1.0.0.md
          │   └── TASK-v1.1.0.md
          └── Sprint-08-2025/
              └── TASK-v1.0.0.md
          \`\`\`
          
          Last Updated: $(date)
          EOF
          
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git commit -m "feat: archive sprint tasks and create new sprint file
          
          - Archived current sprint to docs/sprint-archives/
          - Created new TASK.md for ${{ github.event.inputs.sprint_id }}
          - Updated sprint archives index"
          git push
```

#### 2.2 Create Sprint Template File
**File**: `planning/TASK-template.md`
```markdown
# 📋 TASK MANAGEMENT – Sprint-07-2025

> **AI Assistants**: Read [PLANNING.md](PLANNING.md) first for project context, then work on tasks listed below following [CLAUDE.md](../CLAUDE.md) standards.
> **File Version**: TASK-v1.0.0.md (immutable sprint snapshot for governance/compliance)

**Sprint ID**: Sprint-07-2025  
**Sprint**: [Sprint Number] ([YYYY-MM-DD] to [YYYY-MM-DD])  
**Last Updated**: [YYYY-MM-DD HH:MM]  
**Sprint Goal**: [Brief description of sprint objective]

## 📜 DOCUMENT CHANGELOG
- **v1.0.0** (YYYY-MM-DD) – Initial sprint file creation

---

## 🧩 CURRENT SPRINT TASKS

**Sprint Status Summary**: ✅ Completed: 0 | 🔄 In Progress: 0 | 🚫 Blocked: 0 | 📋 Not Started: 0 | **Total: 0**

| ID | Title | Description | Priority | Points | Status | Reviewed | Owner | PR Link | ETA | Depends On | Sprint ID | Notes |
|----|-------|-------------|----------|--------|--------|----------|-------|---------|-----|------------|-----------|-------|
| T-001 | [Sample Task] | [Add your first task here] | Medium | 3 | Not Started | ✖️ | @dev | - | YYYY-MM-DD | - | Sprint-07-2025 | Ready for assignment |

[Rest of template content...]
```

---

### Phase 3: Label Synchronization Validation (2-3 hours)
#### 3.1 Create Label Sync Workflow
**File**: `.github/workflows/label-sync.yml`
```yaml
name: Sync GitHub Labels
on:
  push:
    paths:
      - '.github/labels.yml'
  workflow_dispatch:

jobs:
  sync-labels:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Sync labels
        uses: crazy-max/ghaction-github-labeler@v4
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          yaml-file: .github/labels.yml
          skip-delete: false
          dry-run: false
```

#### 3.2 Add Label Validation Checklist to TASK.md
```markdown
### GitHub Label Synchronization Checklist
**Verify Required Labels Exist in Repository**:
- [ ] **Priority Labels**: `priority/critical`, `priority/high`, `priority/medium`, `priority/low`
- [ ] **Type Labels**: `type/feature`, `type/bug`, `type/refactor`, `type/tech-debt`
- [ ] **Status Labels**: `status/not-started`, `status/in-progress`, `status/blocked`, `status/review`, `status/testing`
- [ ] **Sprint Labels**: `sprint/Sprint-XX-YYYY` (created per sprint)

**Setup Commands**:
```bash
# Validate label configuration
gh api repos/:owner/:repo/labels | jq '.[].name' | grep -E "(priority|type|status|sprint)/"

# Apply labels from configuration
gh workflow run label-sync.yml
```

**CI Validation**: Labels are automatically validated in `.github/workflows/label-sync.yml` on every push to `.github/labels.yml`
```

---

### Phase 4: Enhanced Task Sync Automation (6-8 hours)
#### 4.1 Update Task Sync Action
**File**: `.github/workflows/task-sync.yml`
```yaml
name: Sync Tasks with GitHub Issues
on:
  issues:
    types: [opened, closed, reopened, labeled, unlabeled]
  pull_request:
    types: [opened, closed, merged, reopened]
  workflow_dispatch:

jobs:
  sync-tasks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          
      - name: Install dependencies
        run: |
          npm install js-yaml @octokit/rest
          
      - name: Sync task status
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const yaml = require('js-yaml');
            
            // Read current TASK.md
            const taskFile = fs.readFileSync('planning/TASK.md', 'utf8');
            
            // Extract task_id from issue body with validation
            const getTaskId = (body) => {
              if (!body) return null;
              const match = body.match(/task_id:\s*(T-\d+)/i);
              return match ? match[1] : null;
            };
            
            // Validate task_id exists and is unique
            const validateTaskId = async (taskId) => {
              if (!taskId) {
                core.setFailed("Missing task_id: in PR or issue body. Cannot sync to TASK.md.");
                return false;
              }
              
              // Check if task exists in TASK.md
              const taskExists = taskFile.includes(`| ${taskId} |`);
              if (!taskExists) {
                core.warning(`Task ${taskId} not found in TASK.md. Creating new entry.`);
              }
              
              return true;
            };
            
            // Safe changelog update using anchor
            const updateChangelog = (content, changelogEntry) => {
              const anchor = '<!-- changelog-insert-point -->';
              const anchorIndex = content.indexOf(anchor);
              
              if (anchorIndex === -1) {
                core.warning("Changelog anchor not found. Skipping changelog update.");
                return content;
              }
              
              const before = content.substring(0, anchorIndex + anchor.length);
              const after = content.substring(anchorIndex + anchor.length);
              
              return before + '\n' + changelogEntry + after;
            };
            
            // Determine status from GitHub issue/PR state
            const getStatusFromGitHub = (issue, pr = null) => {
              if (pr) {
                if (pr.merged) return 'Done';
                if (pr.state === 'open') return 'Review';
                if (pr.state === 'closed') return 'Blocked';
              }
              
              if (issue.state === 'closed') return 'Done';
              
              const labels = issue.labels.map(l => l.name);
              if (labels.includes('status/in-progress')) return 'In Progress';
              if (labels.includes('status/blocked')) return 'Blocked';
              if (labels.includes('status/review')) return 'Review';
              if (labels.includes('status/testing')) return 'Testing';
              
              return 'Not Started';
            };
            
            // Get review status from PR
            const getReviewStatus = async (taskId) => {
              const prs = await github.rest.pulls.list({
                owner: context.repo.owner,
                repo: context.repo.repo,
                state: 'all'
              });
              
              const taskPR = prs.data.find(pr => 
                pr.body?.includes(`task_id: ${taskId}`) || 
                pr.title.includes(taskId)
              );
              
              if (!taskPR) return '✖️';
              if (taskPR.merged) return '✔️';
              if (taskPR.state === 'open') return '🔍';
              
              // Check for requested changes
              const reviews = await github.rest.pulls.listReviews({
                owner: context.repo.owner,
                repo: context.repo.repo,
                pull_number: taskPR.number
              });
              
              const hasChangesRequested = reviews.data.some(r => r.state === 'CHANGES_REQUESTED');
              return hasChangesRequested ? '⚠️' : '🔍';
            };
            
            // Update task in TASK.md
            const updateTask = async (taskId, newStatus, reviewStatus, prLink = null) => {
              let updatedContent = taskFile;
              
              // Find task row and update status
              const taskRegex = new RegExp(
                `(\\| ${taskId} \\|[^|]+\\|[^|]+\\|[^|]+\\|[^|]+\\|[^|]+\\|)([^|]+)(\\|[^|]+\\|)([^|]+)(\\|.*)`,
                'g'
              );
              
              updatedContent = updatedContent.replace(taskRegex, (match, p1, oldStatus, p3, oldReview, p5) => {
                const prColumn = prLink ? ` [#${prLink}](../pull/${prLink}) ` : p3;
                return `${p1} ${newStatus} ${prColumn} ${reviewStatus} ${p5}`;
              });
              
              // Update document changelog
              const now = new Date().toISOString().split('T')[0];
              const changelogUpdate = `- **v1.1.${Date.now() % 1000}** (${now}) – Auto-sync: ${taskId} status → ${newStatus}`;
              
              updatedContent = updatedContent.replace(
                /(## 📜 DOCUMENT CHANGELOG\n)/,
                `$1${changelogUpdate}\n`
              );
              
              fs.writeFileSync('planning/TASK.md', updatedContent);
            };
            
            // Process current event with validation
            if (context.eventName === 'issues') {
              const taskId = getTaskId(context.payload.issue.body);
              if (!(await validateTaskId(taskId))) return;
              
              const status = getStatusFromGitHub(context.payload.issue);
              const reviewStatus = await getReviewStatus(taskId);
              await updateTask(taskId, status, reviewStatus);
            }
            
            if (context.eventName === 'pull_request') {
              const taskId = getTaskId(context.payload.pull_request.body);
              if (!(await validateTaskId(taskId))) return;
              
              const status = getStatusFromGitHub(null, context.payload.pull_request);
              const reviewStatus = await getReviewStatus(taskId);
              const prNumber = context.payload.pull_request.number;
              await updateTask(taskId, status, reviewStatus, prNumber);
            }
            
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Task Sync"
          
          if [[ -n $(git status --porcelain) ]]; then
            git add planning/TASK.md
            git commit -m "auto: sync task status from GitHub issue/PR events
            
            - Updated task status based on issue/PR state changes
            - Synced review status from PR reviews
            - Added changelog entry for audit trail"
            git push
          fi
```

---

### Phase 5: Validation & Testing (3-4 hours)
#### 5.1 Create Test Scenarios
**File**: `tests/task-automation-tests.md`
```markdown
# Task Automation Test Scenarios

## Test 1: File Rotation
1. Trigger `task-archive.yml` workflow
2. Verify old TASK.md archived to correct location
3. Verify new TASK.md created with correct sprint ID
4. Verify document changelog reset

## Test 2: Label Sync
1. Update `.github/labels.yml`
2. Verify `label-sync.yml` runs automatically
3. Check repository labels match configuration
4. Verify validation checklist items

## Test 3: Task Status Sync
1. Create GitHub issue with `task_id: T-XXX`
2. Apply status labels to issue
3. Verify TASK.md updates automatically
4. Create PR referencing task
5. Verify review status updates

## Test 4: Document Changelog
1. Make manual update to TASK.md
2. Verify changelog entry added
3. Check version increment logic
4. Verify archive process preserves history
```

#### 5.2 Create Documentation
**File**: `docs/automation/README.md`
```markdown
# Task Management Automation

## Overview
Automated workflows for TASK.md management, GitHub synchronization, and compliance archiving.

## Workflows
- **task-archive.yml**: Automated sprint file rotation and archiving
- **task-sync.yml**: Bidirectional GitHub issue/PR synchronization
- **label-sync.yml**: GitHub label configuration management

## Setup Instructions
1. Configure `.github/labels.yml` with required labels
2. Run label sync workflow to create labels
3. Use issue templates with `task_id:` references
4. Trigger sprint archive at sprint boundaries

## Maintenance
- Review sync logs weekly for any failures
- Update label configuration as needed
- Archive old sprints before starting new ones
```

---

## 📅 IMPLEMENTATION TIMELINE

| Phase | Duration | Dependencies | Deliverables |
|-------|----------|--------------|--------------|
| **Phase 1** | 1-2 hours | None | Updated TASK.md template, label config |
| **Phase 2** | 4-6 hours | Phase 1 | File rotation automation |
| **Phase 3** | 2-3 hours | Phase 1 | Label sync validation |
| **Phase 4** | 6-8 hours | Phases 1-3 | Enhanced task sync |
| **Phase 5** | 3-4 hours | All phases | Testing & documentation |

**Total Estimated Time**: 16-23 hours

---

## 🎯 SUCCESS METRICS

### Automation Goals
- **File Rotation**: 100% automated sprint transitions
- **Status Sync**: <5 minute lag between GitHub and TASK.md updates
- **Label Compliance**: 100% label validation coverage
- **Audit Trail**: Complete change history in document changelog

### Quality Metrics
- **Zero Manual Sync**: No human intervention required for status updates
- **Compliance Ready**: All sprint files archived with proper versioning
- **Team Efficiency**: 90% reduction in task management overhead
- **Error Rate**: <1% sync failures requiring manual intervention

---

## 🚀 ROLLOUT STRATEGY

### Week 1: Foundation
- Implement Phase 1 (template updates)
- Create label configuration
- Test manual processes

### Week 2: Core Automation
- Deploy Phase 2 (file rotation)
- Deploy Phase 3 (label sync)
- Validate with test sprint

### Week 3: Advanced Features
- Deploy Phase 4 (task sync)
- Full integration testing
- Team training

### Week 4: Production
- Go-live with automation
- Monitor and tune
- Document lessons learned

---

## 🔧 MAINTENANCE PLAN

### Daily
- Monitor workflow execution logs
- Verify sync status accuracy

### Weekly
- Review failed sync attempts
- Update label configuration if needed
- Archive completed sprints

### Monthly
- Analyze automation metrics
- Optimize workflow performance
- Update documentation

---

This implementation plan creates a fully automated, compliance-ready task management system that eliminates manual overhead while maintaining audit trails and process transparency.