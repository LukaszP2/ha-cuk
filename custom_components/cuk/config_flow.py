from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CukApi, CukApiError
from .const import CONF_USER_ID, DOMAIN


class CukConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle CUK API-mode setup."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            user_id = str(user_input[CONF_USER_ID]).strip()
            if not user_id:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_USER_ID): str}),
                    errors={"base": "invalid_user_id"},
                )
            try:
                api = CukApi(async_get_clientsession(self.hass), user_id)
                await api.resolve_user()
                await api.get_policies()
            except CukApiError as err:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_USER_ID): str}),
                    errors={"base": "api_error"},
                    description_placeholders={"error": str(err)},
                )
            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="CUK Strefa Klienta",
                data={CONF_USER_ID: user_id},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_USER_ID): str}),
        )
