"""Diagnostics support for CUK Strefa Klienta."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import CukConfigEntry

TO_REDACT = {
    "user_id",
    "userId",
    "id",
    "NumerPolisy",
    "NumerRejestracyjny",
    "NazwaObiektu",
    "object_name",
    "ImieNazwiskoOpiekuna",
    "Email",
    "NrKontaktowyOpiekuna",
    "AdresPlacowki1",
    "AdresPlacowki2",
    "NrKontaktowyPlacowki",
    "TuNumerKontaktowy",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CukConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "coordinator_data": async_redact_data(coordinator.data, TO_REDACT),
    }
