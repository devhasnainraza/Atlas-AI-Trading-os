"""T005 — the flags we ship must be the safe ones.

`infra/flags/flags.json` is a file people edit under pressure, sometimes to turn something on for
a demo. This test is what stops a `venue.binance.enabled: true` from reaching main: the committed
file must have every real-money venue off and live transmission off, and every venue the code
knows about must have a line here so nobody has to guess whether a missing key means "off" or
"nobody thought about it".
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas_api.modules.trading.venues import VENUE_FLAG_DEFAULTS, VENUE_FLAG_KEYS
from atlas_core.feature_flags import FeatureFlags, FileFlagProvider
from atlas_venues.adapters.paper import PAPER_VENUE_CODE

FLAGS_FILE = Path(__file__).resolve().parents[3] / "infra" / "flags" / "flags.json"


def _shipped_flags() -> dict[str, object]:
    assert FLAGS_FILE.is_file(), f"the flags file is missing: {FLAGS_FILE}"
    return json.loads(FLAGS_FILE.read_text(encoding="utf-8"))


def test_every_known_venue_has_an_explicit_line():
    """A venue with no line is a venue nobody decided about; make the decision visible."""
    flags = _shipped_flags()
    missing = [key for key in VENUE_FLAG_KEYS.values() if key not in flags]
    assert not missing, f"venues with no entry in flags.json: {missing}"


def test_no_real_money_venue_ships_enabled():
    flags = _shipped_flags()
    enabled = [
        key
        for code, key in VENUE_FLAG_KEYS.items()
        if code != PAPER_VENUE_CODE and flags.get(key) is True
    ]
    assert not enabled, f"real-money venue(s) enabled in the committed flags file: {enabled}"


def test_live_order_transmission_ships_disabled():
    assert _shipped_flags().get("trading.live_orders.enabled") is False


def test_paper_ships_enabled_so_the_platform_is_usable_out_of_the_box():
    assert _shipped_flags().get(VENUE_FLAG_KEYS[PAPER_VENUE_CODE]) is True


def test_the_file_and_the_code_defaults_agree():
    """Two sources of the same decision must not disagree.

    They are deliberately duplicated — the file can be edited without a deploy, the code default
    applies when no file is configured — but a disagreement means one of them is a surprise.
    """
    flags = _shipped_flags()
    for code, key in VENUE_FLAG_KEYS.items():
        assert flags[key] == VENUE_FLAG_DEFAULTS.get(code, False), (
            f"flags.json and VENUE_FLAG_DEFAULTS disagree about {code}"
        )


def test_the_file_is_loadable_by_the_provider_the_app_uses():
    """A JSON file that the app cannot read is documentation, not configuration."""
    flags = FeatureFlags(FileFlagProvider(FLAGS_FILE))
    assert flags.is_enabled(VENUE_FLAG_KEYS[PAPER_VENUE_CODE], default=False) is True
    assert flags.is_enabled("trading.live_orders.enabled", default=False) is False
    # An unknown key falls back to the caller's default, which is why those defaults are
    # fail-closed everywhere in trading code.
    assert flags.is_enabled("venue.does_not_exist.enabled", default=False) is False
