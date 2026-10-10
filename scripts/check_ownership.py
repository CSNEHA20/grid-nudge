#!/usr/bin/env python3
"""Fail if the current branch touches files owned by the other person."""
import argparse
import fnmatch
import subprocess
import sys

# Ordered rules: first match wins. owner: "s", "v", or "shared"
RULES = [
    ("contracts/*", "shared"),
    ("contracts/**", "shared"),
    ("docs/engineering/*", "v"),
    ("docs/engineering/**", "v"),
    ("docs/BUILD_LOG.md", "any"),
    ("docs/*", "s"),
    ("docs/**", "s"),
    ("dashboard/*", "both"),
    ("dashboard/**", "both"),
    ("data/scripts/*", "s"),
    ("data/scripts/**", "s"),
    ("data/raw/SOURCES.md", "s"),
    ("data/ASSUMPTIONS.md", "s"),
    ("config/tariffs.yaml", "s"),
    ("gridnudge/language/templates.py", "s"),
    ("README.md", "s"),
    ("*", "v"),
]
PREFIX_OWNER = {"v/": "v", "s/": "s", "contract/": "shared"}


def owner_of(path: str) -> str:
    normalized = path.replace("\\", "/")
    for pattern, owner in RULES:
        if fnmatch.fnmatch(normalized, pattern):
            return owner
    return "v"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=None)
    ap.add_argument("--base", default="origin/dev")
    a = ap.parse_args()

    try:
        branch = a.branch or subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except Exception:
        branch = "master"

    who = next((o for p, o in PREFIX_OWNER.items() if branch.startswith(p)), None)
    if who is None:
        return 0  # main, dev, master, hotfix: not checked here

    try:
        files = subprocess.check_output(
            ["git", "diff", "--name-only", f"{a.base}...HEAD"], text=True
        ).split()
    except Exception:
        files = []

    bad = []
    for f in files:
        o = owner_of(f)
        if o in ("any", "both"):
            continue
        if o == "shared" and who != "shared":
            bad.append((f, "shared (use a contract/* branch)"))
        elif o != "shared" and who != "shared" and o != who:
            bad.append((f, f"owned by {o}"))

    if bad:
        print("OWNERSHIP VIOLATION on branch", branch)
        for f, why in bad:
            print(f"  {f}  -> {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
