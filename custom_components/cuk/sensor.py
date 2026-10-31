from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CukCoordinator


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _device_info() -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, "cuk")},
        "name": "CUK Strefa Klienta",
        "manufacturer": "CUK Ubezpieczenia",
    }


def _policies(coordinator: CukCoordinator) -> list[dict[str, Any]]:
    data = coordinator.data or {}
    return data.get("policies", []) if isinstance(data, dict) else []


def _assistant(coordinator: CukCoordinator) -> dict[str, Any]:
    data = coordinator.data or {}
    value = data.get("assistant") if isinstance(data, dict) else None
    return value if isinstance(value, dict) else {}


def _is_active(policy: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    start = _dt(policy.get("DataObowiazywaniaOd"))
    end = _dt(policy.get("DataObowiazywaniaDo"))
    # In CUK data Status=0 marks the current policy set. Keep the date check as
    # an additional guard so a stale/future record is not exposed as active.
    return (
        policy.get("Status") == 0
        and start is not None
        and end is not None
        and start <= now <= end
    )


def _active_policies(coordinator: CukCoordinator) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [p for p in _policies(coordinator) if _is_active(p, now)]


def _installments(coordinator: CukCoordinator):
    for policy in _policies(coordinator):
        for installment in policy.get("Raty") or []:
            yield policy, installment


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CukCoordinator = entry.runtime_data
    async_add_entities(
        [
            CukPoliciesSensor(coordinator),
            CukActivePoliciesSensor(coordinator),
            CukUnpaidSensor(coordinator),
            CukReceivablesSensor(coordinator),
            CukNextPaymentDateSensor(coordinator),
            CukNextPaymentAmountSensor(coordinator),
            CukExpiringSensor(coordinator),
            CukAssistantSensor(coordinator),
        ]
    )


class CukBaseSensor(SensorEntity):
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


class CukPoliciesSensor(CukBaseSensor):
    _attr_native_unit_of_measurement = "szt."

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_policies", "Polisy")

    @property
    def native_value(self) -> Any:
        return len(_policies(self.coordinator))


class CukActivePoliciesSensor(CukBaseSensor):
    _attr_native_unit_of_measurement = "szt."

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_active_policies", "Aktywne polisy")

    @property
    def native_value(self) -> Any:
        return len(_active_policies(self.coordinator))

    @property
    def extra_state_attributes(self):
        # Details are intentionally exposed only for currently active policies.
        policies = []
        for p in _active_policies(self.coordinator):
            policies.append({
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
            })
        return {**super().extra_state_attributes, "policies": policies}


class CukUnpaidSensor(CukBaseSensor):
    _attr_native_unit_of_measurement = "szt."

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_unpaid_installments", "Niezapłacone raty")

    @property
    def native_value(self) -> Any:
        return sum(
            1 for _, r in _installments(self.coordinator)
            if not r.get("Zaplacona", False)
        )

    @property
    def extra_state_attributes(self):
        items = []
        for p, r in _installments(self.coordinator):
            if r.get("Zaplacona", False):
                continue
            items.append({
                "policy_number": p.get("NumerPolisy"),
                "insurer": p.get("Ubezpieczyciel"),
                "due_date": r.get("TerminPlatnosci"),
                "amount": r.get("Kwota"),
                "installment_number": r.get("NumerRaty"),
            })
        return {**super().extra_state_attributes, "payments": items}


class CukReceivablesSensor(CukBaseSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "PLN"

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_receivables", "Należności")

    @property
    def native_value(self) -> Any:
        return round(sum(
            float(r.get("Kwota", 0) or 0)
            for _, r in _installments(self.coordinator)
            if not r.get("Zaplacona", False)
        ), 2)


class _NextPaymentBase(CukBaseSensor):
    def _next_payment(self) -> tuple[datetime, dict[str, Any], dict[str, Any]] | None:
        candidates = []
        for p, r in _installments(self.coordinator):
            if r.get("Zaplacona", False):
                continue
            due = _dt(r.get("TerminPlatnosci"))
            if due:
                candidates.append((due, p, r))
        return min(candidates, key=lambda x: x[0]) if candidates else None


class CukNextPaymentDateSensor(_NextPaymentBase):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_next_payment_date", "Termin najbliższej płatności")

    @property
    def native_value(self) -> Any:
        payment = self._next_payment()
        return payment[0] if payment else None

    @property
    def extra_state_attributes(self):
        payment = self._next_payment()
        if not payment:
            return super().extra_state_attributes
        _due, p, r = payment
        return {
            **super().extra_state_attributes,
            "amount": r.get("Kwota"),
            "policy_number": p.get("NumerPolisy"),
            "insurer": p.get("Ubezpieczyciel"),
            "installment_number": r.get("NumerRaty"),
        }


class CukNextPaymentAmountSensor(_NextPaymentBase):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "PLN"

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_next_payment_amount", "Kwota najbliższej płatności")

    @property
    def native_value(self) -> Any:
        payment = self._next_payment()
        return payment[2].get("Kwota") if payment else None

    @property
    def extra_state_attributes(self):
        payment = self._next_payment()
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
    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_assistant", "Opiekun CUK")

    @property
    def native_value(self) -> Any:
        assistant = _assistant(self.coordinator)
        return assistant.get("ImieNazwiskoOpiekuna") or "Brak danych"

    @property
    def extra_state_attributes(self):
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
    _attr_native_unit_of_measurement = "szt."

    def __init__(self, coordinator: CukCoordinator) -> None:
        super().__init__(coordinator, "cuk_expiring_policies", "Polisy wygasające")

    @property
    def native_value(self) -> Any:
        now = datetime.now(timezone.utc)
        return sum(
            0 <= (end - now).total_seconds() <= 30 * 86400
            for p in _active_policies(self.coordinator)
            if (end := _dt(p.get("DataObowiazywaniaDo"))) is not None
        )
