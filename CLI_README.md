# Bullet Proof CLI

A unified command-line interface for running all analysis and validation tools in the Bullet Proof project.

## Installation

The CLI is part of the main project. No additional installation needed.

## Usage

```bash
# Run from project root
python -m src.cli [command] [options]

# Or make it executable
chmod +x src/cli.py
./src/cli.py [command] [options]
```

## Commands

### 🎯 Demo
Quick demonstration of key features:
```bash
python -m src.cli demo
```

### 🔍 Compliance Check
Check CLAUDE.md compliance for Python files:
```bash
# Check all files in document_analyzer/
python -m src.cli compliance

# Check specific file
python -m src.cli compliance --file src/module.py

# Check different directory
python -m src.cli compliance --path /path/to/project
```

### 🔗 Reference Validation
Validate document cross-references:
```bash
# Enhanced mode (default)
python -m src.cli references

# Basic mode
python -m src.cli references --basic
```

### 🏗️ Structural Soundness
Check documentation structure:
```bash
python -m src.cli structure
```

### 📍 Instruction Tracing
Trace instruction paths through documentation:
```bash
python -m src.cli trace
```

### 🔄 Similarity Analysis
Analyze document similarity:
```bash
# String-based similarity (default)
python -m src.cli similarity

# Semantic similarity (requires models)
python -m src.cli similarity --semantic

# Custom threshold and filters
python -m src.cli similarity --threshold 0.8 --pattern "README" --limit 10
```

### 🔀 Document Merging
Find and merge similar documents:
```bash
# Dry run (default)
python -m src.cli merge --threshold 0.9

# Actually merge files
python -m src.cli merge --execute --output merged/

# Filter documents
python -m src.cli merge --pattern "requirements" --execute
```

### 🧪 Run All Checks
Execute all analysis tools:
```bash
python -m src.cli all
```

## Global Options

- `--path PATH, -p PATH`: Root directory to analyze (default: current directory)
- `--verbose, -v`: Enable verbose output
- `--help, -h`: Show help message

## Examples

### Complete Project Analysis
```bash
# Run all checks on current directory
python -m src.cli all

# Run all checks on specific project
python -m src.cli all --path ~/projects/myproject
```

### Find Duplicate Documentation
```bash
# Find very similar documents (90% threshold)
python -m src.cli similarity --threshold 0.9

# Find and merge duplicates
python -m src.cli merge --threshold 0.95 --execute
```

### Validate Specific Module
```bash
# Check compliance for a module
python -m src.cli compliance --file src/my_module.py

# Check with verbose output
python -m src.cli compliance --file src/my_module.py --verbose
```

### Analyze Project Documentation
```bash
# Check all documentation references
python -m src.cli references

# Check documentation structure
python -m src.cli structure

# Trace how instructions flow through docs
python -m src.cli trace
```

## Output

All commands provide:
- Clear status indicators (✅ ❌ ⚠️)
- Detailed issue reports
- Summary statistics
- Actionable recommendations

## Return Codes

- `0`: Success
- `1`: Error or issues found
- `2`: Invalid arguments

## Integration

The CLI can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Check CLAUDE.md Compliance
  run: python -m src.cli compliance

- name: Validate Documentation
  run: python -m src.cli references

- name: Run All Checks
  run: python -m src.cli all
```

## Development

To add new commands:
1. Add parser in `main()`
2. Create handler function
3. Add to `command_map`

The CLI uses Python's argparse for argument parsing and provides consistent output formatting across all commands.