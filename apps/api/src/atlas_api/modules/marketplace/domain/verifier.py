"""Marketplace security verification and revenue split accounting (Spec 12 §2, §4)."""

from __future__ import annotations

from decimal import Decimal

_FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "os.system",
    "subprocess",
    "socket.socket",
    "eval(",
    "exec(",
    "__import__('os')",
    "__import__('subprocess')",
    "shutil.rmtree",
)


def scan_plugin_code_security(source_code: str) -> tuple[bool, str | None]:
    """Inspects submitted code against prohibited system calls and network socket creation."""
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in source_code:
            return False, f"SECURITY_VETO: Prohibited system call detected: '{pattern}'"
    return True, None


def calculate_creator_revenue_split(gross_amount_usd: Decimal) -> tuple[Decimal, Decimal]:
    """Calculates creator net earnings (70%) and platform commission (30%).

    Returns (creator_earnings_usd, platform_fees_usd).
    """
    creator_share = (gross_amount_usd * Decimal("0.70")).quantize(Decimal("0.01"))
    platform_share = gross_amount_usd - creator_share
    return creator_share, platform_share
