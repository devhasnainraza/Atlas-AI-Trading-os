"""T027 — the risk gate has no bypass path (FR-038, Constitution VI).

This is a *structural* guard, not a behavioural one. Behavioural tests prove the gate rejects
a bad order today; this one proves nobody can add a way around it tomorrow. It fails if a
bypass parameter appears anywhere in the trading source tree, because the moment a
``skip_risk=True`` exists, some caller eventually passes it.

The checklist entry this backs: "No requirement permits bypassing the pre-trade risk gate."
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Directories where an order can be composed, approved, or transmitted.
TRADING_SOURCE_ROOTS = (
    REPO_ROOT / "shared" / "atlas_venues",
    REPO_ROOT / "apps" / "api" / "src" / "atlas_api" / "modules" / "trading",
    REPO_ROOT / "apps" / "api" / "src" / "atlas_api" / "modules" / "marketdata",
    REPO_ROOT / "services" / "worker",
)

# Names that would constitute a bypass if they ever became a parameter or a field.
FORBIDDEN_NAMES = frozenset(
    {
        "skip_risk",
        "skip_risk_check",
        "bypass_risk",
        "bypass_risk_gate",
        "ignore_risk",
        "disable_risk",
        "force_submit",
        "force_order",
        "no_risk_check",
        "override_risk",
        "risk_override",
        "unchecked",
        "skip_confirmation",
        "bypass_confirmation",
        "skip_kill_switch",
        "ignore_kill_switch",
    }
)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in TRADING_SOURCE_ROOTS:
        if not root.exists():
            continue
        files.extend(
            p for p in root.rglob("*.py") if "__pycache__" not in p.parts and "tests" not in p.parts
        )
    return files


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


class TestNoRiskBypassExists:
    def test_source_tree_is_present(self) -> None:
        """Guard the guard: a moved directory must not silently make this test vacuous."""
        assert (REPO_ROOT / "shared" / "atlas_venues").exists()
        assert _python_files(), "no trading source files found; the guard's roots are stale"

    def test_no_function_accepts_a_bypass_parameter(self) -> None:
        offenders: list[str] = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                args = node.args
                names = [
                    a.arg
                    for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)
                    if a.arg.lower() in FORBIDDEN_NAMES
                ]
                offenders.extend(f"{_relative(path)}:{node.lineno} {node.name}({n})" for n in names)
        assert not offenders, (
            "risk-gate bypass parameter(s) found — FR-038 forbids any override path:\n"
            + "\n".join(offenders)
        )

    def test_no_class_declares_a_bypass_field(self) -> None:
        offenders: list[str] = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for stmt in node.body:
                    target = None
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        target = stmt.target.id
                    elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        first = stmt.targets[0]
                        target = first.id if isinstance(first, ast.Name) else None
                    if target and target.lower() in FORBIDDEN_NAMES:
                        offenders.append(f"{_relative(path)}:{stmt.lineno} {node.name}.{target}")
        assert not offenders, (
            "risk-gate bypass field(s) found — FR-038 forbids any override path:\n"
            + "\n".join(offenders)
        )

    def test_no_call_passes_a_bypass_keyword(self) -> None:
        offenders: list[str] = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                offenders.extend(
                    f"{_relative(path)}:{node.lineno} passes {kw.arg}"
                    for kw in node.keywords
                    if kw.arg and kw.arg.lower() in FORBIDDEN_NAMES
                )
        assert not offenders, "call site(s) passing a risk bypass keyword — FR-038:\n" + "\n".join(
            offenders
        )


class TestSubmitRequestCannotCarryAnOverride:
    """The wire-level request object is the last place a bypass could hide."""

    def test_submit_request_has_no_override_field(self) -> None:
        from atlas_venues.models import SubmitRequest

        fields = {f.lower() for f in SubmitRequest.__dataclass_fields__}
        assert not (fields & FORBIDDEN_NAMES), (
            f"SubmitRequest exposes a bypass field: {sorted(fields & FORBIDDEN_NAMES)}"
        )

    def test_submit_request_is_immutable(self) -> None:
        """An order approved by the gate must not be editable before it reaches the wire."""
        from decimal import Decimal

        from atlas_venues.enums import OrderSide, OrderType, TimeInForce, VenueEnvironment
        from atlas_venues.models import SubmitRequest

        request = SubmitRequest(
            venue_code="paper",
            venue_account_ref="a",
            venue_symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1"),
            time_in_force=TimeInForce.IOC,
            client_order_id="cid-1",
            environment=VenueEnvironment.PAPER,
        )
        with pytest.raises((AttributeError, TypeError)):
            request.quantity = Decimal("999")  # type: ignore[misc]
