"""FRITZ!Box Calllist integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS,
    DEFAULT_REVERSE_LOOKUP_PROVIDERS,
    DOMAIN,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FRITZ!Box Calllist from a config entry."""
    _migrate_reverse_lookup_options(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _migrate_reverse_lookup_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate older reverse lookup options to provider switches."""
    if CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS in entry.options:
        return

    if not entry.options.get("reverse_lookup", False):
        return

    legacy_providers = entry.options.get("reverse_lookup_providers")
    options = dict(entry.options)
    options[CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS] = _normalize_legacy_providers(legacy_providers)
    hass.config_entries.async_update_entry(entry, options=options)


def _normalize_legacy_providers(providers: list[str] | str | None) -> list[str]:
    """Normalize older provider option values."""
    if providers is None:
        return list(DEFAULT_REVERSE_LOOKUP_PROVIDERS)

    if isinstance(providers, str):
        raw_providers = providers.split(",")
    else:
        raw_providers = providers

    normalized = [
        provider
        for provider in DEFAULT_REVERSE_LOOKUP_PROVIDERS
        if provider in {str(value).strip().casefold() for value in raw_providers}
    ]
    return normalized or list(DEFAULT_REVERSE_LOOKUP_PROVIDERS)
