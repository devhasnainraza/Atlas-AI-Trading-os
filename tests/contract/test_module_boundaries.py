"""US1 — module boundary contracts are enforced (T013).

Runs import-linter against the root pyproject contracts: shared packages must not import
the app; modules must not reach into another module's internals.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_import_linter_contracts_pass():
    result = subprocess.run(
        [sys.executable, "-m", "importlinter.cli", "lint_imports"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"import-linter failed:\n{result.stdout}\n{result.stderr}"


def test_sample_module_has_public_interface():
    public = REPO_ROOT / "apps/api/src/atlas_api/modules/sample/public.py"
    assert public.exists(), "every module must expose public.py as its only import surface"
