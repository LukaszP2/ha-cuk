"""Tests for CUK sensors and binary sensors logic."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from custom_components.cuk.binary_sensor import (
    CukPaymentDueSensor,
    CukPolicyExpiringSensor,
)
from custom_components.cuk.models import (
    get_active_installments,
    get_next_payment,
    get_unpaid_installments,
    is_policy_active,
    parse_date,
)
from custom_components.cuk.sensor import (
    CukActivePoliciesSensor,
    CukAssistantSensor,
    CukExpiringSensor,
    CukNextPaymentAmountSensor,
    CukNextPaymentDateSensor,
    CukPoliciesSensor,
    CukReceivablesSensor,
    CukUnpaidSensor,
)


def test_dt_parsing() -> None:
    assert parse_date(None) is None
    assert parse_date("invalid") is None

    # Date only parsing
    d = parse_date("2026-05-01")
    assert d is not None
    assert d.year == 2026
    assert d.month == 5
    assert d.day == 1
    assert d.hour == 0

    # Date only with end_of_day=True
    d_end = parse_date("2026-05-01", end_of_day=True)
    assert d_end is not None
    assert d_end.hour == 23
    assert d_end.minute == 59
    assert d_end.second == 59

    # ISO with timezone
    d_tz = parse_date("2026-05-01T12:00:00Z")
    assert d_tz is not None
    assert d_tz.tzinfo == UTC


def test_is_active_policy() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

    # Active policy
    p_active = {
        "Status": 0,
        "DataObowiazywaniaOd": "2026-01-01",
        "DataObowiazywaniaDo": "2026-12-31",
    }
    assert is_policy_active(p_active, now) is True

    # Expired policy
    p_expired = {
        "Status": 0,
        "DataObowiazywaniaOd": "2025-01-01",
        "DataObowiazywaniaDo": "2025-12-31",
    }
    assert is_policy_active(p_expired, now) is False

    # Inactive status
    p_canceled = {
        "Status": 1,
        "DataObowiazywaniaOd": "2026-01-01",
        "DataObowiazywaniaDo": "2026-12-31",
    }
    assert is_policy_active(p_canceled, now) is False


def test_installments_and_next_payment() -> None:
    coordinator = MagicMock()
    coordinator.data = {
        "policies": [
            # Active policy with 1 paid and 2 unpaid installments
            {
                "Status": 0,
                "NumerPolisy": "ACT-1",
                "DataObowiazywaniaOd": "2026-01-01",
                "DataObowiazywaniaDo": "2026-12-31",
                "Raty": [
                    {
                        "NumerRaty": 1,
                        "Kwota": 250.0,
                        "Zaplacona": True,
                        "TerminPlatnosci": "2026-01-10",
                    },
                    {
                        "NumerRaty": 2,
                        "Kwota": 250.0,
                        "Zaplacona": False,
                        "TerminPlatnosci": "2026-06-10",
                    },
                    {
                        "NumerRaty": 3,
                        "Kwota": 250.0,
                        "Zaplacona": False,
                        "TerminPlatnosci": "2026-09-10",
                    },
                ],
            },
            # Archived policy with old unpaid installment (should be ignored!)
            {
                "Status": 0,
                "NumerPolisy": "OLD-99",
                "DataObowiazywaniaOd": "2020-01-01",
                "DataObowiazywaniaDo": "2020-12-31",
                "Raty": [
                    {
                        "NumerRaty": 1,
                        "Kwota": 999.0,
                        "Zaplacona": False,
                        "TerminPlatnosci": "2020-05-01",
                    },
                ],
            },
        ]
    }

    policies = coordinator.data["policies"]
    # Only installments from active policies
    active_inst = list(get_active_installments(policies))
    assert len(active_inst) == 3

    unpaid = list(get_unpaid_installments(policies))
    assert len(unpaid) == 2
    assert unpaid[0][1]["NumerRaty"] == 2
    assert unpaid[1][1]["NumerRaty"] == 3

    # Next payment should be 2026-06-10, NOT the old 2020-05-01!
    next_p = get_next_payment(policies)
    assert next_p is not None
    assert next_p[0] == datetime(2026, 6, 10, 0, 0, 0, tzinfo=UTC)
    assert next_p[1]["NumerPolisy"] == "ACT-1"
    assert next_p[2]["Kwota"] == 250.0


def test_sensor_values() -> None:
    coordinator = MagicMock()
    coordinator.data = {
        "policies": [
            {
                "Status": 0,
                "NumerPolisy": "ACT-1",
                "DataObowiazywaniaOd": "2026-01-01",
                "DataObowiazywaniaDo": "2026-12-31",
                "Raty": [
                    {
                        "NumerRaty": 1,
                        "Kwota": 100.50,
                        "Zaplacona": False,
                        "TerminPlatnosci": "2026-06-15",
                    },
                    {
                        "NumerRaty": 2,
                        "Kwota": 200.25,
                        "Zaplacona": False,
                        "TerminPlatnosci": "2026-09-15",
                    },
                ],
            }
        ],
        "assistant": {
            "ImieNazwiskoOpiekuna": "Jan Kowalski",
            "Email": "jan@cuk.pl",
        },
    }

    entry_id = "test_entry"
    policies_sensor = CukPoliciesSensor(coordinator, entry_id)
    assert policies_sensor.native_value == 1
    assert policies_sensor.unique_id == "test_entry_policies"

    active_sensor = CukActivePoliciesSensor(coordinator, entry_id)
    assert active_sensor.native_value == 1

    unpaid_sensor = CukUnpaidSensor(coordinator, entry_id)
    assert unpaid_sensor.native_value == 2

    receivables_sensor = CukReceivablesSensor(coordinator, entry_id)
    assert receivables_sensor.native_value == 300.75
    # Ensure state_class is NOT TOTAL
    assert getattr(receivables_sensor, "state_class", None) is None

    next_date_sensor = CukNextPaymentDateSensor(coordinator, entry_id)
    assert next_date_sensor.native_value == datetime(
        2026, 6, 15, 0, 0, tzinfo=UTC
    )

    next_amount_sensor = CukNextPaymentAmountSensor(coordinator, entry_id)
    assert next_amount_sensor.native_value == 100.50

    assistant_sensor = CukAssistantSensor(coordinator, entry_id)
    assert assistant_sensor.native_value == "Jan Kowalski"

    # Expiring sensor count
    coordinator.data["policies"][0]["DataObowiazywaniaDo"] = "2026-06-20"
    expiring_sensor = CukExpiringSensor(coordinator, entry_id, expiring_days=30)
    assert isinstance(expiring_sensor.native_value, int)

    # Expiring binary sensor
    exp_bin_sensor = CukPolicyExpiringSensor(
        coordinator, entry_id, expiring_days=30
    )
    assert isinstance(exp_bin_sensor.is_on, bool)

    # When assistant is empty, returns None, not "Brak danych"
    coordinator.data["assistant"] = {}
    assert assistant_sensor.native_value is None


def test_binary_sensor_payment_due() -> None:
    coordinator = MagicMock()
    # Installment due in 6 months - should NOT trigger problem
    coordinator.data = {
        "policies": [
            {
                "Status": 0,
                "DataObowiazywaniaOd": "2026-01-01",
                "DataObowiazywaniaDo": "2027-12-31",
                "Raty": [
                    {"Zaplacona": False, "TerminPlatnosci": "2027-10-01"},
                ],
            }
        ]
    }
    due_sensor = CukPaymentDueSensor(coordinator, "test_entry", payment_due_days=7)
    assert due_sensor.is_on is False

    # Installment overdue or due within 7 days - should trigger problem
    coordinator.data["policies"][0]["Raty"] = [
        {"Zaplacona": False, "TerminPlatnosci": "2026-01-01"}
    ]
    assert due_sensor.is_on is True
