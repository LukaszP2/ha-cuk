"""Config flow for CUK Strefa Klienta."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CukApi, CukApiError
from .const import (
    CONF_EXPIRING_DAYS,
    CONF_PAYMENT_DUE_DAYS,
    CONF_USER_ID,
    DEFAULT_EXPIRING_DAYS,
    DEFAULT_PAYMENT_DUE_DAYS,
    DOMAIN,
)


class CukConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle CUK API-mode setup."""

    VERSION = 1
    _reauth_entry: ConfigEntry
    _reconfigure_entry: ConfigEntry

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Return the options flow handler."""
        return CukOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle initial user setup."""
        schema = vol.Schema({vol.Required(CONF_USER_ID): str})
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema)

        user_id = user_input[CONF_USER_ID].strip().lower()
        if not user_id:
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                errors={"base": "invalid_user_id"},
            )
        try:
            api = CukApi(async_get_clientsession(self.hass), user_id)
            await api.resolve_user()
            await api.get_policies()
        except CukApiError as err:
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                errors={"base": "api_error"},
                description_placeholders={"error": str(err)},
            )
        await self.async_set_unique_id(user_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="CUK Strefa Klienta",
            data={CONF_USER_ID: user_id},
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when CUK rejects the configured ObjectId."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Validate and save the replacement ObjectId."""
        default_user_id = self._reauth_entry.data.get(CONF_USER_ID, "")
        schema = vol.Schema({vol.Required(CONF_USER_ID, default=default_user_id): str})
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm", data_schema=schema)

        user_id = user_input[CONF_USER_ID].strip().lower()
        if not user_id:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                errors={"base": "invalid_user_id"},
            )
        try:
            api = CukApi(async_get_clientsession(self.hass), user_id)
            await api.resolve_user()
            await api.get_policies()
        except CukApiError as err:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                errors={"base": "api_error"},
                description_placeholders={"error": str(err)},
            )

        await self.async_set_unique_id(user_id)
        self._abort_if_unique_id_configured()
        return self.async_update_reload_and_abort(
            self._reauth_entry,
            unique_id=user_id,
            data_updates={CONF_USER_ID: user_id},
            reason="reauth_successful",
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start reconfiguration to update credentials or options."""
        self._reconfigure_entry = self._get_reconfigure_entry()
        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Validate and update the reconfigured ObjectId."""
        default_user_id = self._reconfigure_entry.data.get(CONF_USER_ID, "")
        schema = vol.Schema({vol.Required(CONF_USER_ID, default=default_user_id): str})
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure_confirm", data_schema=schema
            )

        user_id = user_input[CONF_USER_ID].strip().lower()
        if not user_id:
            return self.async_show_form(
                step_id="reconfigure_confirm",
                data_schema=schema,
                errors={"base": "invalid_user_id"},
            )
        try:
            api = CukApi(async_get_clientsession(self.hass), user_id)
            await api.resolve_user()
            await api.get_policies()
        except CukApiError as err:
            return self.async_show_form(
                step_id="reconfigure_confirm",
                data_schema=schema,
                errors={"base": "api_error"},
                description_placeholders={"error": str(err)},
            )

        await self.async_set_unique_id(user_id)
        self._abort_if_unique_id_configured()
        return self.async_update_reload_and_abort(
            self._reconfigure_entry,
            unique_id=user_id,
            data_updates={CONF_USER_ID: user_id},
            reason="reconfigure_successful",
        )


class CukOptionsFlowHandler(OptionsFlow):
    """Handle CUK options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage CUK options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_expiring = self.config_entry.options.get(
            CONF_EXPIRING_DAYS, DEFAULT_EXPIRING_DAYS
        )
        current_payment_due = self.config_entry.options.get(
            CONF_PAYMENT_DUE_DAYS, DEFAULT_PAYMENT_DUE_DAYS
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_EXPIRING_DAYS, default=current_expiring): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=180)
                ),
                vol.Optional(
                    CONF_PAYMENT_DUE_DAYS, default=current_payment_due
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
