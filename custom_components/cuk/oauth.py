from __future__ import annotations

from homeassistant.helpers import config_entry_oauth2_flow

from .const import AUTHORIZE_URL, CLIENT_ID, DOMAIN, OAUTH_SCOPE, TOKEN_URL


class CukOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2ImplementationWithPkce):
    """Experimental OAuth2/PKCE implementation for CUK Azure B2C."""

    def __init__(self, hass):
        super().__init__(
            hass,
            DOMAIN,
            CLIENT_ID,
            AUTHORIZE_URL,
            TOKEN_URL,
        )

    @property
    def name(self) -> str:
        return "CUK Azure B2C"

    @property
    def redirect_uri(self) -> str:
        """Return the Home Assistant callback, never the CUK frontend URL."""
        external_url = getattr(self.hass.config, "external_url", None)
        if external_url:
            return f"{external_url.rstrip('/')}/auth/external/callback"
        return super().redirect_uri

    @property
    def extra_authorize_data(self) -> dict:
        data = super().extra_authorize_data
        data.update(
            {
                "scope": OAUTH_SCOPE,
                "response_type": "code",
                "response_mode": "query",
            }
        )
        return data
