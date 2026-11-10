"""Tests for CUK API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.cuk.api import (
    CukApi,
    CukApiAuthenticationError,
    CukApiError,
)


def test_validated_base_path_valid() -> None:
    assert CukApi._validated_base_path("/api/default") == "/api/default/"
    assert CukApi._validated_base_path("/api/v1/") == "/api/v1/"


def test_validated_base_path_invalid() -> None:
    with pytest.raises(CukApiError):
        CukApi._validated_base_path("http://evil.com/api")
    with pytest.raises(CukApiError):
        CukApi._validated_base_path("//evil.com/api")
    with pytest.raises(CukApiError):
        CukApi._validated_base_path("/api/../secret")


@pytest.mark.asyncio
async def test_resolve_user_success() -> None:
    session = MagicMock()
    api = CukApi(session, "test-user-id")
    api.config = {
        "defaultApi": {"baseUrl": "/api/default/", "functionKey": "key123"}
    }

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text.return_value = '{"IsSuccess": true, "Data": {"CukUserId": 12345, "CukCompanyId": 67}}'
    session.post.return_value.__aenter__.return_value = mock_resp

    data = await api.resolve_user()
    assert data["CukUserId"] == 12345
    assert api.cuk_user_id == "12345"
    assert api.cuk_company_id == 67


@pytest.mark.asyncio
async def test_resolve_user_auth_failed() -> None:
    session = MagicMock()
    api = CukApi(session, "invalid-user-id")
    api.config = {"defaultApi": {"baseUrl": "/api/default/"}}

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text.return_value = '{"IsSuccess": true, "Data": null}'
    session.post.return_value.__aenter__.return_value = mock_resp

    with pytest.raises(CukApiAuthenticationError):
        await api.resolve_user()


@pytest.mark.asyncio
async def test_get_policies_success() -> None:
    session = MagicMock()
    api = CukApi(session, "test-user-id")
    api.cuk_user_id = "12345"
    api.cuk_company_id = "67"
    api.config = {"policies": {"baseUrl": "/api/policies/"}}

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text.return_value = '{"IsSuccess": true, "Data": [{"NumerPolisy": "POL123"}]}'
    session.post.return_value.__aenter__.return_value = mock_resp

    policies = await api.get_policies()
    assert len(policies) == 1
    assert policies[0]["NumerPolisy"] == "POL123"


@pytest.mark.asyncio
async def test_api_rate_limit_429() -> None:
    session = MagicMock()
    api = CukApi(session, "test-user-id")
    api.config = {"policies": {"baseUrl": "/api/policies/"}}

    mock_resp = AsyncMock()
    mock_resp.status = 429
    mock_resp.headers = {"Retry-After": "120"}
    mock_resp.text.return_value = "Too Many Requests"
    session.post.return_value.__aenter__.return_value = mock_resp

    with pytest.raises(CukApiError) as exc_info:
        await api._post_section("policies", "GetPolicies", {})

    assert "limit zapytań przekroczony (HTTP 429" in str(exc_info.value)
    assert "Retry-After: 120" in str(exc_info.value)


@pytest.mark.asyncio
async def test_post_section_401_retry_success() -> None:
    session = MagicMock()
    api = CukApi(session, "test-user-id")
    api.config = {
        "policies": {"baseUrl": "/api/policies/", "functionKey": "old-rotated-key"}
    }
    api.load_config = AsyncMock(
        return_value={
            "policies": {"baseUrl": "/api/policies/", "functionKey": "new-fresh-key"}
        }
    )

    resp_401 = AsyncMock()
    resp_401.status = 401
    resp_401.text.return_value = "Unauthorized"

    resp_200 = AsyncMock()
    resp_200.status = 200
    resp_200.text.return_value = (
        '{"IsSuccess": true, "Data": [{"NumerPolisy": "POL456"}]}'
    )

    cm_401 = MagicMock()
    cm_401.__aenter__.return_value = resp_401
    cm_200 = MagicMock()
    cm_200.__aenter__.return_value = resp_200

    session.post.side_effect = [cm_401, cm_200]

    result = await api._post_section("policies", "GetPolicies", {})
    assert result == {"IsSuccess": True, "Data": [{"NumerPolisy": "POL456"}]}
    assert api.load_config.await_count == 1
    assert session.post.call_count == 2
    # Verify second call used the rotated key from refreshed config
    second_call_headers = session.post.call_args_list[1].kwargs["headers"]
    assert second_call_headers.get("x-functions-key") == "new-fresh-key"


@pytest.mark.asyncio
async def test_post_section_401_retry_failure() -> None:
    session = MagicMock()
    api = CukApi(session, "test-user-id")
    api.config = {
        "policies": {"baseUrl": "/api/policies/", "functionKey": "old-key"}
    }
    api.load_config = AsyncMock(
        return_value={
            "policies": {"baseUrl": "/api/policies/", "functionKey": "still-bad-key"}
        }
    )

    resp_401_first = AsyncMock()
    resp_401_first.status = 401
    resp_401_first.text.return_value = "Unauthorized"

    resp_401_second = AsyncMock()
    resp_401_second.status = 401
    resp_401_second.text.return_value = "Unauthorized"

    cm_first = MagicMock()
    cm_first.__aenter__.return_value = resp_401_first
    cm_second = MagicMock()
    cm_second.__aenter__.return_value = resp_401_second

    session.post.side_effect = [cm_first, cm_second]

    with pytest.raises(CukApiAuthenticationError) as exc_info:
        await api._post_section("policies", "GetPolicies", {})

    assert "HTTP 401" in str(exc_info.value)
    assert api.load_config.await_count == 1
    assert session.post.call_count == 2


