# 📦 Dependency Decisions

> **Purpose**: Document rationale for dependency choices and exceptions
> **Standards**: Per [CLAUDE.md](../../CLAUDE.md#environment-management) requirements

## 📚 Related Documentation
- **Development Standards**: [CLAUDE.md](../../CLAUDE.md)
- **Dependency Update Plan**: [dependency_update_action_plan.md](../../dependency_update_action_plan.md)
- **Technical Registry**: [TECHNICAL_REGISTRY.md](../../planning/TECHNICAL_REGISTRY.md)

## 🎯 Dependency Selection Criteria

All dependencies must meet these requirements (from CLAUDE.md):

1. **PyPI Health Score**: >90%
2. **Maintenance**: Not abandoned for >2 years
3. **Security**: No known CVEs
4. **Size**: <10MB (exceptions require approval)
5. **License**: Compatible with project license

## ✅ Approved Dependencies

### Core Development Tools

#### `mypy==1.10.0`
- **Purpose**: Static type checking
- **Health Score**: 95%
- **Rationale**: Industry standard, excellent IDE support
- **Alternatives Considered**: pyright (less mature ecosystem)

#### `ruff==0.4.0` ⚠️ 
- **Status**: NEEDS UPDATE to 0.12.2
- **Purpose**: Fast Python linter
- **Security**: Outdated version has vulnerabilities
- **Action**: See [dependency_update_action_plan.md](../../dependency_update_action_plan.md)

#### `black==24.0.0`
- **Purpose**: Code formatting
- **Health Score**: 98%
- **Rationale**: De facto standard, zero configuration
- **Note**: Used alongside ruff for maximum strictness

#### `pytest==8.0.0`
- **Purpose**: Testing framework
- **Health Score**: 99%
- **Rationale**: Most popular, extensive plugin ecosystem
- **Required Plugins**:
  - `pytest-cov` - Coverage reporting
  - `pytest-asyncio` - Async test support
  - `pytest-mock` - Enhanced mocking

#### `bandit==1.7.5`
- **Purpose**: Security vulnerability scanning
- **Health Score**: 92%
- **Rationale**: Identifies common security issues
- **Configuration**: High confidence only

#### `safety==3.0.0`
- **Purpose**: Dependency vulnerability scanning  
- **Health Score**: 90%
- **Rationale**: Checks dependencies against CVE database
- **Note**: Run in CI pipeline

#### `nox==2024.3.2`
- **Purpose**: Task automation
- **Health Score**: 94%
- **Rationale**: Better than tox for our use case
- **Benefits**: Python-based configuration

### Testing Dependencies

#### `hypothesis==6.100.0`
- **Purpose**: Property-based testing
- **Health Score**: 96%
- **Rationale**: Required by CLAUDE.md for complex validation
- **Use Case**: Testing input sanitization

#### `pytest-cov==5.0.0`
- **Purpose**: Coverage reporting
- **Health Score**: 95%
- **Rationale**: Integrates with pytest
- **Requirement**: 90% coverage minimum

### Utility Dependencies

#### `python-dotenv==1.0.0`
- **Purpose**: Environment variable management
- **Health Score**: 93%
- **Rationale**: Simple, no dependencies
- **Use**: Load .env files

#### `pre-commit==3.7.0`
- **Purpose**: Git hook framework
- **Health Score**: 97%
- **Rationale**: Enforces standards before commit
- **Configuration**: See `.pre-commit-config.yaml`

## ❌ Rejected Dependencies

### `flask`
- **Rejected For**: FastAPI
- **Reason**: Less modern, fewer built-in features
- **Date**: 2025-07-01

### `unittest`
- **Rejected For**: pytest
- **Reason**: Less flexible, verbose syntax
- **Date**: 2025-07-01

### `pylint`
- **Rejected For**: ruff
- **Reason**: Slower, more configuration needed
- **Date**: 2025-07-01

## ⚠️ Dependencies Requiring Approval

### Large Dependencies (>10MB)

Currently none. Any future additions require:
1. Justification document
2. Performance impact analysis
3. Alternative evaluation
4. Tech lead approval

### Dependencies with Security History

Currently none. Any additions require:
1. Security audit
2. Mitigation plan
3. Security officer approval
4. Monitoring strategy

## 🔄 Dependency Update Policy

### Security Updates
- **Critical**: Within 24 hours
- **High**: Within 1 week
- **Medium**: Within 1 month
- **Low**: Next release cycle

### Feature Updates
- **Major versions**: Quarterly evaluation
- **Minor versions**: Monthly
- **Patch versions**: Automated PR

### Update Process
1. Check health scores
2. Review changelog
3. Test in isolation
4. Update across codebase
5. Full test suite
6. Update this document

## 📊 Health Score Exceptions

### No Current Exceptions

Any future exceptions must document:
- Dependency name and version
- Current health score
- Reason for exception
- Mitigation plan
- Review date
- Approval signatures

## 🔍 Dependency Auditing

### Monthly Audit Checklist
- [ ] Run `safety check`
- [ ] Check PyPI health scores
- [ ] Review dependency updates
- [ ] Update this document
- [ ] File update tasks in TASK.md

### Audit Tools
```bash
# Security audit
safety check
bandit -r src/

# Dependency analysis
pip list --outdated
pip-audit

# License check
pip-licenses
```

## 📝 Decision History

### 2025-07-07
- Documented initial dependency decisions
- Identified ruff version security issue
- Established approval process

### 2025-07-06
- Selected core development tools
- Defined health score requirements
- Created update policy

---

> **Note**: This document must be updated whenever dependencies change. All exceptions require documented approval.