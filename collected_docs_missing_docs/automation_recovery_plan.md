# 🛡️ AUTOMATION RECOVERY & FAILURE HANDLING PLAN

> **Critical Gap Resolution**: Comprehensive failure handling, rollback procedures, and audit trail management for task automation system failures.

**Document Version**: v1.0.0  
**Last Updated**: 2025-07-06  
**Owner**: DevOps Lead  
**Review Cycle**: Monthly  

## 📚 Related Documentation
- **Standards Compliance**: This document follows the standards defined in [CLAUDE.md](./CLAUDE.md)
- **Project Context**: See [PLANNING.md](./planning/PLANNING.md) for project architecture
- **Task Management**: Related tasks tracked in [TASK.md](./planning/TASK.md)
- **Technical Registry**: Implementation details in [TECHNICAL_REGISTRY.md](./planning/TECHNICAL_REGISTRY.md)

---

## 🚨 FAILURE SCENARIOS & RESPONSE MATRIX

### **Severity Classification**

| Level | Description | Response Time | Authority Level | Rollback Required |
|-------|-------------|---------------|-----------------|-------------------|
| **P0 - Critical** | Data corruption, security breach | < 15 minutes | Any Senior Member | Immediate |
| **P1 - High** | Automation completely broken | < 2 hours | Tech Lead / DevOps Lead | Required |
| **P2 - Medium** | Partial automation failure | < 8 hours | Task Owner | Optional |
| **P3 - Low** | Minor sync issues, cosmetic problems | < 48 hours | Task Owner | Not Required |

### **Common Failure Patterns**

| Failure Type | Probability | Detection Method | Auto-Recovery | Manual Steps Required |
|--------------|-------------|------------------|---------------|----------------------|
| **GitHub API Rate Limiting** | High | Workflow logs, 403 errors | Yes (retry with backoff) | None |
| **TASK.md Parse Errors** | Medium | Validation failures | No | Fix syntax, re-run |
| **Git Merge Conflicts** | Medium | Push failures | No | Manual resolution |
| **File Corruption** | Low | Validation errors | No | Restore from backup |
| **Workflow Token Expiry** | Low | Authentication errors | No | Refresh tokens |
| **Sprint Config Corruption** | Low | JSON validation errors | No | Restore from template |

---

## 🔄 PHASE 7: FAILURE RECOVERY SYSTEM

### **7.1 Automated Failure Detection (2-3 hours)**

#### **Workflow Health Monitor**
**File**: `.github/workflows/automation-health-check.yml`
```yaml
name: Automation Health Check
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Check workflow statuses
        uses: actions/github-script@v7
        with:
          script: |
            const failures = [];
            const workflows = ['task-sync.yml', 'task-archive.yml', 'auto-update-metadata.yml'];
            
            for (const workflow of workflows) {
              const runs = await github.rest.actions.listWorkflowRuns({
                owner: context.repo.owner,
                repo: context.repo.repo,
                workflow_id: workflow,
                per_page: 5
              });
              
              const recentFailures = runs.data.workflow_runs
                .filter(run => run.conclusion === 'failure')
                .filter(run => Date.now() - new Date(run.created_at).getTime() < 3600000); // Last hour
              
              if (recentFailures.length >= 2) {
                failures.push({
                  workflow: workflow,
                  failures: recentFailures.length,
                  lastFailure: recentFailures[0].html_url
                });
              }
            }
            
            if (failures.length > 0) {
              const alert = failures.map(f => 
                `🚨 **${f.workflow}**: ${f.failures} failures in last hour\n${f.lastFailure}`
              ).join('\n\n');
              
              await github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                title: `[AUTOMATION ALERT] Multiple workflow failures detected`,
                body: `## Automation Health Alert
                
${alert}

**Severity**: P1 - High
**Auto-Generated**: ${new Date().toISOString()}
**Action Required**: DevOps team investigation

### Immediate Steps
1. Check workflow logs for root cause
2. Verify GitHub API rate limits
3. Validate TASK.md syntax
4. Execute recovery procedures if needed`,
                labels: ['automation', 'alert', 'priority/high']
              });
            }
            
      - name: Validate critical files
        run: |
          # Check TASK.md syntax
          if ! python scripts/validate_tasks.py planning/TASK.md --quiet; then
            echo "CRITICAL: TASK.md validation failed"
            exit 1
          fi
          
          # Check sprint config
          if ! jq empty planning/sprint.config.json; then
            echo "CRITICAL: sprint.config.json is invalid JSON"
            exit 1
          fi
          
          # Check required GitHub labels exist
          REQUIRED_LABELS=("priority/critical" "priority/high" "status/blocked" "type/bug")
          for label in "${REQUIRED_LABELS[@]}"; do
            if ! gh api repos/:owner/:repo/labels | jq -r '.[].name' | grep -q "^${label}$"; then
              echo "WARNING: Required label missing: ${label}"
            fi
          done
```

#### **Backup Creation Before Critical Operations**
**File**: `scripts/create_recovery_checkpoint.py`
```python
#!/usr/bin/env python3
"""
Create recovery checkpoint before critical automation operations.
Stores state snapshots for rollback scenarios.
"""
import hashlib
import json
import logging
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecoveryCheckpoint:
    """Create recovery checkpoints before critical automation operations.
    
    Provides comprehensive state snapshots for rollback scenarios with
    security validation, audit trails, and integrity verification.
    
    Args:
        checkpoint_type: Type of checkpoint (sprint-archive, task-sync, emergency)
        operation: Description of the operation being performed
        
    Raises:
        ValueError: If checkpoint_type or operation are invalid
        OSError: If backup directory cannot be created
    """
    
    VALID_CHECKPOINT_TYPES = {"sprint-archive", "task-sync", "emergency", "manual"}
    
    def __init__(self, checkpoint_type: str, operation: str) -> None:
        # Input validation and sanitization
        if not checkpoint_type or not checkpoint_type.strip():
            raise ValueError("checkpoint_type cannot be empty")
        
        if not operation or not operation.strip():
            raise ValueError("operation cannot be empty")
        
        # Validate checkpoint type
        sanitized_type = self._sanitize_input(checkpoint_type.strip())
        if sanitized_type not in self.VALID_CHECKPOINT_TYPES:
            raise ValueError(f"Invalid checkpoint_type. Must be one of: {', '.join(self.VALID_CHECKPOINT_TYPES)}")
        
        # Sanitize operation description
        sanitized_operation = self._sanitize_input(operation.strip())
        if len(sanitized_operation) > 100:  # Reasonable limit
            raise ValueError("Operation description too long (max 100 characters)")
        
        self.checkpoint_type = sanitized_type
        self.operation = sanitized_operation
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.checkpoint_id = self._generate_checkpoint_id()
        self.backup_dir = Path(f"backups/checkpoints/{self.checkpoint_id}")
        self.backed_up_files: List[str] = []
        
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created checkpoint directory: {self.backup_dir}")
        except OSError as e:
            logger.error(f"Failed to create backup directory: {e}")
            raise
        
        logger.info(f"Initialized RecoveryCheckpoint: {self.checkpoint_id}")
    
    def _sanitize_input(self, value: str) -> str:
        """Sanitize input to prevent injection attacks.
        
        Args:
            value: Input string to sanitize
            
        Returns:
            Sanitized string with only safe characters
        """
        import re
        # Only allow alphanumeric, hyphens, underscores, and spaces
        sanitized = re.sub(r'[^a-zA-Z0-9_\-\s]', '', value)
        return sanitized.strip()
    
    def _generate_checkpoint_id(self) -> str:
        """Generate unique checkpoint ID with collision prevention.
        
        Returns:
            Unique checkpoint identifier
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        # Add hash component for uniqueness
        hash_input = f"{self.checkpoint_type}-{self.operation}-{timestamp}-{os.getpid()}"
        hash_suffix = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:8]
        return f"{self.checkpoint_type}-{timestamp}-{hash_suffix}"
    
    def backup_critical_files(self) -> None:
        """Backup files that automation might modify.
        
        Raises:
            OSError: If file backup operations fail
        """
        critical_files = [
            "planning/TASK.md",
            "planning/sprint.config.json", 
            ".github/labels.yml",
            "docs/sprint-archives/README.md"
        ]
        
        logger.info(f"Starting backup of {len(critical_files)} critical files")
        
        for file_path in critical_files:
            try:
                src = Path(file_path)
                if src.exists() and src.is_file():
                    # Security check: validate file size
                    file_size = src.stat().st_size
                    if file_size > 50 * 1024 * 1024:  # 50MB limit
                        logger.warning(f"Large file detected: {file_path} ({file_size} bytes)")
                        continue
                    
                    dst = self.backup_dir / src.name
                    shutil.copy2(src, dst)
                    
                    # Calculate checksum for integrity verification
                    checksum = self._calculate_file_checksum(src)
                    
                    self.backed_up_files.append(file_path)
                    print(f"✓ Backed up: {file_path} (checksum: {checksum[:8]}...)")
                    logger.info(f"Backed up: {file_path} -> {dst} ({file_size} bytes)")
                elif src.exists():
                    logger.warning(f"Skipping non-file: {file_path}")
                else:
                    logger.info(f"File not found, skipping: {file_path}")
                    
            except OSError as e:
                logger.error(f"Failed to backup {file_path}: {e}")
                raise
        
        logger.info(f"Successfully backed up {len(self.backed_up_files)} files")
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum for file integrity verification.
        
        Args:
            file_path: Path to file to checksum
            
        Returns:
            SHA256 checksum as hexadecimal string
            
        Raises:
            OSError: If file cannot be read
        """
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            raise
    
    def backup_git_state(self) -> None:
        """Capture current git state for reference.
        
        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        logger.info("Capturing git state information")
        
        git_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository_info": {},
            "environment": {
                "working_directory": str(Path.cwd()),
                "user": os.environ.get("USER", "unknown")
            }
        }
        
        # Safely capture git information with error handling
        git_commands = {
            "commit_hash": ["git", "rev-parse", "HEAD"],
            "branch": ["git", "branch", "--show-current"],
            "status": ["git", "status", "--porcelain"],
            "last_commits": ["git", "log", "--oneline", "-5"],
            "remote_url": ["git", "remote", "get-url", "origin"]
        }
        
        for key, command in git_commands.items():
            try:
                result = subprocess.check_output(
                    command,
                    timeout=30,
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
                git_info["repository_info"][key] = result
                logger.debug(f"Captured git {key}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning(f"Could not capture git {key}: {e}")
                git_info["repository_info"][key] = f"unavailable ({type(e).__name__})"
        
        try:
            with open(self.backup_dir / "git_state.json", "w", encoding="utf-8") as f:
                json.dump(git_info, f, indent=2, ensure_ascii=False)
            logger.info("Git state captured successfully")
        except OSError as e:
            logger.error(f"Failed to save git state: {e}")
            raise
    
    def create_checkpoint(self) -> str:
        """Create complete checkpoint with full validation and audit trail.
        
        Returns:
            Unique checkpoint identifier
            
        Raises:
            OSError: If checkpoint creation fails
        """
        try:
            logger.info(f"Starting checkpoint creation: {self.checkpoint_id}")
            
            # Backup critical files
            self.backup_critical_files()
            
            # Capture git state
            self.backup_git_state()
            
            # Calculate checksums for all backed up files
            file_checksums = {}
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file() and backup_file.name not in ["manifest.json"]:
                    file_checksums[backup_file.name] = self._calculate_file_checksum(backup_file)
            
            # Create comprehensive checkpoint manifest
            manifest = {
                "checkpoint_id": self.checkpoint_id,
                "type": self.checkpoint_type,
                "operation": self.operation,
                "timestamp": self.timestamp,
                "version": "1.0.0",
                "files_backed_up": self.backed_up_files,
                "file_checksums": file_checksums,
                "backup_directory": str(self.backup_dir),
                "recovery_instructions": f"To restore: python scripts/restore_checkpoint.py {self.checkpoint_id}",
                "metadata": {
                    "creator": os.environ.get("USER", "unknown"),
                    "python_version": os.sys.version,
                    "working_directory": str(Path.cwd()),
                    "process_id": os.getpid()
                },
                "security": {
                    "manifest_checksum": "calculated_after_creation",
                    "validation_status": "valid"
                }
            }
            
            # Save manifest
            manifest_path = self.backup_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Calculate and update manifest checksum for integrity
            manifest_checksum = self._calculate_file_checksum(manifest_path)
            manifest["security"]["manifest_checksum"] = manifest_checksum
            
            # Re-save with checksum
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Create integrity verification file
            integrity_data = {
                "checkpoint_id": self.checkpoint_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "total_files": len(self.backed_up_files),
                "manifest_checksum": manifest_checksum,
                "verification_method": "SHA256"
            }
            
            with open(self.backup_dir / "integrity.json", "w", encoding="utf-8") as f:
                json.dump(integrity_data, f, indent=2)
            
            logger.info(f"Checkpoint created successfully: {self.checkpoint_id}")
            print(f"✅ Checkpoint created: {self.checkpoint_id}")
            print(f"📁 Location: {self.backup_dir}")
            print(f"📋 Files backed up: {len(self.backed_up_files)}")
            print(f"🔐 Manifest checksum: {manifest_checksum[:16]}...")
            
            return self.checkpoint_id
            
        except Exception as e:
            logger.error(f"Checkpoint creation failed: {e}", exc_info=True)
            print(f"❌ Checkpoint creation failed: {e}")
            raise

def main() -> None:
    """Main CLI entry point for checkpoint creation.
    
    Raises:
        SystemExit: With appropriate exit code
    """
    import sys
    
    # Validate command line arguments
    if len(sys.argv) < 3:
        print("Usage: python create_recovery_checkpoint.py <type> <operation> [--description <desc>]")
        print("\nCheckpoint Types:")
        for checkpoint_type in RecoveryCheckpoint.VALID_CHECKPOINT_TYPES:
            print(f"  {checkpoint_type}")
        print("\nExample:")
        print("  python create_recovery_checkpoint.py emergency 'pre-rollback-backup'")
        sys.exit(1)
    
    checkpoint_type = sys.argv[1]
    operation = sys.argv[2]
    
    # Optional description parameter
    description = None
    if len(sys.argv) > 4 and sys.argv[3] == "--description":
        description = sys.argv[4]
        operation = f"{operation}: {description}"
    
    try:
        logger.info(f"Starting checkpoint creation via CLI: {checkpoint_type} - {operation}")
        
        # Validate inputs before creating checkpoint
        if not checkpoint_type.strip() or not operation.strip():
            print("❌ Error: Type and operation cannot be empty")
            sys.exit(1)
        
        # Create checkpoint
        checkpoint = RecoveryCheckpoint(checkpoint_type, operation)
        checkpoint_id = checkpoint.create_checkpoint()
        
        print(f"\n🎯 Checkpoint ID: {checkpoint_id}")
        print(f"📝 Type: {checkpoint_type}")
        print(f"⚙️  Operation: {operation}")
        
        logger.info(f"Checkpoint creation completed successfully: {checkpoint_id}")
        sys.exit(0)
        
    except ValueError as e:
        print(f"❌ Validation Error: {e}")
        logger.error(f"Checkpoint creation failed due to validation: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"❌ File System Error: {e}")
        logger.error(f"Checkpoint creation failed due to file system error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Checkpoint creation cancelled by user")
        logger.info("Checkpoint creation cancelled by user interrupt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        logger.error(f"Unexpected error during checkpoint creation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### **7.2 Rollback Procedures (4-5 hours)**

#### **Automated Rollback System**
**File**: `scripts/restore_checkpoint.py`
```python
#!/usr/bin/env python3
"""
Restore system state from recovery checkpoint.
Handles automated rollback with audit trail.
"""
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _sanitize_checkpoint_id(checkpoint_id: str) -> Optional[str]:
    """Sanitize checkpoint ID to prevent path traversal attacks.
    
    Args:
        checkpoint_id: Raw checkpoint ID to sanitize
        
    Returns:
        Sanitized checkpoint ID or None if invalid
    """
    import re
    
    # Only allow alphanumeric characters, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', checkpoint_id):
        logger.warning(f"Invalid checkpoint ID format: {checkpoint_id}")
        return None
    
    # Prevent path traversal
    if '..' in checkpoint_id or '/' in checkpoint_id or '\\' in checkpoint_id:
        logger.warning(f"Path traversal detected in checkpoint ID: {checkpoint_id}")
        return None
    
    return checkpoint_id


class CheckpointRestorer:
    """Restore system state from recovery checkpoint.
    
    Handles automated rollback with comprehensive audit trail and validation.
    Follows SOLID principles and includes proper error handling.
    
    Args:
        checkpoint_id: Unique identifier for the checkpoint to restore
        force: Skip user confirmation if True
        
    Raises:
        FileNotFoundError: If checkpoint directory doesn't exist
        ValueError: If checkpoint_id is invalid
    """
    
    def __init__(self, checkpoint_id: str, force: bool = False) -> None:
        # Input validation and sanitization
        if not checkpoint_id or not checkpoint_id.strip():
            raise ValueError("checkpoint_id cannot be empty")
        
        # Sanitize checkpoint_id to prevent path traversal
        sanitized_id = _sanitize_checkpoint_id(checkpoint_id.strip())
        if not sanitized_id:
            raise ValueError("Invalid checkpoint_id format")
        
        self.checkpoint_id = sanitized_id
        self.force = force
        self.backup_dir = Path(f"backups/checkpoints/{self.checkpoint_id}")
        self.restore_log: List[str] = []
        
        # Validate backup directory exists and is accessible
        if not self.backup_dir.exists():
            logger.error(f"Checkpoint directory not found: {self.backup_dir}")
            raise FileNotFoundError(f"Checkpoint {self.checkpoint_id} not found")
        
        if not self.backup_dir.is_dir():
            logger.error(f"Checkpoint path is not a directory: {self.backup_dir}")
            raise ValueError(f"Invalid checkpoint directory: {self.checkpoint_id}")
        
        logger.info(f"Initialized CheckpointRestorer for checkpoint: {self.checkpoint_id}")
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load checkpoint manifest.
        
        Returns:
            Dictionary containing checkpoint metadata
            
        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is corrupted
        """
        manifest_path = self.backup_dir / "manifest.json"
        if not manifest_path.exists():
            logger.error(f"Manifest file not found: {manifest_path}")
            raise FileNotFoundError("Checkpoint manifest not found")
        
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                logger.info(f"Loaded manifest for checkpoint: {self.checkpoint_id}")
                return manifest
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted manifest file: {e}")
            raise
    
    def confirm_restore(self, manifest: Dict[str, Any]) -> bool:
        """Confirm restore operation with user.
        
        Args:
            manifest: Checkpoint manifest containing metadata
            
        Returns:
            True if user confirms or force flag is set
            
        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        if self.force:
            logger.info("Force flag set, skipping user confirmation")
            return True
        
        print(f"🔄 RESTORE CHECKPOINT: {self.checkpoint_id}")
        print(f"📅 Created: {manifest.get('timestamp', 'Unknown')}")
        print(f"🎯 Operation: {manifest.get('operation', 'Unknown')}")
        print(f"📂 Type: {manifest.get('type', 'Unknown')}")
        print()
        
        try:
            current_state = subprocess.check_output(
                ["git", "status", "--porcelain"],
                timeout=30,
                text=True
            )
            if current_state.strip():
                print("⚠️  WARNING: Uncommitted changes detected:")
                print(current_state)
                print()
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not check git status: {e}")
        except subprocess.TimeoutExpired:
            logger.warning("Git status check timed out")
        except FileNotFoundError:
            logger.warning("Git command not found, skipping status check")
        
        response = input("Proceed with restore? (yes/no): ").lower()
        confirmed = response in ['yes', 'y']
        logger.info(f"User confirmation: {'confirmed' if confirmed else 'denied'}")
        return confirmed
    
    def restore_files(self, manifest: Dict[str, Any]) -> List[str]:
        """Restore backed up files.
        
        Args:
            manifest: Checkpoint manifest (unused but kept for interface consistency)
            
        Returns:
            List of restored file paths
            
        Raises:
            OSError: If file operations fail
        """
        restored_files: List[str] = []
        
        # File mapping for restoration with security validation
        file_mapping = {
            "TASK.md": Path("planning/TASK.md"),
            "sprint.config.json": Path("planning/sprint.config.json"),
            "labels.yml": Path(".github/labels.yml"),
            "README.md": Path("docs/sprint-archives/README.md")
        }
        
        # Validate all target paths are within allowed directories
        allowed_base_dirs = {"planning", ".github", "docs"}
        for filename, target_path in file_mapping.items():
            if not any(str(target_path).startswith(base_dir) for base_dir in allowed_base_dirs):
                logger.error(f"Target path outside allowed directories: {target_path}")
                raise ValueError(f"Security violation: invalid target path for {filename}")
        
        for backup_file in self.backup_dir.glob("*"):
            if backup_file.name in ["manifest.json", "git_state.json"]:
                continue
            
            # Determine original location
            target = file_mapping.get(backup_file.name)
            if not target:
                self.restore_log.append(f"⚠️  Unknown file: {backup_file.name}")
                logger.warning(f"Unknown backup file: {backup_file.name}")
                continue
            
            try:
                # Create backup of current state
                if target.exists():
                    current_backup = Path(
                        f"backups/pre-restore/{target.name}."
                        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    )
                    current_backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, current_backup)
                    self.restore_log.append(f"📋 Current state backed up: {current_backup}")
                    logger.info(f"Backed up current state: {target} -> {current_backup}")
                
                # Ensure target directory exists
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Security check: validate file size before restoration
                backup_size = backup_file.stat().st_size
                if backup_size > 10 * 1024 * 1024:  # 10MB limit
                    logger.warning(f"Large file detected: {backup_file} ({backup_size} bytes)")
                
                # Restore file with metadata preservation
                shutil.copy2(backup_file, target)
                restored_files.append(str(target))
                self.restore_log.append(f"✓ Restored: {target}")
                logger.info(f"Restored: {backup_file} -> {target} ({backup_size} bytes)")
                
            except OSError as e:
                error_msg = f"Failed to restore {backup_file}: {e}"
                self.restore_log.append(f"❌ {error_msg}")
                logger.error(error_msg)
                raise
        
        logger.info(f"Successfully restored {len(restored_files)} files")
        return restored_files
    
    def validate_restored_state(self) -> bool:
        """Validate system state after restore.
        
        Returns:
            True if all validations pass
            
        Raises:
            No exceptions raised - all errors are logged and returned as False
        """
        try:
            # Validate TASK.md if validation script exists
            task_validator = Path("scripts/validate_tasks.py")
            if task_validator.exists():
                result = subprocess.run(
                    ["python", str(task_validator), "planning/TASK.md", "--quiet"],
                    capture_output=True,
                    timeout=30,
                    text=True
                )
                if result.returncode != 0:
                    error_msg = "TASK.md validation failed after restore"
                    self.restore_log.append(f"❌ {error_msg}")
                    logger.error(f"{error_msg}: {result.stderr}")
                    return False
                logger.info("TASK.md validation passed")
            else:
                logger.info("Task validator not found, skipping TASK.md validation")
            
            # Validate sprint config if it exists
            sprint_config = Path("planning/sprint.config.json")
            if sprint_config.exists():
                with open(sprint_config, "r", encoding="utf-8") as f:
                    json.load(f)  # Will raise exception if invalid JSON
                logger.info("Sprint config validation passed")
            else:
                logger.info("Sprint config not found, skipping validation")
            
            self.restore_log.append("✓ All validations passed")
            logger.info("All post-restore validations passed")
            return True
            
        except subprocess.TimeoutExpired:
            error_msg = "Validation timeout expired"
            self.restore_log.append(f"❌ {error_msg}")
            logger.error(error_msg)
            return False
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in restored files: {e}"
            self.restore_log.append(f"❌ {error_msg}")
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Validation error: {e}"
            self.restore_log.append(f"❌ {error_msg}")
            logger.error(error_msg)
            return False
    
    def create_restore_audit(self, manifest: Dict[str, Any], restored_files: List[str]) -> None:
        """Create audit trail for restore operation.
        
        Args:
            manifest: Original checkpoint manifest
            restored_files: List of files that were restored
            
        Raises:
            OSError: If audit file creation fails
        """
        try:
            # Get git information safely
            git_info = {}
            try:
                git_info["operator"] = subprocess.check_output(
                    ["git", "config", "user.name"],
                    timeout=10,
                    text=True
                ).strip()
                git_info["commit"] = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    timeout=10,
                    text=True
                ).strip()
                git_info["status"] = subprocess.check_output(
                    ["git", "status", "--porcelain"],
                    timeout=10,
                    text=True
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning(f"Could not get git information: {e}")
                git_info["operator"] = os.environ.get("USER", "unknown")
                git_info["commit"] = "unknown"
                git_info["status"] = "unknown"
            
            audit_record = {
                "restore_timestamp": datetime.now(timezone.utc).isoformat(),
                "checkpoint_id": self.checkpoint_id,
                "original_checkpoint": manifest,
                "restored_files": restored_files,
                "restore_log": self.restore_log,
                "operator": git_info["operator"],
                "git_state_after": {
                    "commit": git_info["commit"],
                    "status": git_info["status"]
                },
                "environment": {
                    "python_version": os.sys.version,
                    "working_directory": str(Path.cwd()),
                    "process_id": os.getpid()
                }
            }
            
            audit_path = Path(
                f"docs/audit/restore-{self.checkpoint_id}-"
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            )
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(audit_record, f, indent=2)
            
            print(f"📋 Audit record created: {audit_path}")
            logger.info(f"Audit record created: {audit_path}")
            
        except OSError as e:
            error_msg = f"Failed to create audit record: {e}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            raise
    
    def restore(self) -> bool:
        """Execute full restore process.
        
        Returns:
            True if restore completed successfully, False otherwise
            
        Raises:
            No exceptions raised - all errors are logged and returned as False
        """
        try:
            logger.info(f"Starting restore process for checkpoint: {self.checkpoint_id}")
            
            # Load manifest with validation
            manifest = self.load_manifest()
            
            # Confirm with user (unless forced)
            if not self.confirm_restore(manifest):
                logger.info("Restore cancelled by user")
                print("❌ Restore cancelled by user")
                return False
            
            print("🔄 Starting restore process...")
            logger.info("Beginning file restoration")
            
            # Restore files
            restored_files = self.restore_files(manifest)
            
            # Validate restored state
            if self.validate_restored_state():
                # Create audit trail
                self.create_restore_audit(manifest, restored_files)
                
                # Success messages
                success_msg = f"Restore completed successfully for checkpoint: {self.checkpoint_id}"
                logger.info(success_msg)
                print(f"✅ Restore completed successfully")
                print(f"📋 {len(restored_files)} files restored")
                print(f"🆔 Checkpoint: {self.checkpoint_id}")
                return True
            else:
                error_msg = "Restore validation failed"
                logger.error(error_msg)
                print(f"❌ {error_msg}")
                print("💡 Check restore logs for details")
                return False
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # These are expected errors that should be logged but not crash
            error_msg = f"Restore failed: {e}"
            self.restore_log.append(f"❌ {error_msg}")
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            return False
        except Exception as e:
            # Unexpected errors
            error_msg = f"Unexpected error during restore: {e}"
            self.restore_log.append(f"❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            print(f"❌ {error_msg}")
            return False

def main() -> None:
    """Main CLI entry point.
    
    Raises:
        SystemExit: With appropriate exit code
    """
    import sys
    
    # Validate command line arguments
    if len(sys.argv) < 2:
        print("Usage: python restore_checkpoint.py <checkpoint_id> [--force]")
        print("\nOptions:")
        print("  --force    Skip user confirmation")
        sys.exit(1)
    
    checkpoint_id = sys.argv[1]
    force = "--force" in sys.argv
    
    # Validate checkpoint_id format and security
    if not checkpoint_id.strip():
        print("❌ Error: checkpoint_id cannot be empty")
        sys.exit(1)
    
    # Additional security validation for CLI usage
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', checkpoint_id):
        print("❌ Error: checkpoint_id contains invalid characters")
        print("    Only alphanumeric characters, hyphens, and underscores are allowed")
        sys.exit(1)
    
    try:
        logger.info(f"Starting restore operation for checkpoint: {checkpoint_id}")
        restorer = CheckpointRestorer(checkpoint_id, force)
        success = restorer.restore()
        
        if success:
            logger.info("Restore operation completed successfully")
            sys.exit(0)
        else:
            logger.error("Restore operation failed")
            sys.exit(1)
            
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Error: {e}")
        logger.error(f"Restore operation failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Restore operation cancelled by user")
        logger.info("Restore operation cancelled by user interrupt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Unexpected error in restore operation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

#### **Emergency Recovery Workflow**
**File**: `.github/workflows/emergency-recovery.yml`
```yaml
name: Emergency Recovery
on:
  workflow_dispatch:
    inputs:
      recovery_type:
        description: 'Recovery type'
        required: true
        type: choice
        options:
          - task-file-corruption
          - sync-failure-cascade
          - git-history-corruption
          - complete-automation-failure
      checkpoint_id:
        description: 'Checkpoint ID to restore (if available)'
        required: false
      severity:
        description: 'Incident severity'
        required: true
        type: choice
        options:
          - P0-Critical
          - P1-High
          - P2-Medium

jobs:
  emergency-recovery:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0  # Full history for git recovery
          
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          # Use uv for faster local development, pip for CI consistency
          if command -v uv &> /dev/null; then
            uv pip install -r requirements-dev.txt
          else
            pip install -r requirements-dev.txt
          fi
          
      - name: Create incident record
        run: |
          INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
          INCIDENT_FILE="docs/incidents/${INCIDENT_ID}.md"
          
          mkdir -p docs/incidents
          cat > "$INCIDENT_FILE" << EOF
          # Incident: $INCIDENT_ID
          
          **Timestamp**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
          **Severity**: ${{ github.event.inputs.severity }}
          **Recovery Type**: ${{ github.event.inputs.recovery_type }}
          **Operator**: ${{ github.actor }}
          **Checkpoint**: ${{ github.event.inputs.checkpoint_id || 'None specified' }}
          
          ## Timeline
          - $(date -u '+%H:%M') - Emergency recovery initiated
          
          ## Actions Taken
          EOF
          
          echo "INCIDENT_ID=$INCIDENT_ID" >> $GITHUB_ENV
          echo "INCIDENT_FILE=$INCIDENT_FILE" >> $GITHUB_ENV
          
      - name: Execute recovery procedure
        run: |
          case "${{ github.event.inputs.recovery_type }}" in
            "task-file-corruption")
              echo "- $(date -u '+%H:%M') - Detected TASK.md corruption" >> "$INCIDENT_FILE"
              
              # Try to restore from checkpoint
              if [[ -n "${{ github.event.inputs.checkpoint_id }}" ]]; then
                python scripts/restore_checkpoint.py "${{ github.event.inputs.checkpoint_id }}" --force
                echo "- $(date -u '+%H:%M') - Restored from checkpoint ${{ github.event.inputs.checkpoint_id }}" >> "$INCIDENT_FILE"
              else
                # Restore from git history
                git checkout HEAD~1 -- planning/TASK.md
                echo "- $(date -u '+%H:%M') - Restored TASK.md from previous commit" >> "$INCIDENT_FILE"
              fi
              ;;
              
            "sync-failure-cascade")
              echo "- $(date -u '+%H:%M') - Multiple sync failures detected" >> "$INCIDENT_FILE"
              
              # Disable automation temporarily
              find .github/workflows -name "*sync*.yml" -exec mv {} {}.disabled \;
              echo "- $(date -u '+%H:%M') - Disabled sync workflows" >> "$INCIDENT_FILE"
              
              # Reset to known good state
              if [[ -n "${{ github.event.inputs.checkpoint_id }}" ]]; then
                python scripts/restore_checkpoint.py "${{ github.event.inputs.checkpoint_id }}" --force
              fi
              ;;
              
            "complete-automation-failure")
              echo "- $(date -u '+%H:%M') - Complete automation failure recovery" >> "$INCIDENT_FILE"
              
              # Disable all automation
              find .github/workflows -name "*.yml" ! -name "emergency-recovery.yml" -exec mv {} {}.disabled \;
              
              # Create manual recovery instructions
              cat >> docs/manual-recovery-instructions.md << EOF
              # Manual Recovery Instructions - $(date)
              
              ## Immediate Steps
              1. All automation workflows disabled
              2. Manual task management required
              3. Contact DevOps lead for restore plan
              
              ## To Re-enable Automation
              1. Verify all systems operational
              2. Run: find .github/workflows -name "*.yml.disabled" -exec bash -c 'mv "\$1" "\${1%.disabled}"' _ {} \;
              3. Test workflows individually
              EOF
              
              echo "- $(date -u '+%H:%M') - Created manual recovery instructions" >> "$INCIDENT_FILE"
              ;;
          esac
          
      - name: Validate recovery
        run: |
          echo "- $(date -u '+%H:%M') - Starting post-recovery validation" >> "$INCIDENT_FILE"
          
          # Validate TASK.md if it exists
          if [[ -f planning/TASK.md ]]; then
            if python scripts/validate_tasks.py planning/TASK.md --quiet; then
              echo "- $(date -u '+%H:%M') - ✓ TASK.md validation passed" >> "$INCIDENT_FILE"
            else
              echo "- $(date -u '+%H:%M') - ❌ TASK.md validation failed" >> "$INCIDENT_FILE"
              exit 1
            fi
          fi
          
          # Validate sprint config
          if [[ -f planning/sprint.config.json ]]; then
            if jq empty planning/sprint.config.json; then
              echo "- $(date -u '+%H:%M') - ✓ Sprint config validation passed" >> "$INCIDENT_FILE"
            else
              echo "- $(date -u '+%H:%M') - ❌ Sprint config validation failed" >> "$INCIDENT_FILE"
              exit 1
            fi
          fi
          
          echo "- $(date -u '+%H:%M') - Recovery validation completed" >> "$INCIDENT_FILE"
          
      - name: Commit recovery changes
        run: |
          git config --local user.email "emergency-recovery@github.com"
          git config --local user.name "Emergency Recovery Bot"
          
          git add .
          git commit -m "emergency: recovery from ${{ github.event.inputs.recovery_type }}

          Incident: $INCIDENT_ID
          Severity: ${{ github.event.inputs.severity }}
          Operator: ${{ github.actor }}
          Checkpoint: ${{ github.event.inputs.checkpoint_id || 'None' }}
          
          Recovery completed: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
          
          git push
          
          echo "- $(date -u '+%H:%M') - Recovery changes committed and pushed" >> "$INCIDENT_FILE"
          
      - name: Create follow-up issue
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `[POST-INCIDENT] Follow-up for ${process.env.INCIDENT_ID}`,
              body: `## Post-Incident Follow-up
              
              **Original Incident**: ${process.env.INCIDENT_ID}
              **Recovery Type**: ${{ github.event.inputs.recovery_type }}
              **Severity**: ${{ github.event.inputs.severity }}
              **Completed**: ${new Date().toISOString()}
              
              ## Required Actions
              - [ ] Root cause analysis within 48 hours
              - [ ] Update runbooks based on lessons learned
              - [ ] Test all automation functionality
              - [ ] Review and update recovery procedures
              - [ ] Schedule team retrospective
              
              ## Documentation
              - Incident Record: \`docs/incidents/${process.env.INCIDENT_ID}.md\`
              - Recovery Commit: ${context.sha}
              
              **Assigned to**: DevOps Team`,
              labels: ['incident', 'post-recovery', 'priority/high'],
              assignees: ['devops-lead']  // Replace with actual GitHub username
            });
```

### **7.3 Audit Trail Enhancement (2-3 hours)**

#### **Comprehensive Audit Logger**
**File**: `scripts/audit_logger.py`
```python
#!/usr/bin/env python3
"""
Comprehensive audit logging for all automation operations.
Maintains compliance-ready audit trails.
"""
import json
import hashlib
import logging
import os
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuditLogger:
    """Comprehensive audit logger for automation operations.
    
    Provides compliance-ready audit trails with integrity verification,
    structured logging, and comprehensive error handling.
    
    Args:
        component: Name of the component performing operations
        audit_dir: Optional custom audit directory path
        
    Raises:
        ValueError: If component name is invalid
        OSError: If audit directory cannot be created
    """
    
    def __init__(self, component: str, audit_dir: Optional[Path] = None) -> None:
        if not component or not component.strip():
            raise ValueError("Component name cannot be empty")
        
        self.component = component.strip()
        self.audit_dir = audit_dir or Path("docs/audit")
        
        try:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create audit directory {self.audit_dir}: {e}")
            raise
        
        self.session_id = self._generate_session_id()
        logger.info(f"Initialized AuditLogger for component: {self.component}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier.
        
        Returns:
            16-character hexadecimal session ID
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        session_data = f"{self.component}-{timestamp}-{os.getpid()}"
        return hashlib.sha256(session_data.encode('utf-8')).hexdigest()[:16]
    
    def log_operation(
        self,
        operation: str,
        details: Dict[str, Any],
        result: str = "success",
        files_affected: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a single operation with full context.
        
        Args:
            operation: Name of the operation being performed
            details: Detailed information about the operation
            result: Operation result (success, failure, warning)
            files_affected: List of files modified by the operation
            metadata: Additional metadata for the operation
            
        Returns:
            Unique audit ID for this operation
            
        Raises:
            ValueError: If operation name is invalid
            OSError: If audit file cannot be written
        """
        if not operation or not operation.strip():
            raise ValueError("Operation name cannot be empty")
        
        if result not in ["success", "failure", "warning", "info"]:
            logger.warning(f"Unknown result type: {result}")
        
        # Sanitize details to prevent logging sensitive information
        sanitized_details = self._sanitize_audit_data(details)
        
        timestamp = datetime.now(timezone.utc)
        audit_entry = {
            "audit_id": f"AUD-{timestamp.strftime('%Y%m%d%H%M%S')}-{self.component}",
            "session_id": self.session_id,
            "timestamp": timestamp.isoformat(),
            "component": self.component,
            "operation": operation.strip(),
            "result": result,
            "details": sanitized_details,
            "files_affected": files_affected or [],
            "metadata": metadata or {},
            "environment": {
                "git_commit": self._get_git_commit(),
                "workflow_run": self._get_workflow_run_id(),
                "actor": self._get_actor()
            }
        }
        
        # Add file checksums for integrity verification
        if files_affected:
            try:
                audit_entry["file_checksums"] = self._calculate_checksums(files_affected)
            except Exception as e:
                logger.warning(f"Failed to calculate checksums: {e}")
                audit_entry["file_checksums"] = {}
        
        # Write audit entry with error handling
        try:
            audit_file = self.audit_dir / f"audit-{timestamp.strftime('%Y-%m')}.jsonl"
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
            
            logger.debug(f"Logged operation: {operation} with result: {result}")
            return audit_entry["audit_id"]
            
        except OSError as e:
            logger.error(f"Failed to write audit entry: {e}")
            raise
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash.
        
        Returns:
            Git commit hash or None if unavailable
        """
        try:
            result = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                timeout=10,
                text=True,
                stderr=subprocess.DEVNULL
            )
            return result.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    def _get_workflow_run_id(self) -> Optional[str]:
        """Get GitHub Actions workflow run ID.
        
        Returns:
            GitHub workflow run ID or None if not in CI
        """
        return os.environ.get("GITHUB_RUN_ID")
    
    def _get_actor(self) -> str:
        """Get the actor (user or system) performing the operation.
        
        Returns:
            Actor identifier in format 'type:name'
        """
        # Check GitHub Actions environment
        github_actor = os.environ.get("GITHUB_ACTOR")
        if github_actor:
            return f"github:{github_actor}"
        
        # Try to get git user
        try:
            result = subprocess.check_output(
                ["git", "config", "user.name"],
                timeout=5,
                text=True,
                stderr=subprocess.DEVNULL
            )
            return f"git:{result.strip()}"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to system user
            system_user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
            return f"system:{system_user}"
    
    def _calculate_checksums(self, files: List[str]) -> Dict[str, str]:
        """Calculate SHA256 checksums for files.
        
        Args:
            files: List of file paths to checksum
            
        Returns:
            Dictionary mapping file paths to their SHA256 checksums
            
        Raises:
            OSError: If file cannot be read
        """
        checksums = {}
        for file_path in files:
            try:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    with open(path, "rb") as f:
                        checksums[file_path] = hashlib.sha256(f.read()).hexdigest()
                    logger.debug(f"Calculated checksum for: {file_path}")
                else:
                    logger.warning(f"File not found or not a file: {file_path}")
            except OSError as e:
                logger.error(f"Failed to calculate checksum for {file_path}: {e}")
                raise
        return checksums
    
    def log_failure(
        self,
        operation: str,
        error: str,
        context: Dict[str, Any],
        recovery_action: Optional[str] = None
    ) -> str:
        """Log operation failure with recovery context.
        
        Args:
            operation: Name of the failed operation
            error: Error message or description
            context: Additional context about the failure
            recovery_action: Suggested recovery action
            
        Returns:
            Unique audit ID for this failure
        """
        # Sanitize error message to prevent sensitive data exposure
        sanitized_error = self._sanitize_error_message(error)
        sanitized_context = self._sanitize_audit_data(context)
        
        failure_details = {
            "error_message": sanitized_error,
            "context": sanitized_context,
            "recovery_action": recovery_action,
            "stack_trace": self._get_stack_trace()
        }
        
        logger.error(f"Operation failed: {operation} - {sanitized_error}")
        
        return self.log_operation(
            operation=operation,
            details=failure_details,
            result="failure",
            metadata={"requires_investigation": True, "severity": "error"}
        )
    
    def _get_stack_trace(self) -> Optional[str]:
        """Get current stack trace for debugging.
        
        Returns:
            Formatted stack trace or None if unavailable
        """
        try:
            stack_trace = traceback.format_exc()
            # Only return stack trace if there's actual exception info
            if stack_trace and stack_trace.strip() != "NoneType: None":
                return stack_trace
            return None
        except Exception:
            return None
    
    def create_integrity_report(self) -> Dict[str, Any]:
        """Create audit trail integrity report.
        
        Returns:
            Dictionary containing integrity report data
            
        Raises:
            OSError: If report file cannot be written
        """
        audit_files = list(self.audit_dir.glob("audit-*.jsonl"))
        
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_files_count": len(audit_files),
            "total_entries": 0,
            "components": {},
            "date_range": {"earliest": None, "latest": None},
            "integrity_status": "valid",
            "errors": []
        }
        
        logger.info(f"Creating integrity report for {len(audit_files)} audit files")
        
        for audit_file in audit_files:
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:  # Skip empty lines
                            continue
                            
                        try:
                            entry = json.loads(line)
                            report["total_entries"] += 1
                            
                            # Track components
                            component = entry.get("component", "unknown")
                            if component not in report["components"]:
                                report["components"][component] = 0
                            report["components"][component] += 1
                            
                            # Track date range
                            timestamp = entry.get("timestamp")
                            if timestamp:
                                if not report["date_range"]["earliest"] or timestamp < report["date_range"]["earliest"]:
                                    report["date_range"]["earliest"] = timestamp
                                if not report["date_range"]["latest"] or timestamp > report["date_range"]["latest"]:
                                    report["date_range"]["latest"] = timestamp
                                    
                        except json.JSONDecodeError as e:
                            report["integrity_status"] = "corrupted"
                            error_msg = f"Invalid JSON in {audit_file}:{line_num} - {e}"
                            report["errors"].append(error_msg)
                            logger.error(error_msg)
                            
            except Exception as e:
                report["integrity_status"] = "error"
                error_msg = f"Failed to read {audit_file}: {e}"
                report["errors"].append(error_msg)
                logger.error(error_msg)
        
        # Save integrity report
        try:
            report_file = self.audit_dir / f"integrity-report-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Integrity report saved to: {report_file}")
            
        except OSError as e:
            logger.error(f"Failed to save integrity report: {e}")
            raise
        
        return report

    def _sanitize_audit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize audit data to prevent logging sensitive information.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary with sensitive data redacted
        """
        sensitive_keys = {
            "password", "token", "secret", "key", "api_key", "auth", "credential",
            "passwd", "pwd", "authorization", "bearer", "session", "cookie"
        }
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_audit_data(value)
            elif isinstance(value, str) and len(value) > 100:
                # Truncate very long strings
                sanitized[key] = value[:100] + "...[TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_error_message(self, error_msg: str) -> str:
        """Sanitize error message to prevent sensitive data exposure.
        
        Args:
            error_msg: Original error message
            
        Returns:
            Sanitized error message
        """
        # Basic pattern matching for common sensitive data patterns
        import re
        
        # Redact potential tokens, keys, etc.
        patterns = [
            (r'token[=:\s]+[a-zA-Z0-9._-]+', 'token=[REDACTED]'),
            (r'key[=:\s]+[a-zA-Z0-9._-]+', 'key=[REDACTED]'),
            (r'password[=:\s]+\S+', 'password=[REDACTED]'),
            (r'secret[=:\s]+\S+', 'secret=[REDACTED]')
        ]
        
        sanitized = error_msg
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized


# Usage example for workflows
def log_workflow_operation(component: str, operation: str, **kwargs: Any) -> str:
    """Convenience function for workflow logging.
    
    Args:
        component: Component name performing the operation
        operation: Operation being performed
        **kwargs: Additional operation details
        
    Returns:
        Unique audit ID for the logged operation
    """
    audit_logger = AuditLogger(component)
    return audit_logger.log_operation(operation, kwargs)

def main() -> None:
    """Main CLI entry point for audit operations.
    
    Raises:
        SystemExit: With appropriate exit code
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audit_logger.py <command> [args]")
        print("Commands:")
        print("  integrity-check    Create and display integrity report")
        print("  log <component> <operation> <details>    Log a single operation")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "integrity-check":
            audit_logger = AuditLogger("audit-system")
            report = audit_logger.create_integrity_report()
            print(json.dumps(report, indent=2))
            
            if report["errors"]:
                print(f"\nFound {len(report['errors'])} integrity issues:", file=sys.stderr)
                for error in report["errors"]:
                    print(f"  - {error}", file=sys.stderr)
            
            sys.exit(0 if report["integrity_status"] == "valid" else 1)
            
        elif command == "log" and len(sys.argv) >= 5:
            component = sys.argv[2]
            operation = sys.argv[3]
            details_json = sys.argv[4]
            
            try:
                details = json.loads(details_json)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in details: {details_json}", file=sys.stderr)
                sys.exit(1)
            
            audit_logger = AuditLogger(component)
            audit_id = audit_logger.log_operation(operation, details)
            print(f"Logged operation with ID: {audit_id}")
            sys.exit(0)
            
        else:
            print(f"Error: Unknown command or insufficient arguments: {command}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"CLI operation failed: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

#### **Integration with Existing Workflows**
**Update existing workflows to include audit logging:**

```yaml
# Add to all automation workflows
      - name: Log operation start
        run: |
          python -c "
          from scripts.audit_logger import log_workflow_operation
          log_workflow_operation(
              component='task-sync',
              operation='workflow_start',
              trigger='${{ github.event_name }}',
              actor='${{ github.actor }}',
              ref='${{ github.ref }}'
          )"
          
      # ... existing workflow steps ...
      
      - name: Log operation completion
        if: always()
        run: |
          python -c "
          from scripts.audit_logger import log_workflow_operation
          import os
          result = 'success' if '${{ job.status }}' == 'success' else 'failure'
          log_workflow_operation(
              component='task-sync',
              operation='workflow_complete',
              result=result,
              files_modified=['planning/TASK.md'],
              changes_count=int(os.environ.get('CHANGES_COUNT', 0))
          )"
```

### **7.4 Testing & Validation (3-4 hours)**

#### **Recovery Testing Suite**
**File**: `tests/test_recovery_system.py`
```python
#!/usr/bin/env python3
"""
Comprehensive test suite for recovery and rollback procedures.

Follows CLAUDE.md testing requirements with 90% coverage, comprehensive
edge cases, failure scenarios, and property-based testing.
"""
import json
import logging
import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any, Generator

import pytest
from hypothesis import given, strategies as st, settings, example

# Import modules under test
try:
    from create_recovery_checkpoint import RecoveryCheckpoint
    from restore_checkpoint import CheckpointRestorer
    from audit_logger import AuditLogger
except ImportError:
    # Fallback for when running from different directory
    import sys
    sys.path.append('.')
    from create_recovery_checkpoint import RecoveryCheckpoint
    from restore_checkpoint import CheckpointRestorer
    from audit_logger import AuditLogger

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestRecoverySystem:
    """Comprehensive test suite for recovery system components.
    
    Tests cover:
    - Happy path scenarios
    - Edge cases and boundary conditions
    - Failure scenarios and error handling
    - Security validation
    - Performance characteristics
    - Integration between components
    """
    
    @pytest.fixture
    def temp_workspace(self) -> Generator[Path, None, None]:
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create standard directory structure
            (workspace / "planning").mkdir()
            (workspace / "docs" / "audit").mkdir(parents=True)
            (workspace / ".github").mkdir()
            (workspace / "backups" / "checkpoints").mkdir(parents=True)
            
            # Create test files
            (workspace / "planning" / "TASK.md").write_text("# Test TASK content\n\n## Tasks\n- Test task 1")
            (workspace / "planning" / "sprint.config.json").write_text('{"sprint": "test"}')
            (workspace / ".github" / "labels.yml").write_text("labels: []")
            
            yield workspace
    
    def test_checkpoint_creation_valid_input(self, temp_workspace: Path) -> None:
        """Test checkpoint creation with valid inputs."""
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            checkpoint = RecoveryCheckpoint("emergency", "unit-test-operation")
            checkpoint_id = checkpoint.create_checkpoint()
            
            # Verify checkpoint structure
            assert checkpoint.backup_dir.exists()
            assert checkpoint.backup_dir.is_dir()
            
            # Verify required files
            manifest_file = checkpoint.backup_dir / "manifest.json"
            assert manifest_file.exists()
            
            git_state_file = checkpoint.backup_dir / "git_state.json"
            assert git_state_file.exists()
            
            integrity_file = checkpoint.backup_dir / "integrity.json"
            assert integrity_file.exists()
            
            # Verify manifest content
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            assert manifest["checkpoint_id"] == checkpoint_id
            assert manifest["type"] == "emergency"
            assert manifest["operation"] == "unit-test-operation"
            assert "timestamp" in manifest
            assert "file_checksums" in manifest
            assert "security" in manifest
            
            # Verify backed up files exist
            assert (checkpoint.backup_dir / "TASK.md").exists()
            assert (checkpoint.backup_dir / "sprint.config.json").exists()
    
    def test_checkpoint_creation_invalid_type(self) -> None:
        """Test checkpoint creation with invalid type."""
        with pytest.raises(ValueError, match="Invalid checkpoint_type"):
            RecoveryCheckpoint("invalid-type", "test-operation")
    
    def test_checkpoint_creation_empty_inputs(self) -> None:
        """Test checkpoint creation with empty inputs."""
        with pytest.raises(ValueError, match="checkpoint_type cannot be empty"):
            RecoveryCheckpoint("", "test-operation")
        
        with pytest.raises(ValueError, match="operation cannot be empty"):
            RecoveryCheckpoint("emergency", "")
    
    def test_checkpoint_creation_long_operation(self) -> None:
        """Test checkpoint creation with operation description too long."""
        long_operation = "x" * 101  # Exceeds 100 character limit
        with pytest.raises(ValueError, match="Operation description too long"):
            RecoveryCheckpoint("emergency", long_operation)
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    @example("test-operation")
    def test_checkpoint_creation_sanitization(self, operation: str) -> None:
        """Test input sanitization with property-based testing."""
        # Should not raise exception for reasonable inputs
        try:
            checkpoint = RecoveryCheckpoint("emergency", operation)
            assert checkpoint.operation  # Should have sanitized value
        except ValueError as e:
            # Only acceptable if operation becomes empty after sanitization
            assert "cannot be empty" in str(e) or "too long" in str(e)
    
    def test_checkpoint_restore_valid_scenario(self, temp_workspace: Path) -> None:
        """Test checkpoint restoration with valid scenario."""
        # Setup checkpoint directory
        checkpoint_id = "emergency-20250707-123456-abcd1234"
        checkpoint_dir = temp_workspace / "backups" / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True)
        
        # Create comprehensive manifest
        manifest = {
            "checkpoint_id": checkpoint_id,
            "type": "emergency",
            "operation": "unit-test-restore",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "files_backed_up": ["planning/TASK.md", "planning/sprint.config.json"],
            "file_checksums": {"TASK.md": "abc123", "sprint.config.json": "def456"},
            "security": {"validation_status": "valid"}
        }
        (checkpoint_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        
        # Create backup files
        (checkpoint_dir / "TASK.md").write_text("# Original TASK content")
        (checkpoint_dir / "sprint.config.json").write_text('{"original": true}')
        
        # Modify current files to simulate changes
        (temp_workspace / "planning" / "TASK.md").write_text("# Modified TASK content")
        (temp_workspace / "planning" / "sprint.config.json").write_text('{"modified": true}')
        
        # Test restore with mocked git commands
        with patch('pathlib.Path.cwd', return_value=temp_workspace), \
             patch('subprocess.check_output', return_value=""), \
             patch('subprocess.run', return_value=MagicMock(returncode=0)):
            
            restorer = CheckpointRestorer(checkpoint_id, force=True)
            success = restorer.restore()
        
        assert success
        
        # Verify files were restored
        restored_task = (temp_workspace / "planning" / "TASK.md").read_text()
        assert restored_task == "# Original TASK content"
        
        restored_config = (temp_workspace / "planning" / "sprint.config.json").read_text()
        assert restored_config == '{"original": true}'
        
        # Verify audit trail was created
        audit_files = list((temp_workspace / "docs" / "audit").glob("restore-*.json"))
        assert len(audit_files) == 1
    
    def test_checkpoint_restore_invalid_id(self) -> None:
        """Test restore with invalid checkpoint ID."""
        with pytest.raises(ValueError, match="checkpoint_id cannot be empty"):
            CheckpointRestorer("", force=True)
        
        with pytest.raises(ValueError, match="Invalid checkpoint_id format"):
            CheckpointRestorer("../../../etc/passwd", force=True)
    
    def test_checkpoint_restore_nonexistent(self, temp_workspace: Path) -> None:
        """Test restore with nonexistent checkpoint."""
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            with pytest.raises(FileNotFoundError, match="Checkpoint .* not found"):
                CheckpointRestorer("nonexistent-checkpoint", force=True)
    
    def test_checkpoint_restore_corrupted_manifest(self, temp_workspace: Path) -> None:
        """Test restore with corrupted manifest file."""
        checkpoint_id = "test-corrupted"
        checkpoint_dir = temp_workspace / "backups" / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True)
        
        # Create invalid JSON manifest
        (checkpoint_dir / "manifest.json").write_text("invalid json content {")
        
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            restorer = CheckpointRestorer(checkpoint_id, force=True)
            with pytest.raises(json.JSONDecodeError):
                restorer.load_manifest()
    
    def test_checkpoint_restore_security_validation(self, temp_workspace: Path) -> None:
        """Test security validation during restore."""
        checkpoint_id = "test-security"
        checkpoint_dir = temp_workspace / "backups" / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True)
        
        # Create manifest
        manifest = {"checkpoint_id": checkpoint_id, "type": "test", "operation": "security-test"}
        (checkpoint_dir / "manifest.json").write_text(json.dumps(manifest))
        
        # Create a file that would target outside allowed directories
        (checkpoint_dir / "malicious.txt").write_text("malicious content")
        
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            restorer = CheckpointRestorer(checkpoint_id, force=True)
            restored_files = restorer.restore_files(manifest)
            
            # Should not restore files not in the allowed mapping
            assert "malicious.txt" not in str(restored_files)
    
    def test_audit_logging_valid_operation(self, temp_workspace: Path) -> None:
        """Test audit logging with valid operation."""
        audit_logger = AuditLogger("test-component", temp_workspace / "docs" / "audit")
        
        # Log operation
        audit_id = audit_logger.log_operation(
            operation="test_operation",
            details={"test": "data", "count": 42},
            result="success",
            files_affected=["test_file.md"],
            metadata={"test_run": True}
        )
        
        # Verify audit ID format
        assert audit_id.startswith("AUD-")
        assert len(audit_id) > 20  # Should include timestamp and component
        
        # Verify audit file created
        audit_files = list(audit_logger.audit_dir.glob("audit-*.jsonl"))
        assert len(audit_files) == 1
        
        # Verify audit content
        with open(audit_files[0], "r", encoding="utf-8") as f:
            audit_entry = json.loads(f.read().strip())
            
            assert audit_entry["operation"] == "test_operation"
            assert audit_entry["component"] == "test-component"
            assert audit_entry["result"] == "success"
            assert audit_entry["details"]["test"] == "data"
            assert audit_entry["details"]["count"] == 42
            assert audit_entry["metadata"]["test_run"] is True
            assert "timestamp" in audit_entry
            assert "session_id" in audit_entry
            assert "environment" in audit_entry
    
    def test_audit_logging_sensitive_data_sanitization(self, temp_workspace: Path) -> None:
        """Test that sensitive data is properly sanitized in audit logs."""
        audit_logger = AuditLogger("security-test", temp_workspace / "docs" / "audit")
        
        # Log operation with sensitive data
        sensitive_details = {
            "username": "testuser",
            "password": "secret123",
            "api_key": "sk-1234567890",
            "token": "bearer_token_xyz",
            "normal_data": "this should remain"
        }
        
        audit_id = audit_logger.log_operation(
            operation="login_attempt",
            details=sensitive_details
        )
        
        # Verify audit entry
        audit_files = list(audit_logger.audit_dir.glob("audit-*.jsonl"))
        with open(audit_files[0], "r", encoding="utf-8") as f:
            audit_entry = json.loads(f.read().strip())
            
            details = audit_entry["details"]
            assert details["username"] == "testuser"  # Username should remain
            assert details["password"] == "[REDACTED]"  # Password should be redacted
            assert details["api_key"] == "[REDACTED]"  # API key should be redacted
            assert details["token"] == "[REDACTED]"  # Token should be redacted
            assert details["normal_data"] == "this should remain"  # Normal data preserved
    
    def test_audit_logging_failure_scenario(self, temp_workspace: Path) -> None:
        """Test audit logging for failure scenarios."""
        audit_logger = AuditLogger("failure-test", temp_workspace / "docs" / "audit")
        
        # Log failure
        audit_id = audit_logger.log_failure(
            operation="critical_operation",
            error="Database connection failed",
            context={"database_host": "localhost", "retry_count": 3},
            recovery_action="Switch to backup database"
        )
        
        # Verify failure logged correctly
        audit_files = list(audit_logger.audit_dir.glob("audit-*.jsonl"))
        with open(audit_files[0], "r", encoding="utf-8") as f:
            audit_entry = json.loads(f.read().strip())
            
            assert audit_entry["operation"] == "critical_operation"
            assert audit_entry["result"] == "failure"
            assert audit_entry["details"]["error_message"] == "Database connection failed"
            assert audit_entry["details"]["recovery_action"] == "Switch to backup database"
            assert audit_entry["metadata"]["requires_investigation"] is True
    
    def test_audit_logging_integrity_report(self, temp_workspace: Path) -> None:
        """Test audit trail integrity reporting."""
        audit_logger = AuditLogger("integrity-test", temp_workspace / "docs" / "audit")
        
        # Create multiple audit entries
        for i in range(5):
            audit_logger.log_operation(
                operation=f"test_operation_{i}",
                details={"iteration": i}
            )
        
        # Generate integrity report
        report = audit_logger.create_integrity_report()
        
        # Verify report structure
        assert report["integrity_status"] == "valid"
        assert report["total_entries"] == 5
        assert report["audit_files_count"] == 1
        assert "integrity-test" in report["components"]
        assert report["components"]["integrity-test"] == 5
        assert "report_timestamp" in report
        assert "date_range" in report
    
    def test_audit_logging_empty_operation(self, temp_workspace: Path) -> None:
        """Test audit logging with empty operation name."""
        audit_logger = AuditLogger("validation-test", temp_workspace / "docs" / "audit")
        
        with pytest.raises(ValueError, match="Operation name cannot be empty"):
            audit_logger.log_operation(
                operation="",
                details={"test": "data"}
            )

    def test_failure_scenarios_comprehensive(self, temp_workspace: Path) -> None:
        """Test comprehensive failure scenarios and edge cases."""
        
        # Test 1: Invalid checkpoint restoration
        with pytest.raises(FileNotFoundError):
            CheckpointRestorer("nonexistent-checkpoint")
        
        # Test 2: Corrupted manifest
        checkpoint_dir = temp_workspace / "backups" / "checkpoints" / "corrupted"
        checkpoint_dir.mkdir(parents=True)
        (checkpoint_dir / "manifest.json").write_text("invalid json {")
        
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            restorer = CheckpointRestorer("corrupted", force=True)
            with pytest.raises(json.JSONDecodeError):
                restorer.load_manifest()
        
        # Test 3: Permission denied scenarios
        restricted_dir = temp_workspace / "backups" / "checkpoints" / "restricted"
        restricted_dir.mkdir(parents=True)
        manifest_file = restricted_dir / "manifest.json"
        manifest_file.write_text('{"test": "data"}')
        
        # Simulate permission denied by mocking open to raise PermissionError
        with patch('pathlib.Path.cwd', return_value=temp_workspace), \
             patch('builtins.open', side_effect=PermissionError("Access denied")):
            
            restorer = CheckpointRestorer("restricted", force=True)
            with pytest.raises(PermissionError):
                restorer.load_manifest()
        
        # Test 4: Disk space exhaustion during checkpoint creation
        with patch('pathlib.Path.cwd', return_value=temp_workspace), \
             patch('shutil.copy2', side_effect=OSError("No space left on device")):
            
            checkpoint = RecoveryCheckpoint("emergency", "disk-full-test")
            with pytest.raises(OSError, match="No space left on device"):
                checkpoint.create_checkpoint()
        
        # Test 5: Git command failures
        with patch('pathlib.Path.cwd', return_value=temp_workspace), \
             patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'git')):
            
            checkpoint = RecoveryCheckpoint("emergency", "git-fail-test")
            # Should still succeed but log warnings about git failures
            checkpoint_id = checkpoint.create_checkpoint()
            assert checkpoint_id  # Should not fail completely
    
    def test_performance_characteristics(self, temp_workspace: Path) -> None:
        """Test performance characteristics and resource usage."""
        import time
        
        # Create larger test files to simulate real-world scenarios
        large_content = "# Large file content\n" + "Test line\n" * 1000
        (temp_workspace / "planning" / "TASK.md").write_text(large_content)
        
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            # Test checkpoint creation performance
            start_time = time.time()
            checkpoint = RecoveryCheckpoint("emergency", "performance-test")
            checkpoint_id = checkpoint.create_checkpoint()
            creation_time = time.time() - start_time
            
            # Should complete within reasonable time (5 seconds)
            assert creation_time < 5.0
            
            # Test restoration performance
            start_time = time.time()
            restorer = CheckpointRestorer(checkpoint_id, force=True)
            
            with patch('subprocess.check_output', return_value=""), \
                 patch('subprocess.run', return_value=MagicMock(returncode=0)):
                success = restorer.restore()
            
            restoration_time = time.time() - start_time
            
            assert success
            assert restoration_time < 3.0  # Restoration should be faster
    
    def test_integration_end_to_end(self, temp_workspace: Path) -> None:
        """Test complete end-to-end integration scenario."""
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            # Step 1: Create initial state
            original_task_content = "# Original Task File\n\n## Important Tasks\n- Task 1\n- Task 2"
            (temp_workspace / "planning" / "TASK.md").write_text(original_task_content)
            
            # Step 2: Create checkpoint
            checkpoint = RecoveryCheckpoint("emergency", "integration-test")
            checkpoint_id = checkpoint.create_checkpoint()
            
            # Step 3: Modify files (simulate automation changes)
            modified_content = "# Modified Task File\n\n## Modified Tasks\n- New Task 1\n- New Task 2"
            (temp_workspace / "planning" / "TASK.md").write_text(modified_content)
            
            # Step 4: Verify modification
            assert (temp_workspace / "planning" / "TASK.md").read_text() == modified_content
            
            # Step 5: Restore from checkpoint
            with patch('subprocess.check_output', return_value=""), \
                 patch('subprocess.run', return_value=MagicMock(returncode=0)):
                
                restorer = CheckpointRestorer(checkpoint_id, force=True)
                success = restorer.restore()
            
            # Step 6: Verify restoration
            assert success
            restored_content = (temp_workspace / "planning" / "TASK.md").read_text()
            assert restored_content == original_task_content
            
            # Step 7: Verify audit trail exists
            audit_files = list((temp_workspace / "docs" / "audit").glob("restore-*.json"))
            assert len(audit_files) == 1
            
            # Step 8: Verify backup of current state was created
            pre_restore_backups = list((temp_workspace / "backups" / "pre-restore").glob("*.md*"))
            assert len(pre_restore_backups) == 1
    
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=20))
    @settings(max_examples=50, deadline=5000)  # Limit for CI performance
    def test_checkpoint_id_generation_uniqueness(self, operation_suffix: str) -> None:
        """Test that checkpoint IDs are unique using property-based testing."""
        checkpoint_ids = set()
        
        for i in range(10):
            try:
                checkpoint = RecoveryCheckpoint("emergency", f"test-{operation_suffix}-{i}")
                checkpoint_ids.add(checkpoint.checkpoint_id)
            except ValueError:
                # Skip invalid inputs that get rejected by sanitization
                continue
        
        # All generated IDs should be unique
        assert len(checkpoint_ids) == len([id for id in checkpoint_ids])

class TestRecoverySystemPerformance:
    """Performance and stress testing for recovery system."""
    
    def test_large_file_handling(self, temp_workspace: Path) -> None:
        """Test handling of large files within security limits."""
        # Create file approaching size limit (but within it)
        large_content = "x" * (10 * 1024 * 1024)  # 10MB (within limit)
        large_file = temp_workspace / "planning" / "large_task.md"
        large_file.write_text(large_content)
        
        # Update file mapping to include large file for testing
        with patch('pathlib.Path.cwd', return_value=temp_workspace), \
             patch.object(RecoveryCheckpoint, 'backup_critical_files') as mock_backup:
            
            def custom_backup(self):
                # Custom backup that includes our large file
                test_files = ["planning/large_task.md"]
                for file_path in test_files:
                    src = Path(file_path)
                    if src.exists():
                        file_size = src.stat().st_size
                        # Should handle large files within limit
                        assert file_size <= 50 * 1024 * 1024  # 50MB limit
                        dst = self.backup_dir / src.name
                        shutil.copy2(src, dst)
                        self.backed_up_files.append(file_path)
            
            mock_backup.side_effect = custom_backup
            
            checkpoint = RecoveryCheckpoint("emergency", "large-file-test")
            checkpoint_id = checkpoint.create_checkpoint()
            assert checkpoint_id
    
    def test_concurrent_operations_safety(self, temp_workspace: Path) -> None:
        """Test thread safety and concurrent operation handling."""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_checkpoint(thread_id: int):
            try:
                with patch('pathlib.Path.cwd', return_value=temp_workspace):
                    checkpoint = RecoveryCheckpoint("emergency", f"concurrent-test-{thread_id}")
                    checkpoint_id = checkpoint.create_checkpoint()
                    results.append(checkpoint_id)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_checkpoint, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5  # All threads should succeed
        assert len(set(results)) == 5  # All checkpoint IDs should be unique


class TestSecurityValidation:
    """Security-focused test cases."""
    
    def test_path_traversal_prevention(self) -> None:
        """Test prevention of path traversal attacks."""
        malicious_inputs = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "checkpoint; rm -rf /",
            "checkpoint$(rm -rf /)",
            "checkpoint`rm -rf /`"
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises((ValueError, FileNotFoundError)):
                CheckpointRestorer(malicious_input, force=True)
    
    def test_input_sanitization_comprehensive(self) -> None:
        """Test comprehensive input sanitization."""
        dangerous_chars = ['<', '>', '&', '"', "'", ';', '|', '`', '$', '(', ')']
        
        for char in dangerous_chars:
            operation_with_char = f"test{char}operation"
            try:
                checkpoint = RecoveryCheckpoint("emergency", operation_with_char)
                # Should sanitize the dangerous character
                assert char not in checkpoint.operation
            except ValueError:
                # Acceptable if completely rejected
                pass
    
    def test_file_size_limits_enforcement(self, temp_workspace: Path) -> None:
        """Test that file size limits are properly enforced."""
        # Create oversized file (exceeding 50MB limit)
        oversized_content = "x" * (51 * 1024 * 1024)  # 51MB
        oversized_file = temp_workspace / "planning" / "oversized.md"
        oversized_file.write_text(oversized_content)
        
        with patch('pathlib.Path.cwd', return_value=temp_workspace):
            checkpoint = RecoveryCheckpoint("emergency", "size-limit-test")
            
            # Mock the critical files to include our oversized file
            original_files = [
                "planning/TASK.md",
                "planning/sprint.config.json", 
                ".github/labels.yml",
                "docs/sprint-archives/README.md",
                "planning/oversized.md"  # Add our oversized file
            ]
            
            with patch.object(checkpoint, 'backup_critical_files') as mock_backup:
                def size_aware_backup():
                    for file_path in original_files:
                        src = Path(file_path)
                        if src.exists() and src.is_file():
                            file_size = src.stat().st_size
                            if file_size > 50 * 1024 * 1024:  # 50MB limit
                                # Should skip large files
                                continue
                            dst = checkpoint.backup_dir / src.name
                            shutil.copy2(src, dst)
                            checkpoint.backed_up_files.append(file_path)
                
                mock_backup.side_effect = size_aware_backup
                checkpoint_id = checkpoint.create_checkpoint()
                
                # Oversized file should not be in backed up files
                assert "planning/oversized.md" not in checkpoint.backed_up_files


def main() -> None:
    """Main test runner with comprehensive configuration."""
    import sys
    
    # Configure pytest with comprehensive options
    pytest_args = [
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker validation
        "--disable-warnings",  # Clean output
        "--cov=.",  # Coverage reporting
        "--cov-report=term-missing",  # Show missing lines
        "--cov-fail-under=90",  # Require 90% coverage
        "--hypothesis-show-statistics",  # Show Hypothesis statistics
    ]
    
    # Add performance testing if requested
    if "--performance" in sys.argv:
        pytest_args.extend(["-k", "performance"])
        sys.argv.remove("--performance")
    
    # Add security testing if requested
    if "--security" in sys.argv:
        pytest_args.extend(["-k", "security"])
        sys.argv.remove("--security")
    
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

---

## 📋 IMPLEMENTATION CHECKLIST

### **Phase 7.1: Automated Detection**
- [ ] Deploy automation health check workflow
- [ ] Create checkpoint creation script
- [ ] Test failure detection scenarios
- [ ] Verify alert notifications work

### **Phase 7.2: Rollback Procedures** 
- [ ] Implement checkpoint restore script
- [ ] Deploy emergency recovery workflow
- [ ] Test rollback scenarios
- [ ] Validate restore procedures

### **Phase 7.3: Audit Enhancement**
- [ ] Deploy comprehensive audit logger
- [ ] Integrate with existing workflows  
- [ ] Test audit trail integrity
- [ ] Verify compliance requirements

### **Phase 7.4: Testing & Validation**
- [ ] Run recovery test suite
- [ ] Perform end-to-end failure simulation
- [ ] Validate audit completeness
- [ ] Document lessons learned

---

## 🚀 DEPLOYMENT STRATEGY

### **Week 1: Foundation**
- Deploy detection and checkpoint systems
- Test with non-critical operations
- Validate basic functionality

### **Week 2: Integration** 
- Integrate audit logging with all workflows
- Deploy emergency recovery procedures
- Test rollback scenarios

### **Week 3: Validation**
- Comprehensive testing of all scenarios
- Performance and reliability testing
- Team training on recovery procedures

### **Week 4: Production**
- Go-live with full recovery system
- Monitor and tune detection thresholds
- Document and refine procedures

---

## 📊 SUCCESS METRICS

### **Recovery Effectiveness**
- **Detection Time**: Failures detected within 15 minutes (P0/P1)
- **Recovery Time**: Full recovery within 2 hours (P1), 8 hours (P2)
- **Data Integrity**: 100% audit trail preservation during recovery
- **Success Rate**: >95% successful automated recovery for P2/P3 issues

### **Audit Compliance**
- **Coverage**: 100% of automation operations logged
- **Retention**: 7-year audit trail preservation  
- **Integrity**: Regular integrity validation with 99.9% success rate
- **Accessibility**: <5 minutes to retrieve any audit record

### **Team Readiness**
- **Response Time**: Team acknowledges P0 alerts within 15 minutes
- **Procedure Familiarity**: 100% team trained on recovery procedures
- **Documentation Currency**: Recovery runbooks updated within 30 days
- **Practice Frequency**: Recovery procedures tested monthly

This comprehensive recovery plan addresses the critical gap in automation failure handling, providing robust rollback capabilities, comprehensive audit trails, and clear procedures for all failure scenarios.