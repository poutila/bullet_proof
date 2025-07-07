# 🚫 NO.md – Non-Negotiable Practices and Refactoring Restrictions

This file aggregates all the **non-negotiable constraints** gathered from project documentation.

These are rules that must **NEVER** be violated under any circumstances during development or refactoring.

---


## ❌ Restrictions from `CLAUDE.md`

- - **NEVER commit secrets, API keys, passwords, or sensitive data** to version control
- - **NEVER log sensitive information** (passwords, tokens, PII, financial data)
- - **Use parameterized queries** - never concatenate user input into SQL
- - **Always implement proper exception handling** with specific exception types (never bare `except:`)
- - **Write tests BEFORE or ALONGSIDE code** - never after
- ✅ Each class/function has **one purpose** | 🚫 Avoid mixing concerns (e.g., DB logic + business logic)
- **Clients should not be forced to depend on methods they do not use.**
- **High-level modules must not depend on low-level modules. Both depend on abstractions.**
- - **NEVER create files longer than 500 lines** (including comments, excluding imports)
- - **NEVER nest functions more than 3 levels deep**
- - **NEVER create functions with more than 7 parameters** (use dataclasses/Pydantic models)
- - **FORBIDDEN PATTERNS** - CI will reject code containing:
- - **NEVER hallucinate libraries** - only use verified, existing packages
- - [ ] No forbidden patterns in code

## ❌ Restrictions from `CLAUDE_COMPLIANCE_REPORT.md`

- Many files use `print()` instead of logging (forbidden by CLAUDE.md):

## ❌ Restrictions from `CONTRIBUTING.md`

- 1. **NEVER commit secrets, API keys, or passwords**
- ### Forbidden Patterns
- **DO NOT** create public issues for security vulnerabilities.

## ❌ Restrictions from `GLOSSARY.md`

- **Prohibited Actions**: Architecture decisions, security changes, production deployments.

## ❌ Restrictions from `task_automation_plan.md`

- # Use # delimiter to avoid escaping issues
- # Use # delimiter to avoid escaping issues

## ❌ Restrictions from `README.md`

- - **Secret management**: Never in code, always in secure storage
- - **Never** commit secrets to repository

## ❌ Restrictions from `template.md`

- 5. **Options**: Include at least 3 options (including "do nothing")

## ❌ Restrictions from `git-strategy.md`

- ### Never Do These

## ❌ Restrictions from `decisions.md`

- > **Note**: This document must be updated whenever dependencies change. All exceptions require documented approval.

## ❌ Restrictions from `PLANNING.md`

- **AI Assistants Must NOT**:

## ❌ Restrictions from `TASK.md`

- 2. **Do NOT commit** vulnerability details to public repos

## Always run ruff format . and fix remaining errors.
## Always run ruff check --fix and fix remaining errors.
## Always run mypy . and fix remaining errors.
## Always run pytest and fix remaining errors.
## Always run bandit -r . and fix remaining errors. 