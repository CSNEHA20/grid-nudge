"""Leakage audit tests to verify strict isolation between hidden ground truth and decision/pretraining logic.

Validates:
1. data/scripts/fetch_rct.py does NOT import twin.behavior_hidden and does NOT read config/behavior_assumed.yaml.
2. gridnudge/persuasion/pretrain.py does NOT import twin.behavior_hidden and does NOT read config/behavior_assumed.yaml.
3. No module in gridnudge/ imports twin.behavior_hidden (the learner and policy must not know hidden simulation truth).
"""

import ast
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]


def get_all_imported_names(filepath: Path) -> set[str]:
    """Extract all imported module names from a Python source file using AST."""
    content = filepath.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(filepath))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_fetch_rct_has_no_hidden_behavior_leakage():
    """fetch_rct.py must not import twin.behavior_hidden or read behavior_assumed.yaml."""
    fetch_rct_path = ROOT_DIR / "data" / "scripts" / "fetch_rct.py"
    assert fetch_rct_path.exists(), "data/scripts/fetch_rct.py must exist"

    content = fetch_rct_path.read_text(encoding="utf-8")
    assert "behavior_hidden" not in content, "fetch_rct.py must not reference behavior_hidden"
    assert "behavior_assumed" not in content, "fetch_rct.py must not read behavior_assumed.yaml"

    imported = get_all_imported_names(fetch_rct_path)
    for mod in imported:
        assert not mod.startswith("twin.behavior_hidden"), f"Illegal import {mod} in fetch_rct.py"


def test_pretrain_has_no_hidden_behavior_leakage():
    """gridnudge/persuasion/pretrain.py must not import twin.behavior_hidden or read behavior_assumed.yaml."""
    pretrain_path = ROOT_DIR / "gridnudge" / "persuasion" / "pretrain.py"
    assert pretrain_path.exists(), "gridnudge/persuasion/pretrain.py must exist"

    content = pretrain_path.read_text(encoding="utf-8")
    assert "behavior_hidden" not in content, "pretrain.py must not reference behavior_hidden"
    assert "behavior_assumed" not in content, "pretrain.py must not read behavior_assumed.yaml"

    imported = get_all_imported_names(pretrain_path)
    for mod in imported:
        assert not mod.startswith("twin.behavior_hidden"), f"Illegal import {mod} in pretrain.py"


def test_entire_gridnudge_package_has_no_hidden_behavior_leakage():
    """No decision, perception, planner, safety or persuasion module in gridnudge/ may import twin.behavior_hidden."""
    gridnudge_dir = ROOT_DIR / "gridnudge"
    py_files = list(gridnudge_dir.rglob("*.py"))
    assert len(py_files) > 0

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        assert "twin.behavior_hidden" not in content, (
            f"Leakage detected in {py_file}: imports or references twin.behavior_hidden"
        )
        assert "behavior_assumed.yaml" not in content, (
            f"Leakage detected in {py_file}: reads or references config/behavior_assumed.yaml"
        )
