"""Golden test harness for the manufacturing network optimisation platform.

The reference model here is deliberately small. It exists so that the
Optimisation Scientist can hand-solve every golden problem and the Auditor
can verify any solver against known answers.
"""
from .model import build_model, solve, Solution, InfeasibleError, ModelDataError
from .loader import load_problem, Problem
from .data_quality import run_checks, DQFinding, Severity

__all__ = [
    "build_model", "solve", "Solution", "InfeasibleError", "ModelDataError",
    "load_problem", "Problem", "run_checks", "DQFinding", "Severity",
]
