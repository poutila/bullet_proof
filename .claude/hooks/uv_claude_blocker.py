#!/usr/bin/env python3
import json
import sys
import re

# Read input
try:
    input_data = json.load(sys.stdin)
except:
    sys.exit(1)

# Check if it's a Bash tool
if input_data.get("tool_name") != "Bash":
    sys.exit(0)

# Get the command
command = input_data.get("tool_input", {}).get("command", "")

# Block pip commands
if re.search(r'\bpip3?\b', command):
    print("pip is blocked. Claude: refactor this command to use uv instead.", file=sys.stderr)
    sys.exit(2)

# Allow other commands
sys.exit(0)