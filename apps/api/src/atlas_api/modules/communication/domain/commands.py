"""Inbound chat command parser and intent router (Spec 08 §2, §4)."""

from __future__ import annotations


def parse_chat_command(raw_text: str) -> tuple[str, str | None]:
    """Parses raw text from chat apps into a canonical (command_verb, target_arg)."""
    clean_text = raw_text.strip()
    if clean_text.startswith("/"):
        clean_text = clean_text[1:].strip()

    parts = clean_text.split(maxsplit=1)
    if not parts:
        return "UNKNOWN", None

    verb = parts[0].upper()
    arg = parts[1].strip() if len(parts) > 1 else None

    if verb in ("ANALYZE", "SCAN", "RESEARCH"):
        return "ANALYZE", arg.upper() if arg else "BTC/USDT"

    if verb in ("STATUS", "HEALTH", "PORTFOLIO"):
        return "STATUS", None

    if verb in ("CLOSE", "EXIT", "FLATTEN"):
        return "CLOSE", arg.upper() if arg else "ALL"

    if verb in ("PAUSE", "STOP", "HALT"):
        return "PAUSE", None

    if verb in ("RESUME", "START", "ARM"):
        return "RESUME", None

    if verb in ("REPORT", "COACH", "WEEKLY"):
        return "REPORT", None

    return "UNKNOWN", clean_text
