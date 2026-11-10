"""Tests for CUK initialization and entry lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.cuk import async_setup, async_setup_entry, async_unload_entry
from custom_components.cuk.const import CONF_USER_ID


@pytest.mark.asyncio
async def test_async_setup() -> None:
    hass = MagicMock(spec=HomeAssistant)
    assert await async_setup(hass, {}) is True


@pytest.mark.asyncio
async def test_async_setup_and_unload_entry() -> None:
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {CONF_USER_ID: "valid-object-id"}
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock()

    mock_ent_reg = MagicMock()
    # Mock finding an old entity ID to test migration
    mock_ent_reg.async_get_entity_id.side_effect = lambda domain, p_domain, old_id: (
        "sensor.cuk_policies" if old_id == "cuk_policies" else None
    )
    mock_ent_reg.async_update_entity = MagicMock()

    with (
        patch("custom_components.cuk.async_get_clientsession"),
        patch("custom_components.cuk.CukCoordinator") as mock_coord_cls,
        patch("custom_components.cuk.er.async_get", return_value=mock_ent_reg),
    ):
        mock_coord = mock_coord_cls.return_value
        mock_coord.async_config_entry_first_refresh = AsyncMock()

        assert await async_setup_entry(hass, entry) is True
        assert entry.runtime_data == mock_coord
        # Verify migration of old unique ID
        mock_ent_reg.async_update_entity.assert_called_once_with(
            "sensor.cuk_policies", new_unique_id="test_entry_123_policies"
        )
        hass.config_entries.async_forward_entry_setups.assert_called_once()

        # Unload
        assert await async_unload_entry(hass, entry) is True
        hass.config_entries.async_unload_platforms.assert_called_once()
