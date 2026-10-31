from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CukApi, CukApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CukCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate CUK API data for all entities."""

    def __init__(self, hass: HomeAssistant, api: CukApi) -> None:
        self.api = api
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            policies = await self.api.get_policies()
        except CukApiError as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, Any] = {
            "policies": policies,
            "assistant": None,
            "calculations": None,
            "last_update": datetime.now(timezone.utc),
        }

        try:
            data["assistant"] = await self.api.get_assistant()
        except CukApiError as err:
            _LOGGER.warning("GetClientAssistant failed: %s", err)

        try:
            data["calculations"] = await self.api.get_calculations()
        except CukApiError as err:
            _LOGGER.warning("GetClientCalculations failed: %s", err)

        return data
