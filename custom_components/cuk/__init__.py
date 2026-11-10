"""CUK Strefa Klienta integration."""

from __future__ import annotations

from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import CukApi, CukApiAuthenticationError
from .const import CONF_USER_ID, DOMAIN, PLATFORMS
from .coordinator import CukCoordinator

CukConfigEntry: TypeAlias = ConfigEntry[CukCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (YAML is not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CukConfigEntry) -> bool:
    """Set up CUK from a config entry."""
    api = CukApi(async_get_clientsession(hass), entry.data[CONF_USER_ID])
    coordinator = CukCoordinator(hass, api)
    try:
        await coordinator.async_config_entry_first_refresh()
    except CukApiAuthenticationError as err:
        raise ConfigEntryAuthFailed(str(err)) from err

    # Migrate legacy unique IDs from v0.6.x to entry_id scoped unique IDs
    ent_reg = er.async_get(hass)
    for old_id, key in (
        ("cuk_policies", "policies"),
        ("cuk_active_policies", "active_policies"),
        ("cuk_unpaid_installments", "unpaid_installments"),
        ("cuk_receivables", "receivables"),
        ("cuk_next_payment_date", "next_payment_date"),
        ("cuk_next_payment_amount", "next_payment_amount"),
        ("cuk_assistant", "assistant"),
        ("cuk_expiring_policies", "expiring_policies"),
        ("cuk_payment_due", "payment_due"),
        ("cuk_policy_expiring", "policy_expiring"),
    ):
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, old_id
        ) or ent_reg.async_get_entity_id("binary_sensor", DOMAIN, old_id)
        if entity_id:
            ent_reg.async_update_entity(
                entity_id, new_unique_id=f"{entry.entry_id}_{key}"
            )

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CukConfigEntry) -> bool:
    """Unload CUK platforms."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: CukConfigEntry) -> None:
    """Reload config entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
