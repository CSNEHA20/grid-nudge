"""Smoke tests to verify all top-level modules and packages import cleanly without missing dependencies or syntax errors."""

import importlib
import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "eval",
        "eval.baselines",
        "eval.metrics",
        "eval.calibration",
        "eval.plots",
        "eval.run",
        "eval.pareto",
        "twin",
        "twin.world",
        "twin.runner",
        "twin.users",
        "twin.grid",
        "twin.stations",
        "twin.events",
        "twin.data_loader",
        "twin.battery_truth",
        "twin.behavior_hidden",
        "gridnudge",
        "gridnudge.contracts",
        "gridnudge.state",
        "gridnudge.pipeline",
        "gridnudge.planner",
        "gridnudge.allocator",
        "gridnudge.perception.journey",
        "gridnudge.perception.battery",
        "gridnudge.perception.station",
        "gridnudge.perception.grid",
        "gridnudge.perception.flexibility",
        "gridnudge.persuasion.features",
        "gridnudge.persuasion.lints",
        "gridnudge.persuasion.fatigue",
        "gridnudge.persuasion.uplift",
        "gridnudge.persuasion.pretrain",
        "gridnudge.safety.invariants",
        "gridnudge.safety.failsilent",
        "gridnudge.language.templates",
        "gridnudge.language.verify",
        "gridnudge.language.render",
        "services",
        "services.decide",
        "services.outcomes",
        "services.reward_update",
        "services.explain",
        "services.metrics",
        "agent",
        "agent.tools",
    ],
)
def test_module_imports_cleanly(module_name: str):
    """Ensure module can be imported without throwing NameError, ImportError or SyntaxError."""
    mod = importlib.import_module(module_name)
    assert mod is not None
