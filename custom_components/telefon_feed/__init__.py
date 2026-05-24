"""Telefon Feed integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

FRONTEND_PATH = Path(__file__).parent / "frontend"
FRONTEND_URL = "/telefon_feed/telefon-feed-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up static frontend assets."""
    await _async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Telefon Feed from a config entry."""
    await _async_register_frontend(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the Lovelace card module."""
    if hass.data.setdefault(DOMAIN, {}).get("frontend_registered"):
        return

    if hasattr(hass.http, "async_register_static_paths"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/telefon_feed",
                    str(FRONTEND_PATH),
                    cache_headers=True,
                )
            ]
        )
    else:
        hass.http.register_static_path("/telefon_feed", str(FRONTEND_PATH), True)

    if hasattr(frontend, "async_register_extra_module_url"):
        frontend.async_register_extra_module_url(hass, FRONTEND_URL)
    else:
        extra_modules = hass.data.setdefault("frontend_extra_module_url", set())
        extra_modules.add(FRONTEND_URL)

    hass.data[DOMAIN]["frontend_registered"] = True
