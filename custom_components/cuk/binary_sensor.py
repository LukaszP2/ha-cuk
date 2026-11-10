"""Binary sensor platform for CUK Strefa Klienta."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CukConfigEntry
from .const import (
    CONF_EXPIRING_DAYS,
    CONF_PAYMENT_DUE_DAYS,
    DEFAULT_EXPIRING_DAYS,
    DEFAULT_PAYMENT_DUE_DAYS,
)
from .coordinator import CukCoordinator
from .models import (
    get_active_policies,
    get_device_info,
    get_unpaid_installments,
    parse_date,
)


def _policies(coordinator: CukCoordinator) -> list[dict[str, Any]]:
    data = coordinator.data or {}
    return data.get("policies", []) if isinstance(data, dict) else []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CukConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUK binary sensor entities."""
    coordinator = entry.runtime_data
    entry_id = entry.entry_id
    expiring_days = entry.options.get(CONF_EXPIRING_DAYS, DEFAULT_EXPIRING_DAYS)
    payment_due_days = entry.options.get(
        CONF_PAYMENT_DUE_DAYS, DEFAULT_PAYMENT_DUE_DAYS
    )

    async_add_entities(
        [
            CukPaymentDueSensor(coordinator, entry_id, payment_due_days),
            CukPolicyExpiringSensor(coordinator, entry_id, expiring_days),
        ]
    )


class CukBaseBinarySensor(CoordinatorEntity[CukCoordinator], BinarySensorEntity):
    """Base binary sensor for CUK."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: CukCoordinator, entry_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = get_device_info(entry_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        last_update = (self.coordinator.data or {}).get("last_update")
        return {"last_update": last_update.isoformat() if last_update else None}


class CukPaymentDueSensor(CukBaseBinarySensor):
    """Signals overdue or immediately due payments."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator: CukCoordinator, entry_id: str, payment_due_days: int
    ) -> None:
        super().__init__(coordinator, entry_id, "payment_due")
        self._payment_due_days = payment_due_days

    @property
    def is_on(self) -> bool:
        now = datetime.now(UTC)
        threshold_seconds = self._payment_due_days * 86400
        return any(
            (due := parse_date(installment.get("TerminPlatnosci"), end_of_day=True))
            is not None
            and (due - now).total_seconds() <= threshold_seconds
            for _, installment in get_unpaid_installments(_policies(self.coordinator))
        )


class CukPolicyExpiringSensor(CukBaseBinarySensor):
    """Signals that an active policy is expiring within configured days."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator: CukCoordinator, entry_id: str, expiring_days: int
    ) -> None:
        super().__init__(coordinator, entry_id, "policy_expiring")
        self._expiring_days = expiring_days

    @property
    def is_on(self) -> bool:
        now = datetime.now(UTC)
        threshold_seconds = self._expiring_days * 86400
        return any(
            0 <= (end - now).total_seconds() <= threshold_seconds
            for p in get_active_policies(_policies(self.coordinator), now)
            if (end := parse_date(p.get("DataObowiazywaniaDo"), end_of_day=True))
            is not None
        )
