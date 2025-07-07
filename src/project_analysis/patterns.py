"""Pattern definitions for instruction path tracing."""

from typing import Final

# Instruction identification patterns
INSTRUCTION_PATTERNS: Final[list[str]] = [
    r"(?:must|should|need to|required to)\s+(\w+)",
    r"(?:create|implement|build|generate|write)\s+([^.]+)",
    r"(?:follow|use|see)\s+\[([^\]]+)\]\(([^)]+)\)",
    r"(?:run|execute)\s+`([^`]+)`",
    r"CI/CD.*(?:pipeline|workflow|action)",
    r"test.*(?:coverage|automation|framework)",
    r"(?:generates?|creates?|outputs?)\s*:?\s*([^.]+)",
]

# File generation patterns
FILE_GENERATION_PATTERNS: Final[list[str]] = [
    r"(?:create|generate|write)\s+(?:file|script)?\s*`([^`]+)`",
    r"(?:creates?|generates?)\s+([^\s]+\.(py|yml|yaml|md|json|toml|txt))",
    r"(?:output|result).*?([^\s]+\.(py|yml|yaml|md|json|toml|txt))",
    r"`([^`]+\.(py|yml|yaml|md|json|toml|txt))`",
]

# Coverage check terms
CI_CD_TERMS: Final[list[str]] = ["ci/cd", "github action", "workflow", "pipeline"]
TEST_TERMS: Final[list[str]] = ["pytest", "test automation", "coverage", "mutation test"]
ARCHITECTURE_TERMS: Final[list[str]] = ["architecture", "design", "component", "module"]

# File search paths
FILE_SEARCH_PATHS: Final[list[str]] = [
    "",
    "src/",
    "docs/",
    "planning/",
    ".github/",
    ".github/workflows/",
    "scripts/",
    "tests/",
]

# Common directory prefixes
COMMON_PREFIXES: Final[list[str]] = ["planning/", "docs/", ""]