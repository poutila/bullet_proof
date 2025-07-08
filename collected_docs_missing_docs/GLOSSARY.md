# 📚 PROJECT GOVERNANCE GLOSSARY

> **Canonical Definitions**: This document provides authoritative definitions for all terms used across project governance documents (CLAUDE.md, PLANNING.md, TASK.md). When in doubt, refer to these definitions.

**Last Updated**: 2025-07-07  
**Maintained By**: [Tech Lead/Project Manager]

## 📚 Related Documentation
- **Development Standards**: [CLAUDE.md](./CLAUDE.md) - Core development guidelines
- **Project Architecture**: [PLANNING.md](./planning/PLANNING.md) - System design
- **Task Management**: [TASK.md](./planning/TASK.md) - Current tasks
- **Technical Registry**: [TECHNICAL_REGISTRY.md](./planning/TECHNICAL_REGISTRY.md) - Component tracking
- **Contributing Guide**: [CONTRIBUTING.md](./CONTRIBUTING.md) - How to contribute

---

## 🔤 ALPHABETICAL INDEX

**Quick Navigation**: [A](#a) | [B](#b) | [C](#c) | [D](#d) | [E](#e) | [F](#f) | [G](#g) | [H](#h) | [I](#i) | [L](#l) | [M](#m) | [N](#n) | [O](#o) | [P](#p) | [Q](#q) | [R](#r) | [S](#s) | [T](#t) | [V](#v) | [W](#w)

---

## A

### **Acceptance Criteria** {#acceptance-criteria}
Specific, measurable conditions that must be met for a task to be considered complete. Written in "Given-When-Then" format or as bullet points. Must be testable and verifiable.

**Example**: "Given a user is logged in, when they click 'Save Profile', then their changes are persisted to the database and a success message is displayed."

### **ADR (Architecture Decision Record)** {#adr-architecture-decision-record}
A document that captures an important architectural decision made along with its context and consequences. Stored in `docs/adr/` with unique IDs (ADR-001, ADR-002, etc.).

**Template**: Problem statement, considered options, decision, rationale, consequences.

### **AI Assistant** {#ai-assistant}
Software agent (like Claude) that helps with development tasks following the rules defined in CLAUDE.md. Must operate within defined boundaries and always be subject to human review.

**Authorized Actions**: Code generation, testing, documentation updates, refactoring within established patterns.
**Prohibited Actions**: Architecture decisions, security changes, production deployments.

### **Archive** {#archive}
Immutable historical record of project documents stored in `docs/sprint-archives/` for compliance, audit, and retrospective purposes. Archives are read-only and versioned.

---

## B

### **Backlog**
Prioritized list of work items (features, bugs, technical debt) awaiting implementation. Maintained by Product Owner with input from development team.

**Types**: Product backlog (business features), Sprint backlog (current sprint work), Technical backlog (tech debt).

### **Blocked (Task Status)** {#blocked-task-status}
A task that cannot proceed due to external dependencies, missing information, or unresolved issues. Blocked tasks require immediate attention to remove impediments.

**Common Blockers**: Waiting for external API access, pending stakeholder decision, dependency on incomplete task, missing environment setup.

### **Burndown**
Chart showing remaining work in a sprint over time. Indicates whether the team is on track to complete committed work by sprint end.

**Healthy Pattern**: Steady downward slope. **Warning Signs**: Flat line (no progress), steep drop at end (last-minute completion).

---

## C

### **CHANGELOG.md**
Chronological record of notable changes made to the project. Follows [Keep a Changelog](https://keepachangelog.com/) format with versions and release dates.

**Categories**: Added, Changed, Deprecated, Removed, Fixed, Security.

### **CI/CD (Continuous Integration/Continuous Deployment)**
Automated pipeline that builds, tests, and deploys code changes. Configured in `.github/workflows/` using GitHub Actions.

**Quality Gates**: Type checking, linting, testing, security scanning, performance validation.

### **Code Coverage**
Percentage of code executed during automated tests. Minimum requirement is 90% line coverage, with additional mutation testing for critical business logic.

**Types**: Line coverage, branch coverage, function coverage, mutation coverage.

### **Code Review** {#code-review}
Systematic examination of code changes by team members before merge. Required for all changes, including AI-generated code.

**Requirements**: Two approvals for major changes, one approval for minor changes, security review for auth/data changes.

### **Complexity (Cyclomatic)**
Measure of code complexity based on the number of linearly independent paths through code. Maximum allowed complexity is 10 per function.

**Calculation**: Number of decision points (if, while, for, case) + 1.

---

## D

### **Definition of Done (DoD)** {#definition-of-done-dod}
Shared understanding of what it means for a task to be complete. Includes all requirements that must be met before work can be considered finished.

**Standard DoD**:
- [ ] Code written and reviewed
- [ ] Tests written with >90% coverage
- [ ] Documentation updated
- [ ] Security scan passed
- [ ] Performance requirements met
- [ ] Stakeholder acceptance received

### **Dependency** {#dependency}
Relationship between tasks where one task cannot start or complete until another task is finished. Tracked in "Depends On" column of task tables.

**Types**: Finish-to-start (most common), start-to-start, finish-to-finish, start-to-finish.

### **Deploy**
Process of moving code from development environment to production. Includes database migrations, configuration updates, and health checks.

**Environments**: Development → Staging → Production.

---

## E

### **Epic**
Large body of work that can be broken down into smaller tasks. Typically 21+ story points requiring separate tracking in `epics/E-XXX.md` files.

**Characteristics**: Cross-functional, multiple sprints, significant business value, clear success criteria.

### **Escalation**
Process of moving decisions or conflicts to higher levels of authority when normal resolution channels are insufficient. Defined hierarchy: Team Lead → Tech Lead → Product Owner → Engineering Manager.

**Triggers**: Automation conflicts, repeated failures, resource disputes, technical disagreements.

### **ETA (Estimated Time of Arrival)**
Projected completion date for a task based on current progress and known dependencies. Updated regularly as new information becomes available.

---

## F

### **Feature**
New functionality or enhancement that provides value to users. Distinguished from bugs (fixes existing functionality) and technical debt (internal improvements).

**Lifecycle**: Conception → Design → Development → Testing → Release → Monitoring.

---

## G

### **GitHub Actions**
Automation platform integrated with GitHub repositories. Used for CI/CD pipelines, task synchronization, and automated quality checks.

**Workflows**: task-sync.yml, label-sync.yml, task-archive.yml, auto-update-metadata.yml.

---

## H

### **Health Check**
Automated endpoint or script that verifies system components are functioning correctly. Required for all services at `/health` and `/ready` endpoints.

**Types**: Liveness check (is service running), Readiness check (is service ready to handle requests).

---

## I

### **Issue Template**
Standardized format for creating GitHub issues. Located in `.github/ISSUE_TEMPLATE/` with specific templates for features, bugs, and technical debt.

**Required Fields**: task_id, description, acceptance criteria, priority, estimated points.

---

## L

### **Label**
GitHub metadata tag used to categorize and filter issues and pull requests. Synchronized from `.github/labels.yml` configuration.

**Categories**: priority/* (critical, high, medium, low), type/* (feature, bug, refactor, tech-debt), status/* (not-started, in-progress, blocked, review, testing, done), sprint/* (Sprint-XX-YYYY).

---

## M

### **Merge**
Integration of code changes from one branch into another. Requires all quality gates to pass and appropriate approvals.

**Types**: Merge commit, squash and merge (preferred), rebase and merge.

### **MTTR (Mean Time to Recovery)**
Average time required to restore service after an incident. Target is <6 hours for all production issues.

**Calculation**: Total downtime ÷ Number of incidents.

### **Mutation Testing**
Advanced testing technique that modifies code to verify tests can detect changes. Required score >80% for business logic modules.

**Tools**: mutmut, cosmic-ray. **Purpose**: Verify test quality beyond simple coverage metrics.

---

## N

### **Nox**
Python tool for automating development tasks in isolated environments. Used for running tests, linting, formatting, and validation.

**Sessions**: tests, lint, format, security, validate_tasks.

---

## O

### **Override**
Manual intervention that bypasses normal automated processes or standards. Requires documentation and justification.

**Types**: Emergency (production issues), Process (standard deviations), Automation (AI conflicts).

### **Owner** {#owner}
Person responsible for a task's completion. Must be a specific individual (not a team) for clear accountability.

**Responsibilities**: Implementation, testing, documentation, stakeholder communication.

---

## P

### **PR (Pull Request)**
Request to merge code changes from a feature branch into the main branch. Triggers automated testing and requires human review.

**Requirements**: Linked to task_id, passing quality gates, appropriate approvals, updated documentation.

### **Priority**
Relative importance of a task for business or technical reasons. Used for scheduling and resource allocation decisions.

**Levels**: Critical (production issues), High (sprint goals), Medium (important but not critical), Low (nice-to-have).

---

## Q

### **Quality Gates**
Automated checks that must pass before code can be merged. Includes type checking, linting, testing, security scanning.

**Tools**: mypy (typing), ruff (linting/formatting), pytest (testing), bandit (security), safety (vulnerabilities).

---

## R

### **Refactoring**
Improving code structure without changing external behavior. Focuses on maintainability, performance, and adherence to coding standards.

**Goals**: Reduce complexity, eliminate duplication, improve readability, enhance testability.

### **Retrospective**
Team meeting held at the end of each sprint to reflect on processes and identify improvements. Includes review of metrics, blockers, and lessons learned.

**Format**: What went well, what could be improved, action items for next sprint.

### **Review Status**
Current state of code review for a task. Tracked in TASK.md with emoji indicators.

**States**: ✔️ (approved), ✖️ (not submitted), 🔍 (under review), ⚠️ (changes requested), 🚀 (merged).

---

## S

### **SLA (Service Level Agreement)**
Commitment to specific performance standards. Includes response times, availability targets, and resolution timeframes.

**Examples**: API response <200ms, PR review <24h, incident resolution <6h.

### **SOLID Principles**
Five design principles for maintainable software: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion.

**Application**: All code should adhere to SOLID principles unless explicitly documented otherwise in an ADR.

### **Sprint**
Time-boxed iteration (typically 1-2 weeks) during which a team works to complete a set of tasks. Begins with planning and ends with review and retrospective.

**Artifacts**: Sprint goal, task list, burndown chart, completed increment.

### **Sprint ID**
Unique identifier for a sprint following the format "Sprint-XX-YYYY" where XX is the sprint number and YYYY is the year.

**Example**: Sprint-07-2025 (7th sprint of 2025).

### **Story Points**
Relative measure of effort required to complete a task. Based on complexity, uncertainty, and work involved rather than time estimates.

**Scale**: 1 (trivial), 2 (small), 3 (moderate), 5 (complex), 8 (large), 13 (epic), 21+ (requires breakdown).

---

## T

### **Task**
Individual unit of work with specific acceptance criteria and clear owner. Identified with unique ID (T-XXX format).

**Components**: Title, description, acceptance criteria, priority, story points, owner, dependencies, status.

### **Task ID**
Unique identifier for tasks following T-XXX format where XXX is a sequential number. Used for tracking across GitHub issues and TASK.md.

**Ranges**: T-001-099 (planned sprint tasks), T-100-199 (scope additions), T-200+ (backlog candidates).

### **Technical Debt** {#technical-debt}
Code that works but is suboptimal for long-term maintenance. Includes shortcuts taken under time pressure that need future improvement.

**Types**: Code quality, documentation, test coverage, performance, security.

---

## V

### **Velocity**
Measure of team's capacity to complete work, calculated as story points completed per sprint. Used for future sprint planning.

**Calculation**: Average story points completed over last 3-6 sprints.

### **Version**
Identifier for a specific release or document iteration. Follows semantic versioning (MAJOR.MINOR.PATCH) for software and documents.

**Increment Rules**: MAJOR (breaking changes), MINOR (new features), PATCH (bug fixes).

---

## W

### **Workflow**
Automated process defined in GitHub Actions. Triggered by events like code pushes, issue changes, or scheduled times.

**Examples**: CI/CD pipeline, task synchronization, sprint archiving, metadata updates.

---

## 📖 DOCUMENT-SPECIFIC TERMS

### **CLAUDE.md Terms**

**AI Behavior Rules**: Guidelines defining what AI assistants can and cannot do
**Bulletproof Standards**: High-quality development practices that prevent common issues
**Emergency Protocol**: Procedures for handling critical production incidents
**Quality Gates**: Automated checks ensuring code meets standards

### **PLANNING.md Terms**

**Health Scorecard**: Dashboard showing project metrics and status
**Architecture Style**: High-level design approach (layered, hexagonal, event-driven, etc.)
**Constraints**: Limitations affecting project decisions (technical, business, compliance)
**Epic Reference**: Link between large tasks and detailed epic documentation

### **TASK.md Terms**

**Sprint Dashboard**: Real-time view of sprint progress and metrics
**Scope Expansion**: Tasks added during sprint execution
**Document Changelog**: History of changes to the TASK.md file
**Movement Log**: Record of tasks moving between sections

---

## 🔄 WORKFLOW STATES

### **Task Status Progression**
```
Not Started → In Progress → Review → Testing → Done
     ↓
  (Blocked - can occur at any stage)
```

### **Review Status Flow**
```
✖️ (Not Submitted) → 🔍 (Under Review) → ✔️ (Approved) → 🚀 (Merged)
                                     ↓
                                  ⚠️ (Changes Requested) → 🔍 (Re-review)
```

### **Escalation Levels**
```
Team Issue → Team Lead → Tech Lead → Product Owner → Engineering Manager
```

---

## 📚 EXTERNAL REFERENCES

### **Standards & Frameworks**
- **OWASP ASVS**: Application Security Verification Standard
- **SOLID**: Object-oriented design principles
- **GitFlow**: Git branching model
- **Semantic Versioning**: Version numbering scheme
- **Keep a Changelog**: Changelog format standard

### **Tools & Technologies**
- **GitHub Actions**: CI/CD automation platform
- **Nox**: Python task automation tool
- **Pytest**: Python testing framework
- **Ruff**: Python linting and formatting tool
- **Bandit**: Python security linting tool
- **uv**: Ultra-fast Python package manager for local development

---

## 🔄 MAINTENANCE

### **uv** {#uv}
Ultra-fast Python package manager (10-100x faster than pip) recommended for local development. Provides automatic Python version management and faster dependency resolution.

**Usage**: `uv venv venv_local` (create environment), `uv pip install -r requirements-dev.txt` (install dependencies)
**Fallback**: Use `pip` for CI/production compatibility

### **Update Triggers**
- **New terminology** introduced in governance documents
- **Process changes** requiring definition updates
- **Tool additions** or changes in development stack (like uv integration)
- **Stakeholder feedback** on unclear terms

### **Review Schedule**
- **Monthly**: Quick review during sprint retrospectives
- **Quarterly**: Comprehensive review with stakeholder feedback
- **As-needed**: When new processes or tools are introduced

### **Ownership**
- **Primary Maintainer**: Tech Lead
- **Contributors**: All team members can suggest additions
- **Approval**: Tech Lead approval required for changes
- **Distribution**: Link from all governance documents

---

*This glossary serves as the single source of truth for project terminology. When updating governance documents, ensure new terms are added here and existing terms remain consistent with these definitions.*
- **agent**: A duplicated term
