from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CukCoordinator
from .sensor import _active_policies, _dt, _installments


def _device_info() -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, "cuk")},
        "name": "CUK Strefa Klienta",
        "manufacturer": "CUK Ubezpieczenia",
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CukCoordinator = entry.runtime_data
    async_add_entities(
        [CukPaymentDueSensor(coordinator), CukPolicyExpiringSensor(coordinator)]
    )


class CukBaseBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CukCoordinator, unique_id: str, name: str) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_device_info = _device_info()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        last_update = (self.coordinator.data or {}).get("last_update")
        return {"last_update": last_update.isoformat() if last_update else None}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class CukPaymentDueSensor(CukBaseBinarySensor):
    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_payment_due", "Płatność wymagana")
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return any(
            not installment.get("Zaplacona", False)
            for _, installment in _installments(self.coordinator)
        )


class CukPolicyExpiringSensor(CukBaseBinarySensor):
    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_policy_expiring", "Polisa wygasa")
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        now = datetime.now(timezone.utc)
        return any(
            0 <= (end - now).total_seconds() <= 30 * 86400
            for p in _active_policies(self.coordinator)
            if (end := _dt(p.get("DataObowiazywaniaDo"))) is not None
        )
