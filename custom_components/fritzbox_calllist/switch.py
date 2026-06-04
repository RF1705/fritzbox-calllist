"""Switch platform for FRITZ!Box Calllist."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS,
    DEFAULT_REVERSE_LOOKUP_PROVIDERS,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FRITZ!Box Calllist switches."""
    async_add_entities(
        [
            FritzboxCalllistReverseLookupProviderSwitch(hass, entry, provider)
            for provider in DEFAULT_REVERSE_LOOKUP_PROVIDERS
        ]
    )


class FritzboxCalllistReverseLookupProviderSwitch(SwitchEntity):
    """Switch for one optional reverse lookup provider."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:account-search"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, provider: str) -> None:
        """Initialize the switch."""
        self.hass = hass
        self.entry = entry
        self.provider = provider
        self._attr_name = f"Reverse lookup {provider}"
        self._attr_unique_id = f"{entry.entry_id}_reverse_lookup_{provider.replace('.', '_')}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the integration device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.title,
            manufacturer="RF1705",
            model="Calllist",
        )

    @property
    def is_on(self) -> bool:
        """Return true if this provider is enabled."""
        return self.provider in self._enabled_providers

    async def async_turn_on(self, **kwargs) -> None:
        """Enable this provider."""
        enabled_providers = self._enabled_providers
        if self.provider not in enabled_providers:
            enabled_providers.append(self.provider)
        await self._async_save_enabled_providers(enabled_providers)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable this provider."""
        enabled_providers = self._enabled_providers
        if self.provider in enabled_providers:
            enabled_providers.remove(self.provider)
        await self._async_save_enabled_providers(enabled_providers)

    @property
    def _enabled_providers(self) -> list[str]:
        """Return enabled providers."""
        return list(
            self.entry.options.get(
                CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS,
                [],
            )
        )

    async def _async_save_enabled_providers(self, enabled_providers: list[str]) -> None:
        """Persist enabled providers."""
        options = dict(self.entry.options)
        options[CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS] = [
            provider
            for provider in DEFAULT_REVERSE_LOOKUP_PROVIDERS
            if provider in enabled_providers
        ]
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self.async_write_ha_state()
