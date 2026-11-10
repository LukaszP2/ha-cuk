"""Asynchronous client for the CUK Strefa Klienta API."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote, urlsplit

import aiohttp

from .const import CONFIG_URL

BASE_URL = "https://strefaklienta.cuk.pl"
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/pulpit",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "WebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
}


class CukApiError(Exception):
    """Raised when the CUK API cannot return usable data."""


class CukApiAuthenticationError(CukApiError):
    """Raised when CUK rejects the configured user identifier."""


class CukApi:
    """Client for CUK's same-origin API endpoints."""

    def __init__(self, session: aiohttp.ClientSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id.strip()
        self.cuk_user_id: str | None = None
        self.cuk_company_id: str | None = None
        self.config: dict[str, Any] | None = None

    async def load_config(self) -> dict[str, Any]:
        """Fetch remote config with endpoints and Azure Function keys."""
        try:
            async with self.session.get(
                CONFIG_URL, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                response.raise_for_status()
                config = await response.json()
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
            raise CukApiError(f"Nie można pobrać konfiguracji CUK: {err}") from err
        if not isinstance(config, dict):
            raise CukApiError("CUK config endpoint returned invalid data")
        self.config = config
        return config

    @staticmethod
    def _validated_base_path(value: Any) -> str:
        """Accept only a same-origin absolute path from the remote config."""
        if not isinstance(value, str) or not value.startswith("/"):
            raise CukApiError("CUK config contains an invalid API base path")
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or value.startswith("//"):
            raise CukApiError("CUK API base path must be same-origin")
        decoded_path = unquote(parsed.path)
        if ".." in decoded_path.replace("\\", "/").split("/"):
            raise CukApiError("CUK API base path contains an invalid segment")
        return value.rstrip("/") + "/"

    async def _post_section(self, section: str, endpoint: str, payload: Any) -> Any:
        for attempt in range(2):
            if self.config is None:
                self.config = await self.load_config()
            config = self.config or {}
            section_config = config.get(section, {})
            if section == "default":
                section_config = config.get("defaultApi", section_config)
            if not isinstance(section_config, dict):
                raise CukApiError(f"CUK config section '{section}' is invalid")
            base_path = self._validated_base_path(
                section_config.get("baseUrl", "/api/default/")
            )
            function_key = section_config.get("functionKey")
            headers = DEFAULT_HEADERS.copy()
            if (
                isinstance(function_key, str)
                and function_key
                and function_key != "undefined"
            ):
                headers["x-functions-key"] = function_key
            safe_endpoint = endpoint.lstrip("/")
            if ".." in safe_endpoint.split("/"):
                raise CukApiError("Invalid CUK API endpoint")
            url = f"{BASE_URL}{base_path}{safe_endpoint}"
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    body = await response.text()
                    if response.status == 401 and attempt == 0:
                        self.config = None
                        self.config = await self.load_config()
                        continue
                    if response.status in (401, 403):
                        self.config = None
                        raise CukApiAuthenticationError(
                            f"{endpoint}: CUK odrzucił identyfikator użytkownika (HTTP {response.status})"
                        )
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After", "unknown")
                        raise CukApiError(
                            f"{endpoint}: limit zapytań przekroczony (HTTP 429, Retry-After: {retry_after})"
                        )
                    if response.status != 200:
                        raise CukApiError(
                            f"{endpoint}: HTTP {response.status}: {body[:500]}"
                        )
                    try:
                        result = json.loads(body)
                    except json.JSONDecodeError as err:
                        raise CukApiError(f"{endpoint}: invalid JSON response") from err
            except CukApiError:
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                raise CukApiError(f"{endpoint}: błąd połączenia z CUK: {err}") from err
            if isinstance(result, dict) and result.get("IsSuccess") is False:
                code = result.get("Code")
                message = result.get("Message")
                if str(code) in {"401", "403", "Unauthorized", "Forbidden"}:
                    self.config = None
                    raise CukApiAuthenticationError(f"{endpoint}: {message or code}")
                raise CukApiError(
                    f"{endpoint}: API error: {message or code or 'unknown error'}"
                )
            return result

    async def resolve_user(self) -> dict[str, Any]:
        """Resolve CUK internal IDs from the Azure B2C ObjectId."""
        result = await self._post_section(
            "default", "b2c/GetUser", {"id": self.user_id}
        )
        data = result.get("Data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            raise CukApiAuthenticationError(
                "CUK nie zwrócił danych użytkownika dla podanego ObjectId"
            )
        cuk_user_id = data.get("CukUserId")
        if not cuk_user_id:
            raise CukApiAuthenticationError(
                "CUK nie zwrócił CukUserId dla podanego ObjectId"
            )
        self.cuk_user_id = str(cuk_user_id)
        self.cuk_company_id = data.get("CukCompanyId")
        return data

    async def _post_api(self, section: str, endpoint: str, data: Any) -> Any:
        if not self.cuk_user_id:
            await self.resolve_user()
        return await self._post_section(
            section, endpoint, {"data": data, "userId": self.user_id}
        )

    async def get_policies(self) -> list[dict[str, Any]]:
        """Fetch all policies for the user."""
        if not self.cuk_user_id:
            await self.resolve_user()
        variants = (
            {"cukUserId": self.cuk_user_id, "cukCompanyId": self.cuk_company_id},
            {"cukUserId": self.cuk_user_id},
        )
        attempts: list[str] = []
        for data in variants:
            try:
                result = await self._post_section(
                    "policies", "GetPolicies", {"data": data, "userId": self.user_id}
                )
                policies = result.get("Data", []) if isinstance(result, dict) else []
                if not isinstance(policies, list):
                    raise CukApiError("GetPolicies returned an invalid data structure")
                return [item for item in policies if isinstance(item, dict)]
            except CukApiAuthenticationError:
                raise
            except CukApiError as err:
                attempts.append(str(err))
        raise CukApiError(
            f"GetPolicies failed for all payload variants: {'; '.join(attempts)}"
        )

    async def get_assistant(self) -> Any:
        """Fetch client assistant details."""
        if not self.cuk_user_id:
            await self.resolve_user()
        result = await self._post_api("user", "GetClientAssistant", self.cuk_user_id)
        return result.get("Data", result) if isinstance(result, dict) else result
