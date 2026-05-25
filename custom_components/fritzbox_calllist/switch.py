"""Switch platform for FRITZ!Box Calllist."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_REVERSE_LOOKUP, DEFAULT_REVERSE_LOOKUP, DOMAIN, REVERSE_LOOKUP_PROVIDER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FRITZ!Box Calllist switches."""
    async_add_entities([FritzboxCalllistReverseLookupSwitch(hass, entry)])


class FritzboxCalllistReverseLookupSwitch(SwitchEntity):
    """Switch for optional reverse lookup of unknown phone numbers."""

    _attr_has_entity_name = True
    _attr_name = "Das Oertliche reverse lookup"
    _attr_icon = "mdi:account-search"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reverse_lookup"

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
        """Return true if reverse lookup is enabled."""
        return bool(self.entry.options.get(CONF_REVERSE_LOOKUP, DEFAULT_REVERSE_LOOKUP))

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return switch attributes."""
        return {"provider": REVERSE_LOOKUP_PROVIDER}

    async def async_turn_on(self, **kwargs) -> None:
        """Enable reverse lookup."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable reverse lookup."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Persist reverse lookup setting."""
        options = dict(self.entry.options)
        options[CONF_REVERSE_LOOKUP] = enabled
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self.async_write_ha_state()
