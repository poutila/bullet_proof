# 🔀 Git Strategy and Workflow

> **Purpose**: Define Git workflow, branching strategy, and collaboration guidelines
> **Standards**: Follows [CLAUDE.md](../../CLAUDE.md) version control requirements

## 📚 Related Documentation
- **Contributing Guide**: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- **Development Standards**: [CLAUDE.md](../../CLAUDE.md)
- **Task Management**: [TASK.md](../../planning/TASK.md)

## 🌳 Branching Strategy

### Main Branches

#### `main`
- **Purpose**: Production-ready code
- **Protection**: Required reviews, passing tests
- **Deployment**: Automatic to production
- **Merge**: Only from release branches

#### `develop`
- **Purpose**: Integration branch
- **Protection**: Required reviews
- **Deployment**: Automatic to staging
- **Merge**: Feature branches merge here

### Supporting Branches

#### Feature Branches
- **Naming**: `feat/short-description`
- **Base**: `develop`
- **Lifetime**: Until feature complete
- **Example**: `feat/user-authentication`

#### Bugfix Branches
- **Naming**: `fix/issue-description`
- **Base**: `develop` (or `main` for hotfixes)
- **Lifetime**: Until fix merged
- **Example**: `fix/database-connection-timeout`

#### Release Branches
- **Naming**: `release/v1.2.3`
- **Base**: `develop`
- **Purpose**: Prepare for production
- **Example**: `release/v1.2.0`

#### Hotfix Branches
- **Naming**: `hotfix/critical-issue`
- **Base**: `main`
- **Purpose**: Emergency production fixes
- **Example**: `hotfix/security-vulnerability`

## 📝 Commit Standards

### Conventional Commits Format

```
type(scope): description

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/changes
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Maintenance tasks
- `revert`: Revert previous commit

### Examples

```bash
feat(auth): add JWT token validation
fix(database): resolve connection pool exhaustion
docs(readme): update installation instructions
test(api): add integration tests for user endpoints
```

### Commit Rules
1. **Atomic commits** - One logical change per commit
2. **Present tense** - "add" not "added"
3. **Imperative mood** - "fix" not "fixes"
4. **No period** at end of subject line
5. **Body explains** why, not what

## 🔄 Workflow

### 1. Start New Work

```bash
# Update local develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feat/new-feature

# Link to task
# Reference T-XXX from TASK.md in commits
```

### 2. Development

```bash
# Make changes
# Write tests first (TDD)
# Run quality checks
nox -s lint tests format

# Commit frequently
git add -p  # Stage selectively
git commit -m "feat(module): add new capability"
```

### 3. Stay Updated

```bash
# Regularly sync with develop
git checkout develop
git pull origin develop
git checkout feat/new-feature
git rebase develop

# Resolve conflicts carefully
# Re-run tests after rebase
```

### 4. Prepare for Review

```bash
# Clean up commit history
git rebase -i develop

# Squash related commits
# Ensure each commit is meaningful

# Final quality check
nox -s lint tests format security
```

### 5. Create Pull Request

```bash
# Push branch
git push origin feat/new-feature

# Create PR via GitHub
# Include:
# - Task reference (T-XXX)
# - Description of changes
# - Test results
# - Screenshots if UI changes
```

### 6. Code Review

#### Author Responsibilities
- Respond to feedback promptly
- Update per review comments
- Keep PR focused and small
- Ensure CI passes

#### Reviewer Responsibilities
- Review within 24 hours
- Check against CLAUDE.md standards
- Verify test coverage
- Consider security implications

### 7. Merge

```bash
# After approval
# Squash and merge to develop
# Delete feature branch

# Update TASK.md
# Mark task as complete
```

## 🚫 Git Don'ts

### Never Do These
1. **Force push** to shared branches
2. **Commit secrets** or credentials
3. **Commit generated files**
4. **Use `git add .`** blindly
5. **Merge without reviews**
6. **Commit broken code**
7. **Ignore test failures**

### Always Do These
1. **Pull before push**
2. **Review your changes** before commit
3. **Write meaningful commit messages**
4. **Keep commits atomic**
5. **Update documentation**
6. **Run tests locally**
7. **Use branch protection**

## 🏷️ Tagging Strategy

### Version Tags
```bash
# Format: v<major>.<minor>.<patch>
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

### Tag Types
- **Release tags**: `v1.2.3`
- **Pre-release**: `v1.2.3-rc.1`
- **Beta**: `v1.2.3-beta.1`
- **Hotfix**: `v1.2.4-hotfix.1`

## 🔧 Git Configuration

### Recommended Settings

```bash
# User settings
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Helpful aliases
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'

# Better diffs
git config --global diff.algorithm patience
git config --global merge.tool vimdiff

# Rebase by default
git config --global pull.rebase true
```

### Git Hooks

Pre-commit hooks are required:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: nox -s tests
        language: system
        pass_filenames: false
      
      - id: security
        name: Security scan
        entry: nox -s security
        language: system
        pass_filenames: false
```

## 📊 Git Best Practices

### Branch Hygiene
- Delete merged branches
- Keep branch names short
- Use descriptive names
- Regular cleanup

### Commit Hygiene
- Commit early and often
- But push clean history
- Use interactive rebase
- Sign commits if required

### Collaboration
- Communicate in PRs
- Use draft PRs for WIP
- Link issues and tasks
- Celebrate good code!

---

> **Remember**: Git history is documentation. Keep it clean and meaningful.