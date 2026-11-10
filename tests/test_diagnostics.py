"""Tests for CUK diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.cuk.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics_redacts_sensitive_data() -> None:
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.version = 1
    entry.data = {"user_id": "secret-object-id"}

    coordinator = MagicMock()
    coordinator.data = {
        "policies": [
            {
                "NumerPolisy": "SECRET-POL-123",
                "NumerRejestracyjny": "WA12345",
                "NazwaObiektu": "ul. Marszalkowska 10/12, Warszawa",
                "object_name": "Mieszkanie Warszawa",
                "Status": 0,
            }
        ],
        "assistant": {
            "ImieNazwiskoOpiekuna": "Adam Nowak",
            "Email": "adam@cuk.pl",
            "phone": "123456789",
        },
    }
    entry.runtime_data = coordinator

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["entry"]["data"]["user_id"] == "**REDACTED**"
    assert diag["coordinator_data"]["policies"][0]["NumerPolisy"] == "**REDACTED**"
    assert diag["coordinator_data"]["policies"][0]["NumerRejestracyjny"] == "**REDACTED**"
    assert diag["coordinator_data"]["policies"][0]["NazwaObiektu"] == "**REDACTED**"
    assert diag["coordinator_data"]["policies"][0]["object_name"] == "**REDACTED**"
    assert diag["coordinator_data"]["policies"][0]["Status"] == 0
    assert diag["coordinator_data"]["assistant"]["ImieNazwiskoOpiekuna"] == "**REDACTED**"
    assert diag["coordinator_data"]["assistant"]["Email"] == "**REDACTED**"
