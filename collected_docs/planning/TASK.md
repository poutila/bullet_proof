### Sprint File Management
**Versioning Strategy**:
- **Active Sprint**: `TASK.md` (current working file)
- **Sprint Snapshots**: `TASK-v1.0.0.md`, `TASK-v1.1.0.md` (immutable governance records)
- **Archive Location**: `docs/sprint-archives/Sprint-07-2025/TASK-v1.0.0.md`

**Version Increment Rules**:
- **Major (v1.0.0 → v2.0.0)**: New sprint begins
- **Minor (v1.0.0 → v1.1.0)**: Significant scope changes within sprint
- **Patch (v1.1.0 → v1.1.1)**: Corrections, small additions

**Compliance Benefits**:
- **Audit Trail**: Immutable record of task decisions and changes
- **Retrospective Data**: Historical sprint comparison and analysis
- **Regulatory Compliance**: Timestamped evidence of work planning and execution
- **Knowledge Preservation**: Context retention for future team members### Task Templates & GitHub Integration
**Template Location**: Task templates are also available as GitHub issue templates in `.github/ISSUE_TEMPLATE/`:
- `feature_task.md` - New feature development
- `bug_fix.md` - Bug fixes and hotfixes  
- `refactoring.md` - Code refactoring tasks
- `technical_debt.md` - Technical debt cleanup

**GitHub Integration Guidelines**:
- **Task ID Reference**: Include `task_id: T-XXX` in GitHub issue body for CI automation
- **Automated Sync**: GitHub Action parses issues with `task_id:` and updates task status in TASK.md
- **Bidirectional Workflow**: 
  - GitHub issue status changes → Auto-update TASK.md
  - TASK.md manual updates → Sync to GitHub via commit hooks
- **Label Synchronization**: Use GitHub labels that match task properties:
  - **Priority Labels**: `priority/critical`, `priority/high`, `priority/medium`, `priority/low`
  - **Type Labels**: `type/feature`, `type/bug`, `type/refactor`, `type/tech-debt`
  - **Status Labels**: `status/not-started`, `status/in-progress`, `status/blocked`, `status/review`, `status/testing`, `status/done`
  - **Sprint Labels**: `sprint/Sprint-07-2025`

### GitHub Label Synchronization Checklist
**Verify Required Labels Exist in Repository** (managed via `.github/labels.yml`):
- [ ] **Priority Labels**: `priority/critical`, `priority/high`, `priority/medium`, `priority/low`
- [ ] **Type Labels**: `type/feature`, `type/bug`, `type/refactor`, `type/tech-debt`
- [ ] **Status Labels**: `status/not-started`, `status/in-progress`, `status/blocked`, `status/review`, `status/testing`, `status/done`
- [ ] **Sprint Labels**: `sprint/Sprint-XX-YYYY` (created per sprint)

**Setup Commands**:
```bash
# Validate label configuration
gh api repos/:owner/:repo/labels | jq '.[].name' | grep -E "(priority|type|status|sprint)/"

# Apply labels from configuration
gh workflow run label-sync.yml
```

**CI Validation**: Labels are automatically validated in `.github/workflows/label-sync.yml` on every push to `.github/labels.yml`

**Dual Tracking Workflow**:
1. Create GitHub issue using template
2. Add task to TASK.md with same ID
3. Include `task_id: T-XXX` in issue body
4. Apply appropriate labels for filtering
5. GitHub Action automatically syncs status changes
6. Archive sprint file as `TASK-v1.0.0.md` at sprint end

### GitHub Action Configuration
**Automation Setup**: Create `.github/workflows/task-sync.yml` to:
- **Parse GitHub issues** for `task_id: T-XXX` references
- **Update task status** in TASK.md when issue status changes
- **Sync review status** when PR is opened/merged for task
- **Auto-commit** TASK.md updates with bot account
- **Trigger on**: issue events, PR events, label changes

**Example Action Trigger**:
```yaml
name: Sync Tasks
on:
  issues: [opened, closed, labeled]
  pull_request: [opened, closed, merged]
jobs:
  sync-tasks:
    runs-on: ubuntu-latest
    steps:
      - name: Parse task_id and update TASK.md
        # Custom script to update task status
```# 📋 TASK MANAGEMENT – Sprint-07-2025

> **AI Assistants**: Read [PLANNING.md](PLANNING.md) first for project context, then work on tasks listed below following [CLAUDE.md](../CLAUDE.md) standards.
> **File Version**: TASK-v1.0.0.md (immutable sprint snapshot for governance/compliance)

**Sprint ID**: Sprint-07-2025  
**Sprint Number**: 7 *(auto-generated via CI)*  
**Sprint Dates**: 2025-07-01 to 2025-07-14 *(auto-generated via CI)*  
**Last Updated**: 2025-07-06 14:23:00 UTC *(auto-updated on commit)*  
**Sprint Goal**: [Brief description of sprint objective]

## 📊 SPRINT DASHBOARD

| Metric | Value | Target | Status |
|------------------------|-----------|--------|--------|
| **Total Story Points** | 18 | 20 | ✅ |
| **Completed Points** | 0 | 18 | 🔄 |
| **Velocity (Last Sprint)** | 21 points | 18-22 | ✅ |
| **PR Review Time Avg** | 18h | <24h | ✅ |
| **Code Coverage** | 92% | >90% | ✅ |
| **Bug Escape Rate** | 0 | <2/month | ✅ |
| **Sprint Progress** | 0% | 100% | 🔄 |
| **Blocked Tasks** | 1 | 0 | ⚠️ |

**Health Indicator**: 🟡 **On Track** *(6/8 metrics green)*

## 📜 DOCUMENT CHANGELOG
<!-- changelog-insert-point -->
- **v1.0.0** (2025-07-10) – Initial sprint file creation
- **v1.1.0** (2025-07-12) – Added review status column and PR link integration
- **v1.1.1** (2025-07-14) – Corrected dependency mapping for T-004

### **Audit & Retention Policy**
**Document Retention Period**: This sprint task file and all archived versions must be retained for **minimum 7 years** to comply with:
- **SOX Compliance**: Software development process documentation requirements
- **ISO 27001**: Information security management audit trails  
- **Regulatory Standards**: Industry-specific compliance obligations
- **Internal Audit**: Corporate governance and process validation

**Archive Location**: All sprint versions permanently stored in `docs/sprint-archives/Sprint-XX-YYYY/` with immutable file permissions.

**Legal Hold Capability**: Documents may be subject to extended retention during litigation or regulatory investigation.

**Access Controls**: 
- **Read Access**: All team members for transparency and learning
- **Modification Rights**: None - archived documents are immutable compliance records
- **Administrative Access**: Limited to compliance officers and senior leadership per data governance policy

**Disposal Policy**: No automatic deletion of compliance-critical sprint documentation. Secure disposal procedures apply only after legal and regulatory retention periods expire and formal approval from compliance team.

---

## 🧩 CURRENT SPRINT TASKS

**Sprint Status Summary**: ✅ Completed: 0 | 🔄 In Progress: 1 | 🚫 Blocked: 1 | 📋 Not Started: 2 | **Total: 4**

| ID | Title | Description | Priority | Points | Status | Reviewed | Owner | PR Link | ETA | Depends On | Sprint ID | Notes |
|----|-------|-------------|----------|--------|--------|----------|-------|---------|-----|------------|-----------|-------|
| T-001 | Implement Auth Middleware | JWT authentication following CLAUDE security standards. Must pass all quality gates. | High | 8 | In Progress | 🔍 | @devA | [#123](../pull/123) | 2025-07-15 | - | Sprint-07-2025 | Blocked on schema review |
| T-002 | Add User Registration API | FastAPI endpoint with Pydantic validation. Include comprehensive tests. | High | 5 | Not Started | ✖️ | @devB | - | 2025-07-16 | T-001 | Sprint-07-2025 | Depends on auth middleware |
| T-003 | Database Migration Script | Add user_preferences table. Include rollback strategy. | Medium | 3 | Not Started | ✖️ | @devA | - | 2025-07-17 | - | Sprint-07-2025 | Review with DBA required |
| T-004 | Update API Documentation | Regenerate OpenAPI docs after auth changes. | Low | 2 | Not Started | ✖️ | @devC | - | 2025-07-18 | T-001, T-002 | Sprint-07-2025 | Auto-generated from code |

### Task Status Legend
- **Not Started**: Ready to begin
- **In Progress**: Actively being worked on
- **[Blocked](../GLOSSARY.md#blocked-task-status)**: Waiting for external dependency
- **Review**: Code complete, awaiting peer review
- **Testing**: In QA or integration testing
- **Done**: Complete and merged

### Review Status Legend
- **✔️**: Code reviewed and approved, ready for merge
- **✖️**: No code submitted yet / Nothing to review
- **🔍**: Currently under review (PR open)
- **⚠️**: Review requested changes, awaiting developer fixes
- **🚀**: Approved and merged to main branch

### Priority Guidelines
- **Critical**: Production issue, security vulnerability
- **High**: Sprint goal dependency, user-facing feature
- **Medium**: Important but not sprint-critical
- **Low**: Nice-to-have, [technical debt](../GLOSSARY.md#technical-debt), documentation

### [Story Points](../GLOSSARY.md#story-points) Reference
- **1**: Simple change, < 2 hours (config update, documentation fix)
- **3**: Moderate task, < 1 day (small feature, straightforward bug fix)
- **5**: Complex task, 1-3 days (API endpoint with tests, integration work)
- **8**: Large task, 3-5 days (significant feature, complex refactoring)
- **13**: [Epic](../GLOSSARY.md#epic), > 1 week (major feature, architectural change - consider splitting)
- **21+**: Epic requiring separate tracking (create `epics/E-XXX.md` file)

### Epic Task Reference
**For tasks with 21+ points, create dedicated [epic](../GLOSSARY.md#epic) files**:
- **Epic File Template**: `epics/E-XXX-epic-name.md`
- **Task Reference Format**: `Epic: E-XXX Epic Name`
- **Epic Breakdown**: Large epics split into 3-8 point sub-tasks
- **Note**: Epic files to be created in `epics/` directory when needed

---

## 🆕 SCOPE EXPANSIONS

*Tasks discovered during current sprint that expand the original scope*

- [ ] **T-101**: Add retry logic to ServiceX integration - *Discovered during T-001 auth implementation* - **Points**: 3 - **Sprint ID**: Sprint-07-2025
- [ ] **T-102**: Update CORS configuration for new auth flow - *Required for T-001 to work properly* - **Points**: 2 - **Sprint ID**: Sprint-07-2025

## 📥 BACKLOG CANDIDATES

*Tasks discovered during work that should be considered for future sprints*

- [ ] **T-201**: Fix flaky test in user validation module - *Found during T-002 testing* - **Points**: 2
- [ ] **T-202**: Performance optimization for user search endpoint - *Current response time 800ms* - **Points**: 5
- [ ] **T-203**: Refactor legacy payment module to use new patterns - *Technical debt cleanup* - **Points**: 8
- [ ] **T-204**: Implement rate limiting on auth endpoints - *Security enhancement* - **Points**: 3
- [ ] **T-205**: Add architecture diagrams to docs/ - *Documentation improvement* - **Points**: 2

## 🔄 TASK MOVEMENT LOG

*Track when tasks move between sections for retrospective analysis*

| Date | Task ID | From | To | Reason | Impact |
|------|---------|------|----|---------|---------| 
| 2025-07-12 | T-203 | Scope Expansion | Backlog | Too large for current sprint | +8 points to backlog |
| 2025-07-11 | T-102 | Discovered | Scope Expansion | Critical for T-001 completion | +2 points to sprint |

### ID Convention
- **T-001 to T-099**: Planned sprint tasks
- **T-100 to T-199**: Scope expansions (current sprint additions)
- **T-200+**: Backlog candidates (future sprint consideration)

---

## 🚩 BLOCKERS & DEPENDENCIES

### Active Blockers
| Task ID | Blocker | Blocking Since | Owner | Expected Resolution |
|---------|---------|----------------|-------|-------------------|
| T-001 | Waiting for API schema from partner system | 2025-07-10 | @partnerTeam | 2025-07-14 |
| T-003 | DBA review for migration script | 2025-07-12 | @dbaTeam | 2025-07-15 |

### Task Dependencies & Blocking
| Task ID | Blocked By | Impact | Resolution Plan |
|---------|------------|---------|-----------------|
| T-002 | T-001 (auth middleware) | Cannot start user registration without auth | Complete T-001 first |
| T-004 | T-001, T-002 (API changes) | Documentation depends on API completion | Update docs after API stabilizes |

### External Dependencies
- [ ] **Partner API Schema**: Required for auth integration (T-001)
- [ ] **Security Review**: Required before auth deployment (T-001, T-002)
- [ ] **Infrastructure**: Staging environment setup for testing (T-002, T-003)

---

## ✅ COMPLETED TASKS

| ID | Title | Completion Date | Owner | Notes |
|----|-------|----------------|-------|-------|
| T-000 | Setup CI with `nox` hooks | 2025-07-04 | @devA | All quality gates working |
| T-999 | Implement user login endpoint | 2025-07-08 | @devB | Includes session management |
| T-998 | Add password reset flow | 2025-07-09 | @devC | Email integration complete |

---

## 🎯 TASK TEMPLATES

### New Feature Task Template
```markdown
**ID**: T-XXX
**Title**: [Clear, action-oriented title]
**Points**: [Story points: 1=Simple, 3=Moderate, 5=Complex, 8=Large, 13=Epic]
**Depends On**: [T-XXX, T-YYY] or "None"
**Sprint ID**: [Sprint-XX-YYYY]
**GitHub Issue**: [Optional: Link to GitHub issue]
**GitHub Body Reference**: `task_id: T-XXX` (include this in GitHub issue body for automation)
**Description**: 
- What: [What needs to be built]
- Why: [Business justification]
- How: [Technical approach]

**[Acceptance Criteria](../GLOSSARY.md#acceptance-criteria)**:
- [ ] Functional requirement 1
- [ ] Functional requirement 2
- [ ] Non-functional requirement (performance, security)
- [ ] Tests written with >90% coverage
- [ ] Documentation updated
- [ ] Security review passed (if applicable)

**Technical Requirements**:
- [ ] Follows [SOLID principles](../GLOSSARY.md#solid-principles)
- [ ] Passes all [quality gates](../GLOSSARY.md#quality-gates) (typing, linting, security)
- [ ] Includes error handling and logging
- [ ] API endpoints include OpenAPI documentation
- [ ] Database changes include migration scripts

**[Definition of Done](../GLOSSARY.md#definition-of-done-dod)**:
- [ ] [Code reviewed](../GLOSSARY.md#code-review) and approved
- [ ] All tests pass (unit, integration, e2e)
- [ ] Deployed to staging and tested
- [ ] Documentation updated
- [ ] Stakeholder acceptance received
```

### Bug Fix Task Template
```markdown
**ID**: T-XXX
**Title**: [Bug: Clear description of issue]
**Points**: [Usually 1-3 for bugs, 5+ for complex issues]
**Depends On**: [T-XXX if requires other fixes] or "None"
**Description**:
- **Problem**: [What is broken]
- **Impact**: [Who/what is affected]
- **Root Cause**: [Why it happened]
- **Solution**: [How to fix it]

**Reproduction Steps**:
1. [Step 1]
2. [Step 2]
3. [Expected vs Actual behavior]

**Requirements**:
- [ ] [Regression test](../GLOSSARY.md#regression-test) added to prevent recurrence
- [ ] Root cause addressed, not just symptoms
- [ ] All related tests still pass
- [ ] Hotfix process followed (if production issue)

**[Definition of Done](../GLOSSARY.md#definition-of-done-dod)**:
- [ ] Issue no longer reproducible
- [ ] Regression test passes
- [ ] [Code reviewed](../GLOSSARY.md#code-review) and approved
- [ ] Deployed and verified in production
```

### Refactoring Task Template
```markdown
**ID**: T-XXX
**Title**: [Refactor: Component/Module name]
**Points**: [Usually 3-8 depending on scope]
**Depends On**: [T-XXX if requires other work] or "None"
**Description**:
- **Current State**: [What needs improvement]
- **Target State**: [Desired outcome]
- **Benefits**: [Performance, maintainability, etc.]

**Scope**:
- [ ] Files/modules to be changed
- [ ] External interfaces affected
- [ ] Database schema changes (if any)

**Requirements**:
- [ ] No functional behavior changes
- [ ] All existing tests continue to pass
- [ ] Code follows [SOLID principles](../GLOSSARY.md#solid-principles)
- [ ] Performance maintained or improved
- [ ] Documentation updated

**[Definition of Done](../GLOSSARY.md#definition-of-done-dod)**:
- [ ] [Refactoring](../GLOSSARY.md#refactoring) complete
- [ ] All tests pass
- [ ] Performance benchmarks met
- [ ] [Code review](../GLOSSARY.md#code-review) approved
- [ ] No regression in functionality
```

---

## 📊 SPRINT METRICS

### Sprint Progress
- **Total Tasks**: 4
- **Total Story Points**: 18
- **Completed**: 0 (0 points)
- **In Progress**: 1 (8 points)
- **Blocked**: 1 (0 points - T-001 blocking T-002, T-004)
- **Not Started**: 2 (10 points)

### Quality Metrics
- **Code Coverage**: 92% (Target: >90%)
- **PR Review Time**: 18h avg (Target: <24h)
- **Bug Escape Rate**: 0 this sprint (Target: <2/month)
- **Tech Debt Items**: 3 added, 1 resolved

### Velocity Tracking
- **Story Points Committed**: 18
- **Story Points Completed**: 0
- **Burndown**: Behind (Day 3 of 10, expected: 5 points completed)
- **Previous Sprint Velocity**: 21 points
- **Projected Completion**: 95% (17/18 points) based on current blockers

---

## 🔄 TASK WORKFLOW

### AI Assistant Guidelines
**When Starting a Task**:
1. Read task requirements and [acceptance criteria](../GLOSSARY.md#acceptance-criteria)
2. Review related code and existing patterns
3. Create implementation plan following [SOLID principles](../GLOSSARY.md#solid-principles)
4. Write tests first (TDD approach when possible)
5. Implement feature following project patterns
6. Run all [quality gates](../GLOSSARY.md#quality-gates) before requesting review

**Task Progression**:
```
Not Started → In Progress → Review → Testing → Done
             ↓
         ([Blocked](../GLOSSARY.md#blocked-task-status) if external dependency)
```

### Human Review Requirements
- **All AI-generated code** must be [peer-reviewed](../GLOSSARY.md#code-review)
- **Architectural changes** require tech lead approval
- **Security-related changes** require security team review
- **Database changes** require DBA review
- **Breaking changes** require stakeholder approval

### [Quality Gates](../GLOSSARY.md#quality-gates) (Must Pass)
- [ ] Type checking (`mypy`)
- [ ] Linting (`ruff check`)
- [ ] Formatting (`ruff format`)
- [ ] Tests (`pytest` with >90% coverage)
- [ ] Security scan (`bandit`)
- [ ] No vulnerabilities (`safety`)
- [ ] Complexity check (`radon cc`)

---

## 📝 TASK MANAGEMENT RULES

### Adding New Tasks
1. **Use next available ID** (T-XXX format)
2. **Include clear [acceptance criteria](../GLOSSARY.md#acceptance-criteria)**
3. **Estimate effort** (S/M/L or [story points](../GLOSSARY.md#story-points))
4. **Assign priority** based on [sprint](../GLOSSARY.md#sprint) goals
5. **Add to appropriate section** (Current Sprint vs Future)

### Updating Task Status
1. **Update status immediately** when work begins/completes
2. **Add notes** for context or blockers
3. **Update [ETA](../GLOSSARY.md#eta-estimated-time-of-arrival)** if timeline changes
4. **Move to appropriate section** when complete

### Task [Dependencies](../GLOSSARY.md#dependency)
- **Document dependencies** in task description
- **Block dependent tasks** until prerequisites complete
- **Update multiple tasks** when blockers are resolved

### Sprint Boundaries
- **No new tasks added mid-[sprint](../GLOSSARY.md#sprint)** without team approval
- **Scope changes** require product [owner](../GLOSSARY.md#owner) approval
- **Completed tasks** moved to [archive](../GLOSSARY.md#archive) after sprint review

---

## 🆘 EMERGENCY PROTOCOL

### Critical Issues (Production Down)
1. **Create emergency task** with ID format: URGENT-XXX
2. **Notify team lead** immediately
3. **Follow hotfix process** from PLANNING.md
4. **Document in incident log**

### Security Vulnerabilities
1. **Mark as CRITICAL priority**
2. **Do NOT commit** vulnerability details to public repos
3. **Follow security disclosure** process
4. **Coordinate with security team**

---

## 📚 REFERENCES

### Project Documents
- **[PLANNING.md](PLANNING.md)** - Project architecture and standards
- **[CLAUDE.md](../CLAUDE.md)** - AI behavior rules and quality gates
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and changes

### Tools & Resources
- **Task Tracking**: [GitHub Projects](https://github.com/your-org/your-repo/projects) *(placeholder - update with actual URL)*
- **Code Repository**: [GitHub Repository](https://github.com/your-org/your-repo) *(placeholder - update with actual URL)*
- **CI/CD Pipeline**: [GitHub Actions](https://github.com/your-org/your-repo/actions) *(placeholder - update with actual URL)*
- **Documentation**: [Project Docs](https://your-org.github.io/your-repo) *(placeholder - update with actual URL)*

### Automation & Configuration Links
- **Task Sync Workflow**: [`.github/workflows/task-sync.yml`](https://github.com/your-org/your-repo/blob/main/.github/workflows/task-sync.yml)
- **Label Configuration**: [`.github/labels.yml`](https://github.com/your-org/your-repo/blob/main/.github/labels.yml)
- **Label Sync Workflow**: [`.github/workflows/label-sync.yml`](https://github.com/your-org/your-repo/blob/main/.github/workflows/label-sync.yml)
- **Issue Templates**: [`.github/ISSUE_TEMPLATE/`](https://github.com/your-org/your-repo/tree/main/.github/ISSUE_TEMPLATE)
- **Sprint Archive Workflow**: [`.github/workflows/task-archive.yml`](https://github.com/your-org/your-repo/blob/main/.github/workflows/task-archive.yml)

### Quick Commands
```bash
# Local development setup (fast with uv)
uv venv venv_local && source venv_local/bin/activate
uv pip install -r requirements-dev.txt

# Start working on a task
git checkout -b feature/T-XXX-task-description
nox -s tests  # Run all quality gates
git commit -m "feat(T-XXX): implement feature description"

# Quality check before PR
nox -s lint tests security

# Traditional setup (CI/compatibility)
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
```

---

**Last Sprint Review**: [YYYY-MM-DD]  
**Next Sprint Planning**: [YYYY-MM-DD]  
**Document Owner**: [Team Lead Name]

*This document is updated continuously throughout the sprint. For historical task data, see `docs/sprint-summaries/`*