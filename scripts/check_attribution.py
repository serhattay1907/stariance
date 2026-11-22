#!/usr/bin/env python3
"""Fail when commits or tracked files carry AI tool attribution.

The repository's rule (AGENTS.md): no AI attribution in commits, PRs, docs or code.
Naming a technology is fine ("Claude API" in a stack); crediting a tool as an author is not.

    python scripts/check_attribution.py --commits origin/main..HEAD   # commit messages
    python scripts/check_attribution.py --files                       # tracked files
    python scripts/check_attribution.py --message .git/COMMIT_EDITMSG # commit-msg hook

Standard library only, so CI and git hooks can run it without installing anything.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TOOLS = r"(claude|anthropic|chatgpt|openai|copilot|gemini|cursor|codeium|windsurf|devin|aider)"
PATTERNS = [
    re.compile(rf"co-authored-by:[^\n]*{TOOLS}", re.I),
    re.compile(r"generated (with|by) \[?(claude|chatgpt|copilot|gemini|cursor|an? ai\b)", re.I),
    re.compile(r"🤖\s*generated", re.I),
    re.compile(r"noreply@anthropic\.com", re.I),
    re.compile(r"claude\.ai/code/session", re.I),
    re.compile(r"^claude-session:", re.I | re.M),
    re.compile(r"(written|authored|opened) by (claude|chatgpt|copilot|gemini)\b", re.I),
]
# This checker and its test describe the patterns, so they are not scanned.
SKIP = {"scripts/check_attribution.py", "scripts/test_check_attribution.py"}
TEXT = {".md", ".py", ".ts", ".tsx", ".js", ".json", ".toml", ".yml", ".yaml", ".txt", ".cfg", ".ini", ""}


def find(text: str) -> list[str]:
    return [m.group(0).strip() for p in PATTERNS for m in p.finditer(text)]


def check_commits(rev_range: str) -> list[str]:
    out = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x01", rev_range], capture_output=True, text=True, check=True
    ).stdout
    problems = []
    for entry in filter(None, (e.strip() for e in out.split("\x01"))):
        sha, _, body = entry.partition("\x00")
        problems += [f"commit {sha[:9]}: {hit}" for hit in find(body)]
    return problems


def check_files(root: Path) -> list[str]:
    names = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
    problems = []
    for name in names.splitlines():
        path = root / name
        if name in SKIP or path.suffix not in TEXT or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        problems += [f"{name}: {hit}" for hit in find(text)]
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", metavar="RANGE", help="git revision range, e.g. origin/main..HEAD")
    parser.add_argument("--files", action="store_true", help="scan tracked text files")
    parser.add_argument("--message", type=Path, help="a commit message file (commit-msg hook)")
    args = parser.parse_args()
    problems: list[str] = []
    if args.commits:
        problems += check_commits(args.commits)
    if args.files:
        problems += check_files(Path.cwd())
    if args.message:
        problems += [f"commit message: {hit}" for hit in find(args.message.read_text(encoding="utf-8"))]
    for p in problems:
        print(f"AI attribution: {p}", file=sys.stderr)
    if problems:
        print("Remove the attribution lines (see AGENTS.md, Workflow).", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
