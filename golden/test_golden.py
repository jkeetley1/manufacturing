"""pytest entry point: one test per golden problem."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from goldentest.runner import PROBLEMS_DIR, evaluate  # noqa: E402

PROBLEMS = sorted(PROBLEMS_DIR.glob("*.yaml"))


@pytest.mark.parametrize("path", PROBLEMS, ids=[p.stem for p in PROBLEMS])
def test_golden(path):
    o = evaluate(path)
    assert o.passed, "\n".join(o.failures)
