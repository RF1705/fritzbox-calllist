"""Frontend registration for FRITZ!Box Calllist."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Final

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from ..const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

_FRONTEND_DIR: Final = Path(__file__).parent
_CARD_FILE_NAME: Final = "fritzbox-calllist-card.js"
_CARD_FILE: Final = _FRONTEND_DIR / _CARD_FILE_NAME
_STATIC_PATH_REGISTERED_KEY: Final = f"{DOMAIN}_card_static_path_registered"
_CARD_REGISTERED_KEY: Final = f"{DOMAIN}_card_registered"


def _build_card_url() -> str:
    """Build a cache-busted card URL."""
    file_hash = hashlib.md5(_CARD_FILE.read_bytes()).hexdigest()[:8]  # noqa: S324
    return f"/{DOMAIN}/fritzbox-calllist-card-{file_hash}.js"


CARD_URL: Final = _build_card_url()
FALLBACK_CARD_URL: Final = f"/{DOMAIN}/{_CARD_FILE_NAME}"


async def _async_register_static_paths(hass: HomeAssistant) -> None:
    """Register static paths for the Lovelace card."""
    if hass.data.get(_STATIC_PATH_REGISTERED_KEY):
        return

    if not _CARD_FILE.exists():
        _LOGGER.warning("Card frontend file not found at %s", _CARD_FILE)
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(_CARD_FILE), cache_headers=True),
            StaticPathConfig(FALLBACK_CARD_URL, str(_CARD_FILE), cache_headers=True),
        ]
    )
    hass.data[_STATIC_PATH_REGISTERED_KEY] = True


async def async_register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace card with the Home Assistant frontend."""
    if hass.data.get(_CARD_REGISTERED_KEY):
        return

    await _async_register_static_paths(hass)

    if not hass.data.get(_STATIC_PATH_REGISTERED_KEY):
        return

    if frontend.DATA_EXTRA_MODULE_URL not in hass.data:
        _LOGGER.debug("Frontend is not initialized yet. Deferring card registration")

        @callback
        def _retry_register_card(event: Any = None) -> None:
            """Retry card registration after startup."""
            if hass.data.get(_CARD_REGISTERED_KEY):
                return
            if frontend.DATA_EXTRA_MODULE_URL not in hass.data:
                _LOGGER.warning("Frontend still not available after startup. Skipping card registration")
                return
            frontend.add_extra_js_url(hass, CARD_URL)
            hass.data[_CARD_REGISTERED_KEY] = True
            _LOGGER.debug("Registered FRITZ!Box Calllist card at %s", CARD_URL)

        hass.bus.async_listen_once("homeassistant_started", _retry_register_card)
        return

    frontend.add_extra_js_url(hass, CARD_URL)
    hass.data[_CARD_REGISTERED_KEY] = True
    _LOGGER.debug("Registered FRITZ!Box Calllist card at %s", CARD_URL)


def async_unregister_card(hass: HomeAssistant) -> None:
    """Unregister the Lovelace card from the frontend."""
    if not hass.data.get(_CARD_REGISTERED_KEY):
        return

    if (url_manager := hass.data.get(frontend.DATA_EXTRA_MODULE_URL)) is not None:
        if CARD_URL in url_manager.urls:
            frontend.remove_extra_js_url(hass, CARD_URL)

    hass.data.pop(_CARD_REGISTERED_KEY, None)
