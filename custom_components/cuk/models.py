"""Data models and helper functions for CUK Strefa Klienta."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, SERVICE_URL


def parse_date(value: Any, end_of_day: bool = False) -> datetime | None:
    """Parse date or datetime string to UTC datetime."""
    if not value:
        return None
    try:
        val_str = str(value).strip().replace("Z", "+00:00")
        d = datetime.fromisoformat(val_str)
        if not d.tzinfo:
            d = d.replace(tzinfo=UTC)
        if end_of_day and len(val_str) <= 10:
            d = d.replace(hour=23, minute=59, second=59)
        return d
    except (TypeError, ValueError):
        return None


def get_device_info(entry_id: str) -> DeviceInfo:
    """Return standard DeviceInfo for the CUK service account."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="CUK Strefa Klienta",
        manufacturer="CUK Ubezpieczenia",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=SERVICE_URL,
    )


def is_policy_active(policy: dict[str, Any], now: datetime | None = None) -> bool:
    """Check if a policy is currently active."""
    now = now or datetime.now(UTC)
    start = parse_date(policy.get("DataObowiazywaniaOd"))
    end = parse_date(policy.get("DataObowiazywaniaDo"), end_of_day=True)
    return (
        policy.get("Status") == 0
        and start is not None
        and end is not None
        and start <= now <= end
    )


def get_active_policies(
    policies: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    """Filter and return only active policies."""
    now = now or datetime.now(UTC)
    return [p for p in policies if is_policy_active(p, now)]


def get_active_installments(
    policies: list[dict[str, Any]], now: datetime | None = None
):
    """Yield installments belonging to active policies."""
    for policy in get_active_policies(policies, now):
        for installment in policy.get("Raty") or []:
            yield policy, installment


def get_unpaid_installments(
    policies: list[dict[str, Any]], now: datetime | None = None
):
    """Yield unpaid installments belonging to active policies."""
    for policy, installment in get_active_installments(policies, now):
        if not installment.get("Zaplacona", False):
            yield policy, installment


def get_next_payment(
    policies: list[dict[str, Any]], now: datetime | None = None
) -> tuple[datetime, dict[str, Any], dict[str, Any]] | None:
    """Find the earliest unpaid installment from active policies."""
    candidates = []
    for p, r in get_unpaid_installments(policies, now):
        due = parse_date(r.get("TerminPlatnosci"))
        if due:
            candidates.append((due, p, r))
    return min(candidates, key=lambda x: x[0]) if candidates else None
