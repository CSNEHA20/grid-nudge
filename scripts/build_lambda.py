"""Build and stage Lambda package in build/lambda/."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_LAMBDA = ROOT / "build" / "lambda"


def stage():
    if BUILD_LAMBDA.exists():
        shutil.rmtree(BUILD_LAMBDA)
    BUILD_LAMBDA.mkdir(parents=True, exist_ok=True)
    (BUILD_LAMBDA / "config").mkdir(parents=True, exist_ok=True)

    for package_name in ["gridnudge", "services", "agent"]:
        src = ROOT / package_name
        dst = BUILD_LAMBDA / package_name
        if src.exists():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))

    safety_yaml = ROOT / "config" / "safety.yaml"
    if safety_yaml.exists():
        shutil.copy(safety_yaml, BUILD_LAMBDA / "config" / "safety.yaml")

    reqs = "numpy>=1.24.0,<2.0.0\npydantic>=2.0\npyyaml>=6.0\n"
    (BUILD_LAMBDA / "requirements.txt").write_text(reqs, encoding="utf-8")

    # Clean any lingering __pycache__
    for p in BUILD_LAMBDA.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p)

    print(f"Lambda package successfully staged in {BUILD_LAMBDA}")


if __name__ == "__main__":
    stage()
