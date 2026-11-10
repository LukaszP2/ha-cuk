"""Tests for CUK config flow and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.cuk.const import (
    CONF_EXPIRING_DAYS,
    CONF_PAYMENT_DUE_DAYS,
    CONF_USER_ID,
)


@pytest.mark.asyncio
async def test_flow_user_form() -> None:
    hass = MagicMock(spec=HomeAssistant)
    from custom_components.cuk.config_flow import CukConfigFlow

    flow = CukConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result.get("type") == data_entry_flow.FlowResultType.FORM
    assert result.get("step_id") == "user"


@pytest.mark.asyncio
async def test_flow_user_empty_id() -> None:
    hass = MagicMock(spec=HomeAssistant)
    from custom_components.cuk.config_flow import CukConfigFlow

    flow = CukConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user({CONF_USER_ID: "   "})
    assert result.get("type") == data_entry_flow.FlowResultType.FORM
    assert result.get("errors") == {"base": "invalid_user_id"}


@pytest.mark.asyncio
async def test_flow_user_success() -> None:
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    from custom_components.cuk.config_flow import CukConfigFlow

    flow = CukConfigFlow()
    flow.hass = hass
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    with (
        patch("custom_components.cuk.config_flow.async_get_clientsession"),
        patch("custom_components.cuk.config_flow.CukApi") as mock_api_cls,
    ):
        mock_api = mock_api_cls.return_value
        mock_api.resolve_user = AsyncMock()
        mock_api.get_policies = AsyncMock(return_value=[])

        result = await flow.async_step_user({CONF_USER_ID: "my-valid-user-id"})

        assert result.get("type") == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result.get("title") == "CUK Strefa Klienta"
        assert result.get("data") == {CONF_USER_ID: "my-valid-user-id"}


@pytest.mark.asyncio
async def test_flow_reauth_confirm_success() -> None:
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    from custom_components.cuk.config_flow import CukConfigFlow

    flow = CukConfigFlow()
    flow.hass = hass
    mock_entry = MagicMock()
    mock_entry.data = {CONF_USER_ID: "old-user-id"}
    flow._reauth_entry = mock_entry
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_update_reload_and_abort = MagicMock(
        return_value={
            "type": data_entry_flow.FlowResultType.ABORT,
            "reason": "reauth_successful",
        }
    )

    with (
        patch("custom_components.cuk.config_flow.async_get_clientsession"),
        patch("custom_components.cuk.config_flow.CukApi") as mock_api_cls,
    ):
        mock_api = mock_api_cls.return_value
        mock_api.resolve_user = AsyncMock()
        mock_api.get_policies = AsyncMock(return_value=[])

        result = await flow.async_step_reauth_confirm(
            {CONF_USER_ID: "new-user-id"}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.ABORT
        assert result.get("reason") == "reauth_successful"
        flow.async_update_reload_and_abort.assert_called_once_with(
            mock_entry,
            unique_id="new-user-id",
            data_updates={CONF_USER_ID: "new-user-id"},
            reason="reauth_successful",
        )


@pytest.mark.asyncio
async def test_flow_reconfigure_confirm_success() -> None:
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    from custom_components.cuk.config_flow import CukConfigFlow

    flow = CukConfigFlow()
    flow.hass = hass
    mock_entry = MagicMock()
    mock_entry.data = {CONF_USER_ID: "old-user-id"}
    flow._reconfigure_entry = mock_entry
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_update_reload_and_abort = MagicMock(
        return_value={
            "type": data_entry_flow.FlowResultType.ABORT,
            "reason": "reconfigure_successful",
        }
    )

    with (
        patch("custom_components.cuk.config_flow.async_get_clientsession"),
        patch("custom_components.cuk.config_flow.CukApi") as mock_api_cls,
    ):
        mock_api = mock_api_cls.return_value
        mock_api.resolve_user = AsyncMock()
        mock_api.get_policies = AsyncMock(return_value=[])

        result = await flow.async_step_reconfigure_confirm(
            {CONF_USER_ID: "reconfigured-user-id"}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.ABORT
        assert result.get("reason") == "reconfigure_successful"
        flow.async_update_reload_and_abort.assert_called_once_with(
            mock_entry,
            unique_id="reconfigured-user-id",
            data_updates={CONF_USER_ID: "reconfigured-user-id"},
            reason="reconfigure_successful",
        )


@pytest.mark.asyncio
async def test_options_flow() -> None:
    hass = MagicMock(spec=HomeAssistant)
    from custom_components.cuk.config_flow import (
        CukConfigFlow,
        CukOptionsFlowHandler,
    )

    mock_entry = MagicMock()
    mock_entry.options = {CONF_EXPIRING_DAYS: 45, CONF_PAYMENT_DUE_DAYS: 10}

    # Verify options flow getter
    handler = CukConfigFlow.async_get_options_flow(mock_entry)
    assert isinstance(handler, CukOptionsFlowHandler)

    handler.hass = hass
    handler.handler = "test_entry"
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_known_entry.return_value = mock_entry

    # Form step
    form_res = await handler.async_step_init()
    assert form_res.get("type") == data_entry_flow.FlowResultType.FORM
    assert form_res.get("step_id") == "init"

    # Submit step
    submit_res = await handler.async_step_init(
        {CONF_EXPIRING_DAYS: 60, CONF_PAYMENT_DUE_DAYS: 14}
    )
    assert submit_res.get("type") == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert submit_res.get("data") == {
        CONF_EXPIRING_DAYS: 60,
        CONF_PAYMENT_DUE_DAYS: 14,
    }


@pytest.mark.asyncio
async def test_flow_user_uppercase_normalization() -> None:
    """Test that uppercase letters and whitespace in user_id are normalized to lowercase."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    from custom_components.cuk.config_flow import CukConfigFlow

    flow = CukConfigFlow()
    flow.hass = hass
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    with (
        patch("custom_components.cuk.config_flow.async_get_clientsession"),
        patch("custom_components.cuk.config_flow.CukApi") as mock_api_cls,
    ):
        mock_api = mock_api_cls.return_value
        mock_api.resolve_user = AsyncMock()
        mock_api.get_policies = AsyncMock(return_value=[])

        result = await flow.async_step_user({CONF_USER_ID: "  MY-VALID-USER-ID-1234-ABCD  "})

        assert result.get("type") == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result.get("title") == "CUK Strefa Klienta"
        assert result.get("data") == {CONF_USER_ID: "my-valid-user-id-1234-abcd"}
        flow.async_set_unique_id.assert_called_once_with("my-valid-user-id-1234-abcd")


@pytest.mark.asyncio
async def test_flow_reauth_reconfigure_uppercase_normalization() -> None:
    """Test that reauth and reconfigure normalize uppercase user_id."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    from custom_components.cuk.config_flow import CukConfigFlow

    # Reauth confirm
    flow = CukConfigFlow()
    flow.hass = hass
    mock_entry = MagicMock()
    mock_entry.data = {CONF_USER_ID: "old-user-id"}
    flow._reauth_entry = mock_entry
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_update_reload_and_abort = MagicMock(
        return_value={
            "type": data_entry_flow.FlowResultType.ABORT,
            "reason": "reauth_successful",
        }
    )

    with (
        patch("custom_components.cuk.config_flow.async_get_clientsession"),
        patch("custom_components.cuk.config_flow.CukApi") as mock_api_cls,
    ):
        mock_api = mock_api_cls.return_value
        mock_api.resolve_user = AsyncMock()
        mock_api.get_policies = AsyncMock(return_value=[])

        result = await flow.async_step_reauth_confirm(
            {CONF_USER_ID: "  NEW-USER-ID-ABCD  "}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.ABORT
        flow.async_update_reload_and_abort.assert_called_once_with(
            mock_entry,
            unique_id="new-user-id-abcd",
            data_updates={CONF_USER_ID: "new-user-id-abcd"},
            reason="reauth_successful",
        )

    # Reconfigure confirm
    flow_reconf = CukConfigFlow()
    flow_reconf.hass = hass
    flow_reconf._reconfigure_entry = mock_entry
    flow_reconf.async_set_unique_id = AsyncMock()
    flow_reconf._abort_if_unique_id_configured = MagicMock()
    flow_reconf.async_update_reload_and_abort = MagicMock(
        return_value={
            "type": data_entry_flow.FlowResultType.ABORT,
            "reason": "reconfigure_successful",
        }
    )

    with (
        patch("custom_components.cuk.config_flow.async_get_clientsession"),
        patch("custom_components.cuk.config_flow.CukApi") as mock_api_cls,
    ):
        mock_api = mock_api_cls.return_value
        mock_api.resolve_user = AsyncMock()
        mock_api.get_policies = AsyncMock(return_value=[])

        result_reconf = await flow_reconf.async_step_reconfigure_confirm(
            {CONF_USER_ID: "  RECONFIGURED-USER-ID-EFGH  "}
        )

        assert result_reconf.get("type") == data_entry_flow.FlowResultType.ABORT
        flow_reconf.async_update_reload_and_abort.assert_called_once_with(
            mock_entry,
            unique_id="reconfigured-user-id-efgh",
            data_updates={CONF_USER_ID: "reconfigured-user-id-efgh"},
            reason="reconfigure_successful",
        )
