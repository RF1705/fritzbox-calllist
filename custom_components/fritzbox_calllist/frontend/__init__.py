"""JavaScript module registration for FRITZ!Box Calllist."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import FRONTEND_MODULES, FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Register JavaScript modules in Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the registrar."""
        self.hass = hass
        self.lovelace = self.hass.data.get("lovelace")

    async def async_register(self) -> None:
        """Register frontend resources."""
        await self._async_register_path()

        self.lovelace = self.hass.data.get("lovelace")
        if self.lovelace is None:
            _LOGGER.debug("Lovelace is not available yet; retrying")
            async_call_later(self.hass, 5, self._async_retry_register)
            return

        if getattr(self.lovelace, "mode", None) == "storage":
            await self._async_wait_for_lovelace_resources()

    async def _async_retry_register(self, _now: Any) -> None:
        """Retry frontend registration."""
        await self.async_register()

    async def _async_register_path(self) -> None:
        """Register the static HTTP path."""
        try:
            if hasattr(self.hass.http, "async_register_static_paths"):
                await self.hass.http.async_register_static_paths(
                    [
                        StaticPathConfig(
                            FRONTEND_URL_BASE,
                            str(Path(__file__).parent),
                            cache_headers=True,
                        )
                    ]
                )
            else:
                self.hass.http.register_static_path(
                    FRONTEND_URL_BASE,
                    str(Path(__file__).parent),
                    True,
                )
        except RuntimeError:
            _LOGGER.debug("Frontend path already registered: %s", FRONTEND_URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait until Lovelace resources are loaded."""

        async def check_loaded(_now: Any) -> None:
            if getattr(self.lovelace.resources, "loaded", False):
                await self._async_register_modules()
                return

            _LOGGER.debug("Lovelace resources are not loaded yet; retrying")
            async_call_later(self.hass, 5, check_loaded)

        await check_loaded(None)

    async def _async_register_modules(self) -> None:
        """Register or update JavaScript module resources."""
        existing_resources = [
            resource
            for resource in self.lovelace.resources.async_items()
            if resource["url"].split("?")[0].startswith(FRONTEND_URL_BASE)
        ]

        for module in FRONTEND_MODULES:
            path = f"{FRONTEND_URL_BASE}/{module['filename']}"
            versioned_url = f"{path}?v={module['version']}"
            existing_resource = next(
                (
                    resource
                    for resource in existing_resources
                    if resource["url"].split("?")[0] == path
                ),
                None,
            )

            if existing_resource is None:
                _LOGGER.info("Registering Lovelace resource: %s", versioned_url)
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": versioned_url}
                )
                continue

            if existing_resource["url"] != versioned_url:
                _LOGGER.info("Updating Lovelace resource: %s", versioned_url)
                await self.lovelace.resources.async_update_item(
                    existing_resource["id"],
                    {"res_type": "module", "url": versioned_url},
                )
