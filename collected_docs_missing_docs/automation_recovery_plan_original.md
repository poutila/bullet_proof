# 🛡️ AUTOMATION RECOVERY & FAILURE HANDLING PLAN

> **Critical Gap Resolution**: Comprehensive failure handling, rollback procedures, and audit trail management for task automation system failures.

**Document Version**: v1.0.0  
**Last Updated**: 2025-07-06  
**Owner**: DevOps Lead  
**Review Cycle**: Monthly  

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
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class RecoveryCheckpoint:
    def __init__(self, checkpoint_type: str, operation: str):
        self.checkpoint_type = checkpoint_type
        self.operation = operation
        self.timestamp = datetime.now().isoformat()
        self.checkpoint_id = f"{checkpoint_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.backup_dir = Path(f"backups/checkpoints/{self.checkpoint_id}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_critical_files(self) -> None:
        """Backup files that automation might modify."""
        critical_files = [
            "planning/TASK.md",
            "planning/sprint.config.json", 
            ".github/labels.yml",
            "docs/sprint-archives/README.md"
        ]
        
        for file_path in critical_files:
            src = Path(file_path)
            if src.exists():
                dst = self.backup_dir / src.name
                shutil.copy2(src, dst)
                print(f"✓ Backed up: {file_path}")
    
    def backup_git_state(self) -> None:
        """Capture current git state for reference."""
        import subprocess
        
        git_info = {
            "commit_hash": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
            "branch": subprocess.check_output(["git", "branch", "--show-current"]).decode().strip(),
            "status": subprocess.check_output(["git", "status", "--porcelain"]).decode(),
            "last_commits": subprocess.check_output(["git", "log", "--oneline", "-5"]).decode()
        }
        
        with open(self.backup_dir / "git_state.json", "w") as f:
            json.dump(git_info, f, indent=2)
    
    def create_checkpoint(self) -> str:
        """Create complete checkpoint."""
        self.backup_critical_files()
        self.backup_git_state()
        
        # Create checkpoint manifest
        manifest = {
            "checkpoint_id": self.checkpoint_id,
            "type": self.checkpoint_type,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "files_backed_up": list(self.backup_dir.glob("*")),
            "recovery_instructions": f"To restore: python scripts/restore_checkpoint.py {self.checkpoint_id}"
        }
        
        with open(self.backup_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ Checkpoint created: {self.checkpoint_id}")
        return self.checkpoint_id

# CLI interface
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python create_recovery_checkpoint.py <type> <operation>")
        print("Types: sprint-archive, task-sync, emergency")
        sys.exit(1)
    
    checkpoint = RecoveryCheckpoint(sys.argv[1], sys.argv[2])
    checkpoint_id = checkpoint.create_checkpoint()
    print(f"Checkpoint ID: {checkpoint_id}")
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
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class CheckpointRestorer:
    def __init__(self, checkpoint_id: str, force: bool = False):
        self.checkpoint_id = checkpoint_id
        self.force = force
        self.backup_dir = Path(f"backups/checkpoints/{checkpoint_id}")
        self.restore_log = []
        
        if not self.backup_dir.exists():
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")
    
    def load_manifest(self) -> Dict:
        """Load checkpoint manifest."""
        manifest_path = self.backup_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("Checkpoint manifest not found")
        
        with open(manifest_path, "r") as f:
            return json.load(f)
    
    def confirm_restore(self, manifest: Dict) -> bool:
        """Confirm restore operation with user."""
        if self.force:
            return True
        
        print(f"🔄 RESTORE CHECKPOINT: {self.checkpoint_id}")
        print(f"📅 Created: {manifest['timestamp']}")
        print(f"🎯 Operation: {manifest['operation']}")
        print(f"📂 Type: {manifest['type']}")
        print()
        
        current_state = subprocess.check_output(["git", "status", "--porcelain"]).decode()
        if current_state.strip():
            print("⚠️  WARNING: Uncommitted changes detected:")
            print(current_state)
            print()
        
        response = input("Proceed with restore? (yes/no): ").lower()
        return response in ['yes', 'y']
    
    def restore_files(self, manifest: Dict) -> None:
        """Restore backed up files."""
        restored_files = []
        
        for backup_file in self.backup_dir.glob("*"):
            if backup_file.name in ["manifest.json", "git_state.json"]:
                continue
            
            # Determine original location
            if backup_file.name == "TASK.md":
                target = Path("planning/TASK.md")
            elif backup_file.name == "sprint.config.json":
                target = Path("planning/sprint.config.json")
            elif backup_file.name == "labels.yml":
                target = Path(".github/labels.yml")
            else:
                self.restore_log.append(f"⚠️  Unknown file: {backup_file.name}")
                continue
            
            # Create backup of current state
            if target.exists():
                current_backup = Path(f"backups/pre-restore/{target.name}.{datetime.now().strftime('%Y%m%d-%H%M%S')}")
                current_backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, current_backup)
                self.restore_log.append(f"📋 Current state backed up: {current_backup}")
            
            # Restore file
            shutil.copy2(backup_file, target)
            restored_files.append(str(target))
            self.restore_log.append(f"✓ Restored: {target}")
        
        return restored_files
    
    def validate_restored_state(self) -> bool:
        """Validate system state after restore."""
        try:
            # Validate TASK.md
            result = subprocess.run(
                ["python", "scripts/validate_tasks.py", "planning/TASK.md", "--quiet"],
                capture_output=True
            )
            if result.returncode != 0:
                self.restore_log.append("❌ TASK.md validation failed after restore")
                return False
            
            # Validate sprint config
            with open("planning/sprint.config.json", "r") as f:
                json.load(f)  # Will raise exception if invalid
            
            self.restore_log.append("✓ All validations passed")
            return True
            
        except Exception as e:
            self.restore_log.append(f"❌ Validation error: {e}")
            return False
    
    def create_restore_audit(self, manifest: Dict, restored_files: list) -> None:
        """Create audit trail for restore operation."""
        audit_record = {
            "restore_timestamp": datetime.now().isoformat(),
            "checkpoint_id": self.checkpoint_id,
            "original_checkpoint": manifest,
            "restored_files": restored_files,
            "restore_log": self.restore_log,
            "operator": subprocess.check_output(["git", "config", "user.name"]).decode().strip(),
            "git_state_after": {
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
                "status": subprocess.check_output(["git", "status", "--porcelain"]).decode()
            }
        }
        
        audit_path = Path(f"docs/audit/restore-{self.checkpoint_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(audit_path, "w") as f:
            json.dump(audit_record, f, indent=2)
        
        print(f"📋 Audit record created: {audit_path}")
    
    def restore(self) -> bool:
        """Execute full restore process."""
        try:
            manifest = self.load_manifest()
            
            if not self.confirm_restore(manifest):
                print("❌ Restore cancelled by user")
                return False
            
            print("🔄 Starting restore process...")
            restored_files = self.restore_files(manifest)
            
            if self.validate_restored_state():
                self.create_restore_audit(manifest, restored_files)
                print(f"✅ Restore completed successfully")
                print(f"📋 {len(restored_files)} files restored")
                print(f"🆔 Checkpoint: {self.checkpoint_id}")
                return True
            else:
                print("❌ Restore validation failed")
                print("💡 Check restore logs for details")
                return False
                
        except Exception as e:
            self.restore_log.append(f"❌ Restore failed: {e}")
            print(f"❌ Restore failed: {e}")
            return False

# CLI interface
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python restore_checkpoint.py <checkpoint_id> [--force]")
        sys.exit(1)
    
    checkpoint_id = sys.argv[1]
    force = "--force" in sys.argv
    
    restorer = CheckpointRestorer(checkpoint_id, force)
    success = restorer.restore()
    sys.exit(0 if success else 1)
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

class AuditLogger:
    def __init__(self, component: str):
        self.component = component
        self.audit_dir = Path("docs/audit")
        self.audit_dir.mkdir(exist_ok=True)
        self.session_id = self._generate_session_id()
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return hashlib.sha256(f"{self.component}-{timestamp}".encode()).hexdigest()[:16]
    
    def log_operation(
        self,
        operation: str,
        details: Dict[str, Any],
        result: str = "success",
        files_affected: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a single operation with full context."""
        
        audit_entry = {
            "audit_id": f"AUD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{self.component}",
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": self.component,
            "operation": operation,
            "result": result,
            "details": details,
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
            audit_entry["file_checksums"] = self._calculate_checksums(files_affected)
        
        # Write audit entry
        audit_file = self.audit_dir / f"audit-{datetime.now(timezone.utc).strftime('%Y-%m')}.jsonl"
        with open(audit_file, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
        
        return audit_entry["audit_id"]
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            import subprocess
            return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        except:
            return None
    
    def _get_workflow_run_id(self) -> Optional[str]:
        """Get GitHub Actions workflow run ID."""
        import os
        return os.environ.get("GITHUB_RUN_ID")
    
    def _get_actor(self) -> Optional[str]:
        """Get the actor (user or system) performing the operation."""
        import os
        github_actor = os.environ.get("GITHUB_ACTOR")
        if github_actor:
            return f"github:{github_actor}"
        
        try:
            import subprocess
            return f"git:{subprocess.check_output(['git', 'config', 'user.name']).decode().strip()}"
        except:
            return "system:unknown"
    
    def _calculate_checksums(self, files: List[str]) -> Dict[str, str]:
        """Calculate SHA256 checksums for files."""
        checksums = {}
        for file_path in files:
            path = Path(file_path)
            if path.exists():
                with open(path, "rb") as f:
                    checksums[file_path] = hashlib.sha256(f.read()).hexdigest()
        return checksums
    
    def log_failure(
        self,
        operation: str,
        error: str,
        context: Dict[str, Any],
        recovery_action: Optional[str] = None
    ) -> str:
        """Log operation failure with recovery context."""
        
        failure_details = {
            "error_message": error,
            "context": context,
            "recovery_action": recovery_action,
            "stack_trace": self._get_stack_trace()
        }
        
        return self.log_operation(
            operation=operation,
            details=failure_details,
            result="failure",
            metadata={"requires_investigation": True}
        )
    
    def _get_stack_trace(self) -> Optional[str]:
        """Get current stack trace for debugging."""
        try:
            import traceback
            return traceback.format_exc()
        except:
            return None
    
    def create_integrity_report(self) -> Dict[str, Any]:
        """Create audit trail integrity report."""
        audit_files = list(self.audit_dir.glob("audit-*.jsonl"))
        
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_files_count": len(audit_files),
            "total_entries": 0,
            "components": {},
            "date_range": {"earliest": None, "latest": None},
            "integrity_status": "valid"
        }
        
        for audit_file in audit_files:
            try:
                with open(audit_file, "r") as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            entry = json.loads(line.strip())
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
                                    
                        except json.JSONDecodeError:
                            report["integrity_status"] = "corrupted"
                            report.setdefault("errors", []).append(f"Invalid JSON in {audit_file}:{line_num}")
                            
            except Exception as e:
                report["integrity_status"] = "error"
                report.setdefault("errors", []).append(f"Failed to read {audit_file}: {e}")
        
        # Save integrity report
        report_file = self.audit_dir / f"integrity-report-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        return report

# Usage example for workflows
def log_workflow_operation(component: str, operation: str, **kwargs):
    """Convenience function for workflow logging."""
    logger = AuditLogger(component)
    return logger.log_operation(operation, kwargs)

# CLI interface for integrity checking
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "integrity-check":
        logger = AuditLogger("audit-system")
        report = logger.create_integrity_report()
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["integrity_status"] == "valid" else 1)
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
"""
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from scripts.create_recovery_checkpoint import RecoveryCheckpoint
from scripts.restore_checkpoint import CheckpointRestorer
from scripts.audit_logger import AuditLogger

class TestRecoverySystem:
    
    def test_checkpoint_creation(self):
        """Test checkpoint creation process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test environment
            test_task_file = Path(temp_dir) / "planning" / "TASK.md"
            test_task_file.parent.mkdir(parents=True)
            test_task_file.write_text("# Test TASK.md content")
            
            # Create checkpoint
            checkpoint = RecoveryCheckpoint("test", "unit-test")
            checkpoint.backup_dir = Path(temp_dir) / "backups" / checkpoint.checkpoint_id
            
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                checkpoint_id = checkpoint.create_checkpoint()
            
            # Verify checkpoint created
            assert checkpoint.backup_dir.exists()
            assert (checkpoint.backup_dir / "manifest.json").exists()
            assert (checkpoint.backup_dir / "TASK.md").exists()
    
    def test_checkpoint_restore(self):
        """Test checkpoint restoration process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup checkpoint
            checkpoint_dir = Path(temp_dir) / "backups" / "checkpoints" / "test-checkpoint"
            checkpoint_dir.mkdir(parents=True)
            
            # Create manifest
            manifest = {
                "checkpoint_id": "test-checkpoint",
                "type": "test",
                "operation": "unit-test",
                "timestamp": "2025-07-06T10:00:00Z"
            }
            (checkpoint_dir / "manifest.json").write_text(json.dumps(manifest))
            
            # Create backup file
            (checkpoint_dir / "TASK.md").write_text("# Original content")
            
            # Create current file (to be restored)
            current_file = Path(temp_dir) / "planning" / "TASK.md"
            current_file.parent.mkdir(parents=True)
            current_file.write_text("# Modified content")
            
            # Test restore
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                restorer = CheckpointRestorer("test-checkpoint", force=True)
                success = restorer.restore()
            
            assert success
            assert current_file.read_text() == "# Original content"
    
    def test_audit_logging(self):
        """Test audit logging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup audit logger
            logger = AuditLogger("test-component")
            logger.audit_dir = Path(temp_dir) / "audit"
            
            # Log operation
            audit_id = logger.log_operation(
                operation="test_operation",
                details={"test": "data"},
                files_affected=["test_file.md"]
            )
            
            # Verify audit entry
            assert audit_id.startswith("AUD-")
            audit_files = list(logger.audit_dir.glob("audit-*.jsonl"))
            assert len(audit_files) == 1
            
            # Verify audit content
            with open(audit_files[0], "r") as f:
                audit_entry = json.loads(f.read().strip())
                assert audit_entry["operation"] == "test_operation"
                assert audit_entry["component"] == "test-component"

    def test_failure_scenarios(self):
        """Test various failure scenarios."""
        # Test invalid checkpoint restoration
        with pytest.raises(FileNotFoundError):
            CheckpointRestorer("nonexistent-checkpoint")
        
        # Test corrupted manifest
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_dir = Path(temp_dir) / "backups" / "checkpoints" / "corrupted"
            checkpoint_dir.mkdir(parents=True)
            (checkpoint_dir / "manifest.json").write_text("invalid json")
            
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                restorer = CheckpointRestorer("corrupted", force=True)
                with pytest.raises(json.JSONDecodeError):
                    restorer.load_manifest()

if __name__ == "__main__":
    pytest.main([__file__])
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