"""FRITZ!Box Calllist integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import CoreState, EVENT_HOMEASSISTANT_STARTED, HomeAssistant
from homeassistant.helpers.typing import ConfigType

from . import frontend
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up static frontend assets."""
    await _async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FRITZ!Box Calllist from a config entry."""
    await _async_register_frontend(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the Lovelace card module."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("frontend_registered") or domain_data.get("frontend_registering"):
        return
    domain_data["frontend_registering"] = True

    async def register_frontend() -> None:
        await frontend.JSModuleRegistration(hass).async_register()
        hass.data[DOMAIN]["frontend_registered"] = True
        hass.data[DOMAIN]["frontend_registering"] = False

    if hass.state == CoreState.running:
        await register_frontend()
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            lambda _: hass.async_create_task(register_frontend()),
        )
