# 🔧 Troubleshooting Guide

> **Purpose**: Common issues, solutions, and debugging procedures
> **Audience**: Developers and operations team

## 📚 Related Documentation
- **Development Standards**: [CLAUDE.md](../CLAUDE.md)
- **Architecture**: [Architecture Overview](./architecture/README.md)
- **Deployment**: [Deployment Guide](./deployment/README.md)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

## 🚨 Quick Diagnostics

### System Health Check
```bash
# Check all services
./scripts/health_check.sh

# Verify dependencies
pip check
safety check

# Run tests
pytest --tb=short

# Check logs
tail -f logs/application.log
```

## 🐛 Common Issues

### 1. Import Errors

#### Symptom
```python
ImportError: No module named 'module_name'
```

#### Solutions
- Check virtual environment is activated
- Verify dependencies installed: `pip install -r requirements-dev.txt`
- Check PYTHONPATH: `echo $PYTHONPATH`
- Ensure __init__.py files exist in packages

### 2. Type Checking Failures

#### Symptom
```
mypy: error: Incompatible types
```

#### Solutions
- Run `mypy --install-types`
- Check for missing type hints
- Verify import statements
- NO `# type: ignore` - fix the actual issue

### 3. Test Coverage Below 90%

#### Symptom
```
FAIL Required test coverage of 90% not reached. Total coverage: 85.67%
```

#### Solutions
- Run coverage report: `pytest --cov-report=term-missing`
- Add tests for uncovered lines
- Focus on edge cases and error paths
- Check for unreachable code

### 4. Git Hook Failures

#### Symptom
```
pre-commit hook failed
```

#### Solutions
- Run checks manually: `nox -s lint tests format`
- Fix issues before committing
- Update hooks: `pre-commit install --install-hooks`
- Check hook configuration in `.pre-commit-config.yaml`

### 5. GitHub Actions Failures

#### Symptom
CI pipeline fails but local tests pass

#### Solutions
- Check environment differences
- Verify secrets are set correctly
- Review workflow logs in detail
- Ensure dependencies match exactly
- Check for timing/race conditions

## 🔍 Debugging Procedures

### 1. Debugging Failed Tests

```bash
# Run specific test with verbose output
pytest -vv path/to/test_file.py::test_function_name

# Show local variables on failure
pytest --showlocals

# Drop into debugger on failure
pytest --pdb

# Run with specific marker
pytest -m "not slow"
```

### 2. Debugging Import Issues

```python
# Check module search path
import sys
print(sys.path)

# Find where module is loaded from
import module_name
print(module_name.__file__)

# List all installed packages
pip list
```

### 3. Debugging Performance Issues

```python
# Profile code execution
import cProfile
cProfile.run('function_to_profile()')

# Time specific operations
import timeit
timeit.timeit('operation()', number=1000)

# Memory profiling
from memory_profiler import profile
@profile
def memory_intensive_function():
    pass
```

### 4. Debugging Async Issues

```python
# Enable asyncio debug mode
import asyncio
asyncio.set_debug(True)

# Check for pending tasks
pending = asyncio.all_tasks()
print(f"Pending tasks: {len(pending)}")

# Trace coroutines
import logging
logging.getLogger('asyncio').setLevel(logging.DEBUG)
```

## 🛠️ Environment Issues

### Virtual Environment Problems

```bash
# Recreate virtual environment
rm -rf venv_local
uv venv venv_local
source venv_local/bin/activate
uv pip install -r requirements-dev.txt

# Verify Python version
python --version  # Should be 3.11.9+
```

### Path Issues

```bash
# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# For permanent fix, add to .env
echo "PYTHONPATH=${PWD}" >> .env
```

### Permission Issues

```bash
# Fix file permissions
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type d -exec chmod 755 {} \;

# Fix script permissions
chmod +x scripts/*.py
```

## 📊 Performance Troubleshooting

### Slow Tests
- Use pytest markers to separate slow tests
- Profile test execution: `pytest --durations=10`
- Mock external dependencies
- Use fixtures efficiently
- Consider parallel execution: `pytest -n auto`

### High Memory Usage
- Check for memory leaks with tracemalloc
- Review large data structures
- Implement pagination for large datasets
- Use generators instead of lists
- Clear caches appropriately

### Database Performance
- Check query execution plans
- Add appropriate indexes
- Use connection pooling
- Implement query result caching
- Monitor slow query logs

## 🔐 Security Troubleshooting

### Security Scan Failures

```bash
# Run bandit with detailed output
bandit -r src/ -ll -f json

# Check specific security issues
safety check --json

# Audit dependencies
pip-audit
```

### Common Security Issues
- Hardcoded passwords → Use environment variables
- SQL injection → Use parameterized queries
- Path traversal → Validate and sanitize paths
- Weak crypto → Use approved algorithms
- Missing rate limiting → Implement throttling

## 📝 Logging and Monitoring

### Enable Debug Logging

```python
# In code
import logging
logging.basicConfig(level=logging.DEBUG)

# Via environment
export LOG_LEVEL=DEBUG
```

### Structured Logging

```python
import structlog
logger = structlog.get_logger()
logger.info("operation_complete", 
           user_id=123, 
           duration=0.456,
           status="success")
```

### Common Log Locations
- Application logs: `logs/app.log`
- Error logs: `logs/error.log`
- Access logs: `logs/access.log`
- Audit logs: `docs/audit/`

## 🚀 Recovery Procedures

### From Checkpoint
```bash
# List available checkpoints
ls backups/checkpoints/

# Restore from checkpoint
python scripts/restore_checkpoint.py <checkpoint-id>
```

### Database Recovery
```bash
# Backup before recovery
pg_dump database_name > backup_$(date +%Y%m%d).sql

# Restore from backup
psql database_name < backup_file.sql
```

## 💡 Best Practices

### Prevention
1. Always run tests before committing
2. Keep dependencies up to date
3. Monitor system resources
4. Regular security audits
5. Document unusual issues

### When Stuck
1. Check the logs first
2. Reproduce in isolation
3. Search error messages
4. Check recent changes
5. Ask for help early

## 📞 Getting Help

### Internal Resources
- Check this guide first
- Review [CLAUDE.md](../CLAUDE.md) for standards
- Search closed issues
- Check team documentation

### Escalation Path
1. Team chat channel
2. Tech lead
3. Architecture team
4. External support

---

> **Remember**: Every problem is an opportunity to improve our documentation and systems.