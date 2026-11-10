"""Constants for the CUK integration."""

from typing import Final

DOMAIN: Final = "cuk"
CONF_USER_ID: Final = "user_id"
CONFIG_URL: Final = "https://strefaklienta.cuk.pl/config.json"
SERVICE_URL: Final = "https://strefaklienta.cuk.pl"
DEFAULT_SCAN_INTERVAL: Final = 30 * 60
PLATFORMS: Final = ["sensor", "binary_sensor"]

CONF_EXPIRING_DAYS: Final = "expiring_days"
DEFAULT_EXPIRING_DAYS: Final = 30

CONF_PAYMENT_DUE_DAYS: Final = "payment_due_days"
DEFAULT_PAYMENT_DUE_DAYS: Final = 7
