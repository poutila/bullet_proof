# 📦 PACKAGE_TODO.md - Docpipe Package Refactoring Tasks

## 🎯 Goal
Transform the current codebase into a reusable Python package called 'docpipe' for analyzing AI coding instructions in markdown documentation.

## 📋 Task List

### Phase 1: Package Structure Setup ✅
- [x] Create new package directory structure
  - [x] Create `docpipe/` root directory
  - [x] Create `docpipe/__init__.py` with main exports
  - [x] Create `docpipe/__version__.py` with version info
  - [x] Create `docpipe/api.py` for high-level functions
  - [x] Create subdirectories: `core/`, `analyzers/`, `models/`, `utils/`, `cli/`
- [x] Create `pyproject.toml` with proper metadata
  - [x] Define package metadata (name, version, description, author)
  - [x] Specify dependencies (required and optional)
  - [x] Configure build system
  - [x] Add entry points for CLI
- [x] Create package documentation structure
  - [x] Create `README.md` with package overview
  - [x] Create `docs/` directory for detailed documentation
  - [x] Create `examples/` directory with usage examples

### Phase 2: Create Unified Models ✅
- [x] Design and implement Pydantic models
  - [x] Create `models/__init__.py`
  - [x] Create `models/results.py` with AnalysisResults model
  - [x] Create `models/issues.py` with Issue and Feedback models
  - [x] Create `models/config.py` with AnalysisConfig model
  - [x] Create models for each analyzer's results
    - [x] ComplianceResults
    - [x] ReferenceResults
    - [x] SimilarityResults
    - [x] InstructionResults
- [x] Create enums and constants
  - [x] Severity levels
  - [x] Analysis types
  - [x] Export formats

### Phase 3: Implement Core API ✅
- [x] Create main API entry point
  - [x] Implement `analyze_project()` function
  - [x] Add configuration handling
  - [x] Add progress callback support
- [x] Create DocPipe class
  - [x] Implement `__init__` with configuration
  - [x] Implement `analyze()` method
  - [x] Add individual analysis methods
  - [x] Add result aggregation logic
- [x] Create analyzer orchestration
  - [x] Implement analyzer discovery
  - [x] Add parallel execution support (placeholder)
  - [x] Handle analyzer dependencies

### Phase 4: Refactor Analyzers ✅
- [x] Create base analyzer interface
  - [x] Define BaseAnalyzer protocol
  - [x] Create AnalyzerResult base class
  - [x] Add analyzer registration system
- [x] Refactor compliance analyzer
  - [x] Move from `src/compliance/` to `docpipe/analyzers/compliance/`
  - [x] Implement BaseAnalyzer interface
  - [x] Update to use new models
  - [x] Add configuration support
- [x] Refactor document analyzers
  - [x] Create reference validator
  - [ ] Move structural soundness checker (deferred)
  - [x] Create similarity analyzers (string and semantic)
  - [x] Update to use unified interface
- [ ] Refactor project analyzer (deferred - needs more analysis)
  - [ ] Move instruction path tracer
  - [ ] Implement new interface
  - [ ] Add configuration support
- [x] Create analyzer factory
  - [x] Implement plugin loading (via create_similarity_analyzer)
  - [x] Add analyzer validation
  - [ ] Support custom analyzers (future enhancement)

### Phase 5: Simplify Dependencies ✅
- [x] Make heavy dependencies optional
  - [x] Create feature detection for sentence-transformers
  - [x] Add fallback for semantic similarity
  - [x] Make pandas optional for exports
  - [x] Create lightweight alternatives
- [x] Implement feature flags
  - [x] Add FEATURES dictionary
  - [x] Create feature checking utilities
  - [x] Add warnings for missing features
- [x] Optimize imports
  - [x] Use lazy imports for optional deps
  - [x] Minimize startup time
  - [x] Add import error handling

### Phase 6: Testing & Documentation ✅
- [x] Create test structure
  - [x] Mirror package structure in tests/
  - [x] Create test fixtures and utilities
  - [x] Add integration test framework
- [x] Write unit tests
  - [x] Test each analyzer (90% coverage minimum)
  - [x] Test API functions
  - [x] Test models and validation
  - [x] Test error handling
- [x] Write integration tests
  - [x] Test full pipeline execution
  - [x] Test with sample projects
  - [x] Test configuration handling
  - [ ] Test plugin system (future enhancement)
- [x] Create documentation
  - [x] Write API reference (docstrings)
  - [x] Create user guide
  - [ ] Write migration guide (deferred)
  - [ ] Add architecture documentation (deferred)
- [x] Create examples
  - [x] Basic usage example
  - [x] Advanced configuration example
  - [ ] Custom analyzer example (future)
  - [x] CI/CD integration example

### Phase 7: Package Distribution 🚀
- [ ] Prepare for distribution
  - [ ] Create MANIFEST.in
  - [ ] Add LICENSE file
  - [ ] Create CONTRIBUTING.md
  - [ ] Add CHANGELOG.md
- [ ] Set up CI/CD
  - [ ] Create GitHub Actions workflow
  - [ ] Add test automation
  - [ ] Configure coverage reporting
  - [ ] Set up PyPI deployment
- [ ] Create release process
  - [ ] Version bumping strategy
  - [ ] Release notes template
  - [ ] Distribution testing
- [ ] Publish package
  - [ ] Test on Test PyPI
  - [ ] Publish to PyPI
  - [ ] Create GitHub release
  - [ ] Announce release

## 🎯 Success Criteria
- [ ] Package installable via `pip install docpipe`
- [ ] Simple API: `results = analyze_project("/path")`
- [ ] All existing functionality preserved
- [ ] 90%+ test coverage
- [ ] Full type hints
- [ ] Comprehensive documentation
- [ ] Clean separation of concerns
- [ ] Extensible plugin system

## 📝 Notes
- Maintain backward compatibility where possible
- Follow CLAUDE.md guidelines throughout
- Create tests alongside implementation
- Document decisions in ADRs as needed

## 🔄 Progress Tracking
- Created: 2025-01-07
- Phase 1: ✅ Completed
- Phase 2: ✅ Completed
- Phase 3: ✅ Completed
- Phase 4: ✅ Completed
- Phase 5: ✅ Completed
- Phase 6: ✅ Completed
- Phase 7: 📋 Planned

---
Last Updated: 2025-01-07

## 🔄 Current State (Phase 4 In Progress)

### Completed Actions:
1. ✅ Renamed `ml` to `nlp` in optional dependencies (pyproject.toml and README.md)
2. ✅ Analyzed document_analysis module structure:
   - String similarity uses rapidfuzz (lightweight)
   - Semantic similarity uses sentence-transformers (heavy, should be optional)
   - Good separation with Protocol pattern and base classes
   - pandas is heavily used but could be made optional
3. ✅ Analyzed compliance module structure:
   - Uses ONLY standard library (ast, re, pathlib, etc.)
   - No external dependencies - excellent for portability
   - Well-structured with separated check functions
   - Ready for direct refactoring

### Next Steps for Phase 4:
1. Create base analyzer interface in docpipe/analyzers/base.py
2. Refactor compliance analyzer (easiest - no external deps)
3. Refactor document analyzers with NLP features optional
4. Refactor project analyzer (instruction tracer)
5. Ensure all NLP features have string-based fallbacks

### Key Design Decisions:
- Keep sentence-transformers strictly optional under [nlp] extra
- Provide string-based fallbacks for all semantic features
- Make pandas optional under [data] extra where possible
- Maintain clean separation between core and optional features

### Completed in Phase 4-5:
1. ✅ Created base analyzer interface with Protocol pattern
2. ✅ Refactored compliance analyzer (no external dependencies)
3. ✅ Created similarity analyzers with optional NLP support:
   - StringSimilarityAnalyzer (uses rapidfuzz)
   - SemanticSimilarityAnalyzer (optional, requires [nlp])
   - CombinedSimilarityAnalyzer (uses both methods)
4. ✅ Created reference validator for markdown links
5. ✅ Implemented feature detection and graceful fallbacks
6. ✅ Updated engine to use actual analyzers
7. ✅ All NLP features are strictly optional with string fallbacks

### Ready for Installation:
The package structure is complete and ready for:
- `pip install -e .` for development
- `pip install -e .[nlp]` for semantic similarity
- `pip install -e .[data]` for pandas exports
- `pip install -e .[dev]` for development tools

### Completed in Phase 6:
1. ✅ Created comprehensive test structure with fixtures
2. ✅ Unit tests for:
   - Configuration models
   - Issue and feedback models
   - Compliance analyzer
   - Similarity analyzers (string and semantic)
   - Reference validator
3. ✅ Integration tests for:
   - Main API (analyze_project)
   - DocPipe class
   - Result exports
   - Edge cases and error handling
4. ✅ Documentation:
   - Comprehensive user guide
   - Complete API reference
   - Examples (basic and advanced)
5. ✅ Test runner script (run_tests.py)