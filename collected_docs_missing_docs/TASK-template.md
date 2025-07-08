# Task Template

> **Instructions**: Copy this template when creating new tasks in TASK.md
> **Reference**: See [TASK.md](./planning/TASK.md) for examples and [CLAUDE.md](./CLAUDE.md) for standards

## Task ID Format
- Sprint tasks: `T-XXX` (e.g., T-001, T-002)
- Hotfixes: `H-XXX` (e.g., H-001)
- Emergency: `E-XXX` (e.g., E-001)

---

## 📋 NEW TASK TEMPLATE

### T-[NUMBER]: [Task Title]
**Created**: YYYY-MM-DD
**Status**: ⏳ pending
**Assignee**: [Username or "unassigned"]
**Effort**: [1, 2, 3, 5, 8, 13, or 21] story points
**Priority**: 🔴 critical | 🟡 high | 🟢 normal | ⚪ low
**Type**: 🐛 bugfix | ✨ feature | 📚 documentation | 🔧 maintenance | 🚨 security

**Description**:
[Clear, concise description of what needs to be done. Include context and why this is needed.]

**Acceptance Criteria**:
- [ ] [Specific, measurable criterion 1]
- [ ] [Specific, measurable criterion 2]
- [ ] [Specific, measurable criterion 3]
- [ ] Tests written and passing (≥90% coverage)
- [ ] Documentation updated

**Technical Details**:
- **Files to modify**: [List key files]
- **Dependencies**: [List any dependencies on other tasks]
- **Testing approach**: [Brief test strategy]

**Security Considerations**:
- [Any security implications]
- [Required security checks]

**Notes**:
- [Any additional context]
- [Potential blockers or risks]

---

## 📊 EFFORT ESTIMATION GUIDE

Use Fibonacci sequence for story points:
- **1**: Trivial change (< 1 hour) - typo fix, config update
- **2**: Small task (1-2 hours) - simple bug fix, minor feature
- **3**: Medium task (2-4 hours) - standard feature, moderate refactoring
- **5**: Large task (1-2 days) - complex feature, significant refactoring
- **8**: Extra large task (3-5 days) - major feature, complex integration
- **13**: Epic (> 1 week) - consider breaking down
- **21+**: Mega epic - must be broken down into subtasks

## 🎯 PRIORITY LEVELS

- 🔴 **Critical**: Security issues, data loss risks, production blockers
- 🟡 **High**: Important features, significant bugs, performance issues
- 🟢 **Normal**: Standard features, minor bugs, improvements
- ⚪ **Low**: Nice-to-have features, cosmetic issues, technical debt

## 📝 COMPLETION CHECKLIST

Before marking a task as complete:
- [ ] All acceptance criteria met
- [ ] Tests written with ≥90% coverage
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] No new security vulnerabilities
- [ ] Performance impact assessed
- [ ] Task moved to COMPLETED section with date

## 🔄 STATUS WORKFLOW

1. **⏳ pending** → Task created, not started
2. **🚧 in-progress** → Active development
3. **👀 review** → In code review
4. **🧪 testing** → Testing/QA phase
5. **✅ done** → Completed and merged

## 📌 IMPORTANT REMINDERS

- Follow all standards in [CLAUDE.md](./CLAUDE.md)
- Create tests BEFORE implementation (TDD)
- Update task status in real-time
- Link related PRs and issues
- Communicate blockers immediately
- Break down tasks > 8 points

---

> **Note**: Delete these instructions when creating actual tasks