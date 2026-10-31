from __future__ import annotations

from typing import Any

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
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
}


class CukApiError(Exception):
    """Raised when the CUK API cannot return usable data."""


class CukApi:
    """Client for the CUK Strefa Klienta API."""

    def __init__(self, session: aiohttp.ClientSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id.strip()
        self.cuk_user_id: str | None = None
        self.cuk_company_id: str | None = None
        self.config: dict[str, Any] | None = None

    async def load_config(self) -> dict[str, Any]:
        async with self.session.get(
            CONFIG_URL, timeout=aiohttp.ClientTimeout(total=20)
        ) as response:
            response.raise_for_status()
            config = await response.json()
            if not isinstance(config, dict):
                raise CukApiError("CUK config endpoint returned invalid data")
            self.config = config
            return config

    async def _post_section(
        self, section: str, endpoint: str, payload: Any
    ) -> Any:
        if self.config is None:
            await self.load_config()

        config = self.config or {}
        section_config = config.get(section, {})
        if section == "default":
            section_config = config.get("defaultApi", section_config)

        base_url = section_config.get("baseUrl", "/api/default/")
        function_key = section_config.get("functionKey")
        headers = DEFAULT_HEADERS.copy()
        if function_key and function_key != "undefined":
            headers["x-functions-key"] = function_key

        url = f"{BASE_URL}{base_url}{endpoint}"
        async with self.session.post(
            url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            text = await response.text()
            if response.status != 200:
                raise CukApiError(
                    f"{endpoint}: HTTP {response.status}: {text[:500]}"
                )
            try:
                result = await response.json()
            except Exception as err:
                raise CukApiError(f"{endpoint}: invalid JSON") from err

        if isinstance(result, dict) and result.get("IsSuccess") is False:
            detail = {
                "IsSuccess": result.get("IsSuccess"),
                "Message": result.get("Message"),
                "Code": result.get("Code"),
            }
            raise CukApiError(f"{endpoint}: API error: {detail}")
        return result

    async def resolve_user(self) -> dict[str, Any]:
        result = await self._post_section(
            "default", "b2c/GetUser", {"id": self.user_id}
        )
        data = result.get("Data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            raise CukApiError("CUK nie zwrócił danych użytkownika")

        cuk_user_id = data.get("CukUserId")
        if not cuk_user_id:
            raise CukApiError(
                "CUK nie zwrócił CukUserId dla podanego ObjectId"
            )

        self.cuk_user_id = str(cuk_user_id)
        self.cuk_company_id = data.get("CukCompanyId")
        return data

    async def _post_api(
        self, section: str, endpoint: str, data: Any
    ) -> Any:
        if not self.cuk_user_id:
            await self.resolve_user()
        return await self._post_section(
            section, endpoint, {"data": data, "userId": self.user_id}
        )

    async def get_policies(self) -> list[dict[str, Any]]:
        """Return policies using the payload variants observed in the web app."""
        if not self.cuk_user_id:
            await self.resolve_user()

        variants = (
            {"cukUserId": self.cuk_user_id, "cukCompanyId": self.cuk_company_id},
            {"cukUserId": self.cuk_user_id},
        )
        attempts: list[dict[str, Any]] = []
        for data in variants:
            try:
                result = await self._post_section(
                    "policies",
                    "GetPolicies",
                    {"data": data, "userId": self.user_id},
                )
                return result.get("Data", []) if isinstance(result, dict) else []
            except CukApiError as err:
                attempts.append({"payload_keys": list(data), "error": str(err)})

        raise CukApiError(
            f"GetPolicies failed for all payload variants: {attempts}"
        )

    async def get_assistant(self) -> Any:
        if not self.cuk_user_id:
            await self.resolve_user()
        result = await self._post_api(
            "user", "GetClientAssistant", self.cuk_user_id
        )
        if isinstance(result, dict) and isinstance(result.get("Data"), dict):
            return result["Data"]
        return result

    async def get_calculations(self) -> Any:
        if not self.cuk_user_id:
            await self.resolve_user()
        result = await self._post_api(
            "calculations", "GetClientCalculations", self.cuk_user_id
        )
        if isinstance(result, dict) and "Data" in result:
            return result["Data"]
        return result

    async def get_custom_policies(self) -> Any:
        if not self.cuk_user_id:
            await self.resolve_user()
        return await self._post_section(
            "default",
            "custom-policies/GetAll",
            {
                "ownerId": self.user_id,
                "customPoliciesFilter": 0,
                "checksum": "fcctq/OP/Sun5pA",
            },
        )

    async def test(self) -> list[dict[str, Any]]:
        await self.resolve_user()
        return await self.get_policies()
