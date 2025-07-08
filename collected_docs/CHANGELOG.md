# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of docpipe package
- Core API with `analyze_project()` function and `DocPipe` class
- Compliance analyzer for Python code (CLAUDE.md standards)
- String-based similarity analyzer using rapidfuzz
- Semantic similarity analyzer using sentence-transformers (optional)
- Reference validator for markdown documents
- Comprehensive result models using Pydantic
- Multiple export formats (JSON, CSV, Excel, Markdown)
- Progress tracking support
- Feature detection for optional dependencies
- Command-line interface
- Comprehensive test suite
- User guide and API documentation

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Input validation for all user-provided paths
- No execution of arbitrary code
- Secure handling of file operations

## [0.1.0] - 2025-01-07

### Added
- Initial package structure
- Basic functionality for document analysis
- Support for Python 3.9+

[Unreleased]: https://github.com/username/docpipe/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/username/docpipe/releases/tag/v0.1.0