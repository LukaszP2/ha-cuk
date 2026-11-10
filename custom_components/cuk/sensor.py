"""Sensor platform for CUK Strefa Klienta."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CukConfigEntry
from .const import CONF_EXPIRING_DAYS, DEFAULT_EXPIRING_DAYS
from .coordinator import CukCoordinator
from .models import (
    get_active_policies,
    get_device_info,
    get_next_payment,
    get_unpaid_installments,
    parse_date,
)


def _policies(coordinator: CukCoordinator) -> list[dict[str, Any]]:
    data = coordinator.data or {}
    return data.get("policies", []) if isinstance(data, dict) else []


def _assistant(coordinator: CukCoordinator) -> dict[str, Any]:
    data = coordinator.data or {}
    value = data.get("assistant") if isinstance(data, dict) else None
    return value if isinstance(value, dict) else {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CukConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUK sensor entities."""
    coordinator = entry.runtime_data
    entry_id = entry.entry_id
    expiring_days = entry.options.get(CONF_EXPIRING_DAYS, DEFAULT_EXPIRING_DAYS)

    async_add_entities(
        [
            CukPoliciesSensor(coordinator, entry_id),
            CukActivePoliciesSensor(coordinator, entry_id),
            CukUnpaidSensor(coordinator, entry_id),
            CukReceivablesSensor(coordinator, entry_id),
            CukNextPaymentDateSensor(coordinator, entry_id),
            CukNextPaymentAmountSensor(coordinator, entry_id),
            CukExpiringSensor(coordinator, entry_id, expiring_days),
            CukAssistantSensor(coordinator, entry_id),
        ]
    )


class CukBaseSensor(CoordinatorEntity[CukCoordinator], SensorEntity):
    """Base class for CUK sensors."""

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


class CukPoliciesSensor(CukBaseSensor):
    """Total policies count sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "policies")

    @property
    def native_value(self) -> int:
        return len(_policies(self.coordinator))


class CukActivePoliciesSensor(CukBaseSensor):
    """Active policies count sensor."""

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "active_policies")

    @property
    def native_value(self) -> int:
        return len(get_active_policies(_policies(self.coordinator)))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        policies = []
        for p in get_active_policies(_policies(self.coordinator)):
            policies.append(
                {
                    "number": p.get("NumerPolisy"),
                    "insurer": p.get("Ubezpieczyciel"),
                    "object_type": p.get("TypObiektu"),
                    "object_name": p.get("NazwaObiektu"),
                    "vehicle": p.get("MarkaPojazdu"),
                    "registration": p.get("NumerRejestracyjny"),
                    "risk": p.get("Ryzyko"),
                    "valid_from": p.get("DataObowiazywaniaOd"),
                    "valid_to": p.get("DataObowiazywaniaDo"),
                    "status": p.get("Status"),
                    "state": p.get("Stan"),
                    "contact_phone": p.get("TuNumerKontaktowy"),
                    "logo_url": p.get("TuLogoUrl"),
                    "installments": p.get("Raty") or [],
                }
            )
        return {**super().extra_state_attributes, "policies": policies}


class CukUnpaidSensor(CukBaseSensor):
    """Unpaid installments count sensor."""

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "unpaid_installments")

    @property
    def native_value(self) -> int:
        return sum(
            1 for _ in get_unpaid_installments(_policies(self.coordinator))
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = []
        for p, r in get_unpaid_installments(_policies(self.coordinator)):
            items.append(
                {
                    "policy_number": p.get("NumerPolisy"),
                    "insurer": p.get("Ubezpieczyciel"),
                    "due_date": r.get("TerminPlatnosci"),
                    "amount": r.get("Kwota"),
                    "installment_number": r.get("NumerRaty"),
                }
            )
        return {**super().extra_state_attributes, "payments": items}


class CukReceivablesSensor(CukBaseSensor):
    """Total unpaid receivables sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "PLN"

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "receivables")

    @property
    def native_value(self) -> float:
        return round(
            sum(
                float(r.get("Kwota", 0) or 0)
                for _, r in get_unpaid_installments(_policies(self.coordinator))
            ),
            2,
        )


class CukNextPaymentDateSensor(CukBaseSensor):
    """Next payment due date sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "next_payment_date")

    @property
    def native_value(self) -> datetime | None:
        payment = get_next_payment(_policies(self.coordinator))
        return payment[0] if payment else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        payment = get_next_payment(_policies(self.coordinator))
        if not payment:
            return super().extra_state_attributes
        _, p, r = payment
        return {
            **super().extra_state_attributes,
            "amount": r.get("Kwota"),
            "policy_number": p.get("NumerPolisy"),
            "insurer": p.get("Ubezpieczyciel"),
            "installment_number": r.get("NumerRaty"),
        }


class CukNextPaymentAmountSensor(CukBaseSensor):
    """Next payment amount sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "PLN"

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "next_payment_amount")

    @property
    def native_value(self) -> float | None:
        payment = get_next_payment(_policies(self.coordinator))
        if payment and payment[2].get("Kwota") is not None:
            return float(payment[2]["Kwota"])
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        payment = get_next_payment(_policies(self.coordinator))
        if not payment:
            return super().extra_state_attributes
        due, p, r = payment
        return {
            **super().extra_state_attributes,
            "due_date": due.isoformat(),
            "policy_number": p.get("NumerPolisy"),
            "insurer": p.get("Ubezpieczyciel"),
            "installment_number": r.get("NumerRaty"),
        }


class CukAssistantSensor(CukBaseSensor):
    """CUK supervisor details sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CukCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "assistant")

    @property
    def native_value(self) -> str | None:
        assistant = _assistant(self.coordinator)
        val = assistant.get("ImieNazwiskoOpiekuna")
        return str(val).strip() if val else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        a = _assistant(self.coordinator)
        return {
            **super().extra_state_attributes,
            "email": a.get("Email"),
            "phone": a.get("NrKontaktowyOpiekuna"),
            "branch": a.get("NazwaPlacowki"),
            "branch_address_1": a.get("AdresPlacowki1"),
            "branch_address_2": a.get("AdresPlacowki2"),
            "branch_phone": a.get("NrKontaktowyPlacowki"),
            "monday": a.get("GodzinyOtwarciaPon"),
            "tuesday": a.get("GodzinyOtwarciaWt"),
            "wednesday": a.get("GodzinyOtwarciaSr"),
            "thursday": a.get("GodzinyOtwarciaCzw"),
            "friday": a.get("GodzinyOtwarciaPt"),
            "saturday": a.get("GodzinyOtwarciaSob"),
            "sunday": a.get("GodzinyOtwarciaNd"),
        }


class CukExpiringSensor(CukBaseSensor):
    """Policies expiring within configurable days count sensor."""

    def __init__(
        self, coordinator: CukCoordinator, entry_id: str, expiring_days: int
    ) -> None:
        super().__init__(coordinator, entry_id, "expiring_policies")
        self._expiring_days = expiring_days

    @property
    def native_value(self) -> int:
        now = datetime.now(UTC)
        threshold_seconds = self._expiring_days * 86400
        return sum(
            1
            for p in get_active_policies(_policies(self.coordinator), now)
            if (end := parse_date(p.get("DataObowiazywaniaDo"), end_of_day=True))
            is not None
            and 0 <= (end - now).total_seconds() <= threshold_seconds
        )
