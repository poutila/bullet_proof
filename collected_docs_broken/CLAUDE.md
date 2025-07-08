# 🛡️ Bulletproof CLAUDE Development Guidelines

## 📚 Related Documentation
- **Project Overview**: [README.md](./README.md) - Quick start and project introduction
- **Current Tasks**: [TASK.md](./planning/TASK.md) - Sprint tasks and priorities
- **Architecture**: [PLANNING.md](./planning/PLANNING.md) - System design and phases
- **Terminology**: [GLOSSARY.md](./GLOSSARY.md) - Project-specific terms
- **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md) - How to contribute
- **Version History**: [CHANGELOG.md](./CHANGELOG.md) - Release notes

## 🔒 CRITICAL - Security & Data Integrity (Zero Tolerance)

### Security Fundamentals
- **NEVER commit secrets, API keys, passwords, or sensitive data** to version control
- **NEVER log sensitive information** (passwords, tokens, PII, financial data)
- **Always validate and sanitize ALL inputs** at API boundaries and before database operations
- **Use environment variables for ALL configuration** including secrets, endpoints, and feature flags
- **Implement rate limiting** for all public APIs (default: 100 requests/minute per IP)
- **Use HTTPS only** - reject HTTP connections in production
- **Implement proper authentication and authorization** for all protected endpoints
- **Escape user input** before rendering in templates or responses
- **Use parameterized queries** - never concatenate user input into SQL
- **SECRET DETECTION**: Use `gitleaks` or `truffleHog` in pre-push hooks and CI to catch secrets
- **OWASP ASVS LEVEL 2 COMPLIANCE** required for all applications
- **JWT SECURITY**: Maximum 15-minute access token lifetime, 7-day refresh token max, mandatory rotation
- **SECURITY LOGGING**: All failed auth, suspicious input, and privilege escalations must be logged with IP and timestamp
- **PII REDACTION**: All logs must redact/mask PII (email, phone, etc.). Use log scrubber middleware

### Data Protection
- **Encrypt sensitive data at rest** using industry-standard encryption
- **Use secure session management** with proper expiration and invalidation
- **Implement CSRF protection** for state-changing operations
- **Add security headers** (HSTS, CSP, X-Frame-Options, etc.)
- **Regularly audit dependencies** for known vulnerabilities using `safety`
- **Run security scans** with `bandit` before every commit

## 🚨 HIGH PRIORITY - Reliability & Resilience

### Error Handling (Mandatory)
- **Always implement proper exception handling** with specific exception types (never bare `except:`)
- **Use context managers** for ALL resource management (files, DB connections, network calls)
- **Fail fast principle** - validate inputs at function entry points
- **Log ALL errors** with appropriate levels and include context (user ID, request ID, stack trace)
- **Implement graceful degradation** for non-critical service failures
- **Use circuit breakers** for external service calls
- **Set timeouts** for ALL external requests (default: 30 seconds)
- **Implement retry logic** with exponential backoff for transient failures

```python
# Example error handling pattern
def process_data(data: Dict[str, Any]) -> ProcessedData:
    """Process user data with proper error handling."""
    try:
        # Validate inputs first
        if not data or 'required_field' not in data:
            raise ValueError("Missing required field")
        
        # Process with timeout
        with timeout_context(30):
            result = external_service.process(data)
        
        return ProcessedData(**result)
    
    except ValidationError as e:
        logger.error(f"Validation failed: {e}", extra={'data': data})
        raise ProcessingError("Invalid input data") from e
    
    except TimeoutError as e:
        logger.error(f"Service timeout: {e}", extra={'service': 'external_service'})
        raise ProcessingError("Service temporarily unavailable") from e
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", extra={'data': data}, exc_info=True)
        raise ProcessingError("Internal processing error") from e
```

### Testing Requirements

#### 🚨 MANDATORY TEST CREATION CHECKLIST
**BEFORE ANY CODE IS CONSIDERED COMPLETE:**

- [ ] **Test file exists** for EVERY Python file (except `__init__.py`)
- [ ] **Test file naming**: `test_<module_name>.py` in same directory or `tests/` 
- [ ] **Minimum test requirements per file:**
  - [ ] 1+ happy path test
  - [ ] 2+ edge case tests  
  - [ ] 1+ failure scenario test
  - [ ] 1+ integration test (if applicable)
- [ ] **Coverage verification**: `pytest --cov=. --cov-fail-under=90`
- [ ] **Test naming follows convention**: `test_<method>_<condition>_<expected_result>`

**ENFORCEMENT:** CI/CD pipeline MUST reject any PR with Python files lacking corresponding tests.

#### Test-First Development (Mandatory)
- **Write tests BEFORE or ALONGSIDE code** - never after
- **No Python file merges without tests** - zero exceptions
- **Test coverage reports required** in all PRs
- **Mutation testing required** for business logic modules

#### Comprehensive Testing Standards
- **MANDATORY 90% CODE COVERAGE** using `pytest-cov` - CI fails below this threshold
- **Always create Pytest unit tests** for new features with minimum requirements:
  - 1 happy path test
  - 2+ edge cases
  - 1+ failure scenario
  - 1 integration test (if applicable)
- **TEST NAMING CONVENTION**: Use `test_<method>_<condition>_<expected_result>` format for clarity:
  ```python
  def test_calculate_risk_score_valid_input_returns_float()
  def test_calculate_risk_score_missing_data_raises_validation_error()
  def test_calculate_risk_score_extreme_volatility_caps_at_one()
  ```
- **TEST CLASS STRUCTURE**: Use `TestClassName` for related test groups, flat `test_function_name` for simple cases
- **REGRESSION TESTS MANDATORY** for all bugfix PRs - include test that reproduces the original bug
- **MUTATION TESTING**: Use `mutmut` for critical business logic modules (payment, auth, risk calculation)
- **Mock ALL external dependencies** in unit tests
- **Use fixtures** for test data setup
- **Test error conditions explicitly** - don't just test success paths
- **Run tests in CI/CD pipeline** - no commits without passing tests
- **Use property-based testing** (Hypothesis) for complex data validation
- **Performance tests** for critical paths (response time < 200ms for APIs)

## 📊 CODE QUALITY - Structure & Maintainability

### SOLID Design Principles (Required for All Architecture)
> Use these principles when designing classes, services, interfaces, and architecture boundaries. All code should reflect SOLID unless a tradeoff is explicitly documented in an ADR.

#### S – Single Responsibility Principle (SRP)
**A class/module should have one and only one reason to change.**
✅ Each class/function has **one purpose** | 🚫 Avoid mixing concerns (e.g., DB logic + business logic)

```python
# ❌ Violates SRP
class UserManager:
    def save_to_db(self, user): ...
    def send_welcome_email(self, user): ...

# ✅ Follows SRP
class UserRepository:
    def save(self, user): ...

class WelcomeEmailSender:
    def send(self, user): ...
```

#### O – Open/Closed Principle (OCP)
**Software entities should be open for extension, but closed for modification.**
✅ Extend via **subclasses, plugins, or composition** | 🚫 Don't modify core logic for new behavior

```python
# ✅ Extend without modifying
class DiscountStrategy:
    def apply(self, price: float) -> float: return price

class PercentageDiscount(DiscountStrategy):
    def apply(self, price: float) -> float: return price * 0.9
```

#### L – Liskov Substitution Principle (LSP)
**Subtypes must be substitutable for their base types.**
✅ Subclasses must respect parent's interface and behavior | 🚫 Don't override with incompatible behavior

#### I – Interface Segregation Principle (ISP)
**Clients should not be forced to depend on methods they do not use.**
✅ Interfaces/schemas should be **focused and minimal** | 🚫 Don't create large, multipurpose interfaces

#### D – Dependency Inversion Principle (DIP)
**High-level modules must not depend on low-level modules. Both depend on abstractions.**
✅ Use **interfaces and dependency injection** | 🚫 Don't hardwire low-level logic into high-level modules

```python
# ✅ Abstract dependency
from typing import Protocol

class NotificationService(Protocol):
    def send(self, message: str) -> None: ...

class Notifier:
    def __init__(self, service: NotificationService):
        self.service = service
```

### Architecture & Structure (Strict)
- **NEVER create files longer than 500 lines** (including comments, excluding imports)
- **NEVER nest functions more than 3 levels deep**
- **NEVER create functions with more than 7 parameters** (use dataclasses/Pydantic models)
- **Cyclomatic complexity MUST be ≤ 10** per function (check with `radon`)
- **No circular imports** - design proper dependency hierarchy
- **No global variables** - use dependency injection or configuration objects
- **Single Responsibility Principle** - each function/class has ONE clear purpose

### Module Organization (Mandatory)
```
project/
├── src/
│   ├── domain/         # Core business logic (DDD entities, value objects)
│   ├── services/       # Application services (orchestration layer)
│   ├── api/            # API routes and schemas
│   ├── database/       # Database models and migrations
│   ├── events/         # Event handlers and pub-sub logic
│   ├── utils/          # Utility functions
│   └── config/         # Configuration management
├── tests/              # Mirror src/ structure
├── docs/               # Documentation + architecture diagrams
└── scripts/            # Deployment and utility scripts
```

### Domain-Driven Design (Required for Complex Projects)
- **SEPARATE domain logic** from application services and infrastructure
- **Domain entities** should be pure business logic with no external dependencies
- **Services layer** orchestrates domain operations and external calls
- **Repository pattern** for data access abstraction
- **Event system**: Use `events/` directory for event handlers, follow pub-sub pattern

### Agent-Specific Structure
```
agents/
├── agent_name/
│   ├── agent.py        # Main agent class (< 200 lines)
│   ├── tools.py        # Tool implementations (< 300 lines)
│   ├── prompts.py      # System prompts and templates
│   ├── config.py       # Agent-specific configuration
│   └── __init__.py     # Public interface
```

### AI Agent Security & Standards
- **PROMPT INJECTION PROTECTION**: Sanitize all user inputs, use input validation schemas
- **TOOL METADATA CONTRACT**: All agent tools MUST use Pydantic models for input/output schemas
- **JAILBREAK PREVENTION**: Implement content filtering and output validation
- **TOOL SCHEMA EXAMPLE**:
  ```python
  class ToolInput(BaseModel):
      """Input schema for agent tool."""
      query: str = Field(..., max_length=1000, description="Search query")
      filters: Dict[str, Any] = Field(default_factory=dict)
  
  class ToolOutput(BaseModel):
      """Output schema for agent tool."""
      results: List[Dict[str, Any]]
      metadata: Dict[str, Any]
      success: bool
  ```

### Code Quality Rules
- **Use type hints for EVERYTHING** - functions, variables, class attributes
- **NO `# type: ignore`** - fix typing errors properly
- **NO `# noqa`** - fix linting errors properly  
- **NO `# fmt: off`** - fix formatting errors properly
- **NO commented-out code** - delete it or use version control
- **NO print statements** - use structured logging only
- **NO magic numbers** - define as named constants with clear purpose
- **NO hardcoded values** - use configuration, environment variables, or constants
- **NO duplicate code** - refactor into reusable functions (DRY principle)
- **NO unused imports, variables, or functions** - clean up immediately
- **FORBIDDEN PATTERNS** - CI will reject code containing:
  ```
  print(          # Use logging instead
  eval(           # Security risk
  exec(           # Security risk
  input(          # Use proper input validation
  __import__(     # Use standard imports
  ```

### Performance Requirements
- **Profile performance** for all critical paths using `cProfile`
- **Use async/await** for ALL I/O-bound operations (file, network, database)
- **Implement caching** for expensive computations and external API calls
- **Database queries MUST be optimized** - no N+1 queries, use proper indexing
- **Memory usage monitoring** - no memory leaks, clean up resources
- **Response time targets**: APIs < 200ms, background tasks < 5 minutes
- **Use connection pooling** for database and external service connections

## 🔧 DEVELOPMENT PROCESS - Workflow & Standards

### Git & Version Control (Enforced)
- **Conventional Commits format** required:
  ```
  type(scope): description
  
  feat(api): add user authentication endpoint
  fix(database): resolve connection pool exhaustion
  docs(readme): update installation instructions
  ```
- **Branch naming convention**: `type/scope-description` (e.g., `feat/user-auth`, `fix/database-connection`)
- **NO direct commits to main/master** - use pull requests only
- **Squash commits** before merging to maintain clean history
- **PRE-COMMIT FRAMEWORK REQUIRED** using `.pre-commit-config.yaml`:
  ```yaml
  repos:
    - repo: local
      hooks:
        - id: mypy
        - id: ruff-check
        - id: ruff-format
        - id: black  # Additional strictness for formatting
        - id: pytest
        - id: bandit
        - id: safety
        - id: gitleaks
  ```
- **TASK RUNNER STANDARD**: Use `nox` for standardized test/lint/format chains:
  ```python
  # noxfile.py
  @nox.session
  def tests(session):
      session.run("pytest", "--cov=src", "--cov-report=term-missing")
  
  @nox.session  
  def lint(session):
      session.run("ruff", "check", "src/")
      session.run("mypy", "src/")
      session.run("bandit", "-r", "src/")
  ```
- **TOOL VERSION LOCKING**: All tools must have exact versions in `requirements-dev.txt`
  ```
  mypy==1.10.0
  ruff==0.4.0
  black==24.0.0
  pytest==8.0.0
  bandit==1.7.5
  nox==2024.3.2
  ```

### Documentation Requirements
- **README.md MUST include**:
  - Quick start guide (< 5 minutes to run locally)
  - API documentation links
  - Environment variables list
  - Troubleshooting section
  - Contributing guidelines
- **LICENSE file REQUIRED** with clear open/closed source policy
- **CONTRIBUTING.md MANDATORY** even for internal projects - include:
  - Code review process
  - Branch naming conventions
  - Issue reporting guidelines
  - Security vulnerability reporting process
- **ARCHITECTURE DOCUMENTATION REQUIRED**:
  - `docs/architecture/README.md` with system overview, data flow, external services
  - `docs/architecture/*.png` or diagrams showing component relationships
- **CHANGELOG.md MANDATORY** following [Keep a Changelog](https://keepachangelog.com/) format
- **Function docstrings MANDATORY** using Google style:
  ```python
  def calculate_risk_score(user_data: UserData, market_conditions: MarketData) -> RiskScore:
      """Calculate risk score for investment decision.
      
      Uses proprietary algorithm combining user profile with current market
      conditions to generate risk assessment.
      
      Args:
          user_data: User profile including investment history and preferences
          market_conditions: Current market volatility and trend data
          
      Returns:
          Risk score between 0.0 (low risk) and 1.0 (high risk)
          
      Raises:
          ValidationError: If user_data is incomplete or invalid
          MarketDataError: If market_conditions are stale or unavailable
          
      Example:
          >>> user = UserData(age=35, income=75000, risk_tolerance='moderate')
          >>> market = MarketData(volatility=0.15, trend='bullish')
          >>> score = calculate_risk_score(user, market)
          >>> print(f"Risk score: {score.value}")
          Risk score: 0.45
      """
  ```
- **API documentation** auto-generated from OpenAPI/FastAPI schemas
- **Architecture Decision Records (ADRs)** for major design choices

### Monitoring & Observability (Required)
- **Structured logging** using JSON format with correlation IDs
- **Log levels properly used**:
  - DEBUG: Detailed diagnostic info
  - INFO: General application flow
  - WARNING: Potentially harmful situations
  - ERROR: Error conditions that don't stop execution
  - CRITICAL: Serious errors that may cause termination
- **Health check endpoints** for all services (`/health`, `/ready`)
- **Metrics collection** for business KPIs and system performance
- **Request tracing** with unique request IDs in logs and responses
- **Performance monitoring** with alerts for SLA violations
- **BACKGROUND WORKERS** (e.g. Celery, RQ) must have:
  - Retry policies with exponential backoff
  - Crash monitoring and alerting
  - Separate logging with correlation IDs
  - Dead letter queues for failed jobs

### Environment Management
- **Use python-dotenv and load_dotenv()** for environment configuration
- **Environment-specific configs** (.env.development, .env.production)
- **Docker support** with multi-stage builds for production optimization

#### **Local Development Environment (Recommended)**
- **uv (Ultra-fast Python Package Manager)**:
  - **Installation**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - **Create Environment**: `uv venv venv_local`
  - **Activate**: `source venv_local/bin/activate` or `uv shell`
  - **Install Dependencies**: `uv pip install -r requirements-dev.txt`
  - **Benefits**: 10-100x faster than pip, automatic Python version management

#### **Production/CI Environment (Standard)**
- **pip (Traditional Package Manager)**:
  - **Virtual environment isolation** - use `python -m venv venv` for CI/production
  - **Use Cases**: Docker containers, CI/CD pipelines, production deployments

- **Dependency management**:
  - `requirements.txt` for production dependencies
  - `requirements-dev.txt` for development tools with EXACT versions
  - `pyproject.toml` for build configuration and uv settings
  - **Local Development**: Use `uv pip install -r requirements-dev.txt` for faster installs
  - **Production**: Use `pip install -r requirements.txt` (containers/CI)
  - Use version ranges for prod, exact pins for dev tools
- **DEPENDENCY HEALTH REQUIREMENTS**:
  - All dependencies MUST have >90% PyPI health score
  - No dependencies abandoned for >2 years
  - Security audit required for dependencies with known CVEs
  - Document rationale for any exceptions in `docs/dependency-decisions.md`
- **THIRD-PARTY LIBRARY POLICY**: Prior approval required for new dependencies > 10MB or with security history
- **ALLOWED FILE EXTENSIONS IN SRC/**: Only `.py` files allowed - NO `.ipynb`, `.txt`, `.bak`, `.tmp`

## 📋 PROJECT MANAGEMENT - Task & Context Awareness

### Mandatory Project Files
- **ALWAYS read `PLANNING.md`** at conversation start for context
- **CHECK `TASK.md`** before starting work:
  - If task exists: follow specifications exactly
  - If task missing: add with description, acceptance criteria, and date
  - Mark completed tasks immediately with completion date
- **UPDATE documentation** when features change

### Task Management
- **Break large tasks** into sub-tasks (< 4 hours each)
- **Add discovered tasks** to `TASK.md` under "Discovered During Work"
- **Include acceptance criteria** for each task
- **Estimate effort** (Small/Medium/Large) for planning
- **Track dependencies** between tasks

## 🧠 AI BEHAVIOR RULES - Development Assistant Guidelines

### Code Generation Standards
- **NEVER hallucinate libraries** - only use verified, existing packages
- **ALWAYS verify file paths** and module names before referencing
- **ASK for clarification** when requirements are ambiguous
- **PROVIDE examples** when suggesting new patterns or libraries
- **EXPLAIN reasoning** for architectural decisions
- **CONSIDER alternatives** and mention trade-offs

### AI Code Generation Test Requirements
- **AI MUST create test files** when generating Python modules
- **AI MUST verify test coverage** before marking tasks complete  
- **AI MUST suggest test scenarios** for complex logic
- **AI assistants cannot claim completion** without corresponding tests

### Quality Assurance
- **RUN quality checks** after each code change using `nox`:
  ```bash
  # Standardized quality pipeline
  nox -s lint          # Type checking, linting, security
  nox -s tests         # Unit tests with coverage
  nox -s format        # Code formatting (ruff + black)
  nox -s security      # Security and vulnerability scans
  nox -s muttest       # Mutation testing for critical modules
  ```
- **VERIFY all imports** are available and correctly specified
- **TEST code examples** before providing them
- **VALIDATE against requirements** before marking tasks complete

### Communication Standards
- **Be explicit about assumptions** when generating code
- **Warn about potential issues** or limitations
- **Suggest improvements** to existing code when relevant
- **Reference specific files** when discussing project structure
- **Provide step-by-step instructions** for complex setup or deployment

---

## 🎯 QUICK CHECKLIST - Before Any Commit

- [ ] All tests pass with ≥90% coverage (`nox -s tests`)
- [ ] Type checking passes (`nox -s lint`)
- [ ] Code formatting applied (`nox -s format`)
- [ ] Security scan clean (`nox -s security`)
- [ ] No secrets detected (`gitleaks`)
- [ ] Complexity acceptable (`radon cc`)
- [ ] **SOLID principles followed** (SRP, OCP, LSP, ISP, DIP)
- [ ] No forbidden patterns in code
- [ ] Test naming follows `test_<method>_<condition>_<expected_result>` pattern
- [ ] Mutation tests pass for critical modules (`nox -s muttest`)
- [ ] All dependencies have >90% PyPI health score
- [ ] Documentation updated (including CHANGELOG.md)
- [ ] Architecture diagrams updated if needed
- [ ] Task marked complete in `TASK.md`
- [ ] Regression tests added for bug fixes
- [ ] Tool schemas use Pydantic models (for agents)
- [ ] Only .py files in src/ directory

## 🚩 RED FLAGS - Stop Work Immediately

### BLOCKING CONDITIONS - Work Cannot Proceed
- **Python file without corresponding test file**
- **Test coverage below 90% threshold**
- **Tests not following naming conventions**
- **Missing edge case or failure scenario tests**
- **Integration tests absent for complex modules**

### Critical System Issues
- **Any security vulnerability** detected
- **Tests failing** in critical business logic
- **Memory leaks** or performance degradation
- **Circular imports** or architectural violations
- **Hardcoded secrets** or configuration
- **Missing error handling** in production code
- **Uncaught exceptions** reaching users
- **Data integrity issues** or potential corruption

*These conditions trigger immediate work stoppage and remediation.*

*Remember: It's better to take time to do it right than to rush and create technical debt or security vulnerabilities.*

---

## 🆘 EMERGENCY RESPONSE PROTOCOL

When critical failures occur (security breach, data corruption, production outage):

### Immediate Response (< 15 minutes)
- [ ] **Escalate to engineering lead** and document incident start time
- [ ] **Assess impact scope** - users affected, data at risk, security implications
- [ ] **Contain the issue** - isolate affected systems, disable problematic features
- [ ] **Rotate any exposed secrets** immediately (API keys, database passwords, tokens)

### Short-term Response (< 2 hours)
- [ ] **Roll back production** if incident affects user data or security
- [ ] **Implement temporary mitigation** if rollback isn't possible
- [ ] **Communicate status** to stakeholders and affected users
- [ ] **Preserve evidence** - logs, database states, system snapshots

### Recovery & Learning (< 48 hours)
- [ ] **Write incident postmortem** in `docs/incidents/YYYY-MM-DD-incident-name.md`
- [ ] **Root cause analysis** with timeline of events
- [ ] **Action items** with owners and deadlines to prevent recurrence
- [ ] **Update monitoring/alerting** based on lessons learned
- [ ] **Security review** if incident involved data or access compromise

### Postmortem Template
```markdown
# Incident: [Title] - [Date]

## Summary
Brief description of what happened and impact.

## Timeline
- HH:MM - Initial detection
- HH:MM - Engineering team alerted
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

## Root Cause
What actually caused the issue.

## Impact
- Users affected: X
- Data compromised: Yes/No
- Downtime: X minutes
- Revenue impact: $X

## Action Items
- [ ] [Action] - [Owner] - [Deadline]
- [ ] [Action] - [Owner] - [Deadline]

## Lessons Learned
What we learned and how we'll prevent this in the future.
```
See [MISSING.md](MISSING.md) for more info.
