#!/usr/bin/env python3
import json
import os
import subprocess
import sys

input_data = json.loads(sys.stdin.read())

try:
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True, timeout=2
    )
    if remote.returncode == 0:
        project = remote.stdout.strip().split("/")[-1].removesuffix(".git")
    else:
        project = os.path.basename(os.getcwd())
except Exception:
    project = os.path.basename(os.getcwd())

user = os.environ.get("USER", "unknown")

output = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "\n".join([
            f"Project: {project} | Recorded by: {user}",
            "",
            "RECORD: Evaluate if this conversation contains a significant engineering decision (architecture, stack selection, complexity tradeoff, environment config, project context/goals).",
            "If yes, record to ~/.claude/decisions/ using: python3 ~/.claude/frontier-brain/bin/decision-engine.py",
            'Test: would forgetting this hurt in 3 months? If trivial, skip silently.',
            'Confirm with one line: "Recorded #N: title"',
            "",
            "RECALL: If the user is evaluating alternatives or making an engineering choice, offer to search past decisions before proceeding.",
        ]),
    },
}

print(json.dumps(output))
