"""Data update coordinator for CUK."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CukApi, CukApiAuthenticationError, CukApiError
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
        except CukApiAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CukApiError as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, Any] = {
            "policies": policies,
            "assistant": None,
        }
        try:
            data["assistant"] = await self.api.get_assistant()
        except CukApiAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CukApiError as err:
            _LOGGER.warning("CUK assistant endpoint failed: %s", err)

        data["last_update"] = datetime.now(UTC)
        return data
