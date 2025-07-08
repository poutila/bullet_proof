# Test Coverage Report

Generated on: 2025-07-07 16:45:33

## Summary

- Total source files: 23
- Source files with tests: 13 (56.5%)
- Source files without tests: 10
- Total test files: 16
- Orphan test files: 2

## Coverage Assessment

⚠️ **Poor**: Test coverage is below 70% and needs improvement

## Source Files Without Tests

The following source files do not have corresponding test files:

- `src/cli.py`
- `src/document_analysis/merging.py`
- `src/document_analysis/similarity/base.py`
- `src/document_analysis/similarity/matrix_utils.py`
- `src/document_analysis/similarity/semantic_similarity.py`
- `src/project_analysis/coverage_analyzer.py`
- `src/project_analysis/document_parser.py`
- `src/project_analysis/instruction_node.py`
- `src/project_analysis/path_resolver.py`
- `src/project_analysis/report_generator.py`

## Orphan Test Files

The following test files do not have corresponding source files:

- `tests/conftest.py`
- `tests/test___init__.py`

## Source to Test Mapping

| Source File | Test File | Status |
|-------------|-----------|--------|
| `src/cli.py` | `**Missing**` | ❌ |
| `src/compliance/claude_compliance_checker.py` | `tests/compliance/test_claude_compliance_checker.py` | ✅ |
| `src/compliance/claude_compliance_checker_simple.py` | `tests/compliance/test_claude_compliance_checker_simple.py` | ✅ |
| `src/compliance/compliance_checks.py` | `tests/compliance/test_compliance_checks.py` | ✅ |
| `src/document_analysis/analyzers.py` | `tests/test_document_analysis/test_analyzers.py` | ✅ |
| `src/document_analysis/config.py` | `tests/test_document_analysis/test_config.py` | ✅ |
| `src/document_analysis/markdown_analyzer.py` | `tests/test_document_analysis/test_markdown_analyzer.py` | ✅ |
| `src/document_analysis/merging.py` | `**Missing**` | ❌ |
| `src/document_analysis/reference_validator.py` | `tests/test_document_analysis/test_reference_validator.py` | ✅ |
| `src/document_analysis/reports.py` | `tests/test_compliance/test_reports.py` | ✅ |
| `src/document_analysis/similarity/base.py` | `**Missing**` | ❌ |
| `src/document_analysis/similarity/matrix_utils.py` | `**Missing**` | ❌ |
| `src/document_analysis/similarity/semantic_similarity.py` | `**Missing**` | ❌ |
| `src/document_analysis/similarity/string_similarity.py` | `tests/document_analysis/similarity/test_string_similarity.py` | ✅ |
| `src/document_analysis/structural_soundness_checker.py` | `tests/test_document_analysis/test_structural_soundness_checker.py` | ✅ |
| `src/document_analysis/validation.py` | `tests/test_document_analysis/test_validation.py` | ✅ |
| `src/project_analysis/coverage_analyzer.py` | `**Missing**` | ❌ |
| `src/project_analysis/document_parser.py` | `**Missing**` | ❌ |
| `src/project_analysis/instruction_node.py` | `**Missing**` | ❌ |
| `src/project_analysis/instruction_path_tracer.py` | `tests/project_analysis/test_instruction_path_tracer.py` | ✅ |
| `src/project_analysis/path_resolver.py` | `**Missing**` | ❌ |
| `src/project_analysis/patterns.py` | `tests/test_project_analysis/test_patterns.py` | ✅ |
| `src/project_analysis/report_generator.py` | `**Missing**` | ❌ |

## Test to Source Mapping

| Test File | Source File |
|-----------|-------------|
| `tests/compliance/test_claude_compliance_checker.py` | `src/compliance/claude_compliance_checker.py` |
| `tests/compliance/test_claude_compliance_checker_simple.py` | `src/compliance/claude_compliance_checker_simple.py` |
| `tests/compliance/test_compliance_checks.py` | `src/compliance/compliance_checks.py` |
| `tests/document_analysis/similarity/test_string_similarity.py` | `src/document_analysis/similarity/string_similarity.py` |
| `tests/project_analysis/test_instruction_path_tracer.py` | `src/project_analysis/instruction_path_tracer.py` |
| `tests/test_compliance/test_compliance_checks.py` | `src/compliance/compliance_checks.py` |
| `tests/test_compliance/test_reports.py` | `src/document_analysis/reports.py` |
| `tests/test_document_analysis/test_analyzers.py` | `src/document_analysis/analyzers.py` |
| `tests/test_document_analysis/test_config.py` | `src/document_analysis/config.py` |
| `tests/test_document_analysis/test_markdown_analyzer.py` | `src/document_analysis/markdown_analyzer.py` |
| `tests/test_document_analysis/test_reference_validator.py` | `src/document_analysis/reference_validator.py` |
| `tests/test_document_analysis/test_structural_soundness_checker.py` | `src/document_analysis/structural_soundness_checker.py` |
| `tests/test_document_analysis/test_validation.py` | `src/document_analysis/validation.py` |
| `tests/test_project_analysis/test_patterns.py` | `src/project_analysis/patterns.py` |
