"""T007 — the float ban.

Binary floating point cannot represent `0.1`. Every arithmetic step on a price or a quantity
compounds that, and the error surfaces as an order that is off by a tick, a position that will
not fully close, or a balance that does not reconcile. So money and quantity are ``Decimal``
everywhere in trading code, and this test is the mechanism that keeps them that way.

Ruff has no rule for "no float literals", and a blanket ban would be wrong anyway: durations,
timeouts, and token-bucket rates are legitimately floats and nothing rounds to a cent. So the
ban is scoped by *what the value is*, not by syntax — an identifier that names money or
quantity may not be annotated ``float``, defaulted to a float literal, or produced by
``float()``.

Adding a genuinely non-monetary name that trips this test is a one-line addition to
``_NON_MONETARY_SUFFIXES``. Adding a monetary one that needs a float is not something to allow.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Trees where the ban applies. These are the only places prices and quantities are handled.
SCANNED_ROOTS = (
    Path("shared/atlas_venues"),
    Path("apps/api/src/atlas_api/modules/trading"),
    Path("apps/api/src/atlas_api/modules/marketdata"),
)

#: Identifier fragments that mean "this holds money or a tradeable quantity". Single words are
#: matched against whole ``_``-separated segments, so ``fee`` does not match ``feed`` and
#: ``price`` does not match ``priced``; fragments containing ``_`` are matched as substrings.
_MONEY_TOKENS = (
    "price",
    "quantity",
    "qty",
    "notional",
    "balance",
    "equity",
    "margin",
    "commission",
    "fee",
    "pnl",
    "profit",
    "loss",
    "amount",
    "premium",
    "volume",
    "drawdown",
    "tick_size",
    "step_size",
    "contract_size",
    "bps",
)

#: Suffixes that make a name a measurement of something other than money. A value denominated
#: in seconds or expressed as a count cannot round to a cent, so ``equity_seconds`` (the
#: staleness window for equities) is not an account balance.
_NON_MONETARY_SUFFIXES = (
    "_seconds",
    "_secs",
    "_ms",
    "_minutes",
    "_hours",
    "_days",
    "_count",
    "_index",
)

#: Files permitted to call ``float()``. The token bucket works in monotonic seconds and
#: fractional tokens; there is no money in it.
_FLOAT_CALL_ALLOWED = frozenset({"shared/atlas_venues/ratelimit.py"})


def _is_monetary(name: str | None) -> bool:
    if not name:
        return False
    lowered = name.lower()
    if lowered.endswith(_NON_MONETARY_SUFFIXES):
        return False
    segments = set(lowered.split("_"))
    for token in _MONEY_TOKENS:
        if "_" in token:
            if token in lowered:
                return True
        elif token in segments or f"{token}s" in segments:
            return True
    return False


def _mentions_float(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    return bool(re.search(r"\bfloat\b", ast.unparse(annotation)))


def _is_float_literal(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, float)
        and not isinstance(node.value, bool)
    )


def _target_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Attribute):
            names.append(target.attr)
    return names


def _scan_file(path: Path, rel: str) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        # A money-named field annotated float.
        if isinstance(node, ast.AnnAssign):
            for name in _target_names(node):
                if _is_monetary(name) and _mentions_float(node.annotation):
                    violations.append(
                        f"{rel}:{node.lineno} '{name}' is annotated float; money and quantity "
                        f"must be Decimal"
                    )
            # A Decimal field defaulted to a float literal: `x: Decimal = 0.1` stores
            # 0.1000000000000000055511151231257827.
            if (
                node.value is not None
                and _is_float_literal(node.value)
                and node.annotation is not None
                and "Decimal" in ast.unparse(node.annotation)
            ):
                violations.append(
                    f"{rel}:{node.lineno} Decimal field defaulted to a float literal; "
                    f"use a string or int"
                )

        # A money-named parameter annotated float.
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = node.args
            for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                if _is_monetary(arg.arg) and _mentions_float(arg.annotation):
                    violations.append(
                        f"{rel}:{node.lineno} parameter '{arg.arg}' of '{node.name}' is "
                        f"annotated float; money and quantity must be Decimal"
                    )
            if _is_monetary(node.name) and _mentions_float(node.returns):
                violations.append(
                    f"{rel}:{node.lineno} '{node.name}' returns float; money and quantity "
                    f"must be Decimal"
                )

        # A money-named variable assigned a float literal.
        elif isinstance(node, ast.Assign):
            if _is_float_literal(node.value):
                for name in _target_names(node):
                    if _is_monetary(name):
                        violations.append(
                            f"{rel}:{node.lineno} '{name}' assigned a float literal; use Decimal"
                        )

        # A money-named keyword argument given a float literal.
        elif isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg and _is_monetary(keyword.arg) and _is_float_literal(keyword.value):
                    violations.append(
                        f"{rel}:{node.lineno} keyword '{keyword.arg}' given a float literal; "
                        f"use Decimal or a string"
                    )
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "float"
                and rel not in _FLOAT_CALL_ALLOWED
            ):
                violations.append(
                    f"{rel}:{node.lineno} float() conversion; if this is a duration add the "
                    f"file to _FLOAT_CALL_ALLOWED, otherwise use Decimal"
                )

    return violations


def _python_files() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for root in SCANNED_ROOTS:
        directory = REPO_ROOT / root
        assert directory.is_dir(), f"scanned root missing: {root} (did a package move?)"
        for path in sorted(directory.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            found.append((path, path.relative_to(REPO_ROOT).as_posix()))
    return found


def test_money_and_quantity_are_never_float():
    files = _python_files()
    assert len(files) > 10, "the scan found almost nothing; the roots are probably wrong"

    violations: list[str] = []
    for path, rel in files:
        violations.extend(_scan_file(path, rel))

    assert not violations, "float used for money or quantity:\n  " + "\n  ".join(violations)


def test_the_scanner_actually_catches_a_violation(tmp_path: Path):
    """A guard test that cannot fail is worse than no guard test.

    Each case below is a real way the ban has to hold, so a refactor that quietly stops
    detecting one of them fails here instead of passing silently.
    """
    cases = {
        "annotated_field": "class Order:\n    quantity: float\n",
        "annotated_param": "def submit(price: float) -> None: ...\n",
        "float_literal_default": "from decimal import Decimal\nfee: Decimal = 0.1\n",
        "float_literal_assign": "max_notional = 1000.0\n",
        "float_keyword": "submit(quantity=1.5)\n",
        "float_call": "x = float('1.5')\n",
    }
    for label, source in cases.items():
        target = tmp_path / f"{label}.py"
        target.write_text(source, encoding="utf-8")
        assert _scan_file(target, f"{label}.py"), f"scanner missed {label}"


def test_the_scanner_does_not_flag_durations():
    """Seconds are not money. A ban that fires on timeouts would be turned off within a week."""
    for benign in (
        "timeout_seconds",
        "interval",
        "equity_seconds",  # the staleness window for equities, not an account balance
        "feed_heartbeat_timeout_seconds",  # 'fee' must not match inside 'feed'
        "price_count",  # a count of prices is a count
        "latency_seconds",
    ):
        assert not _is_monetary(benign), f"{benign} is not money"

    for monetary in (
        "max_notional",
        "quantity",
        "reference_price",
        "account_equity",
        "available_margin",
        "commission_bps",
        "realized_pnl",
        "contract_size",
        "prices",
    ):
        assert _is_monetary(monetary), f"{monetary} is money"
