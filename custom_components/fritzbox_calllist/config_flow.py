"""Config flow for FRITZ!Box Calllist."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.storage import Store

from .const import (
    CONF_CALLMONITOR_ENTITY,
    CONF_MAX_ITEMS,
    DEFAULT_MAX_ITEMS,
    DOMAIN,
    LOOKUP_CACHE_VERSION,
)

CONF_CACHE_ACTION = "cache_action"
ACTION_NO_CHANGE = "__no_change__"
ACTION_CLEAR_ALL = "__clear_all__"
ACTION_DELETE_PREFIX = "delete:"


class FritzboxCalllistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FRITZ!Box Calllist."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CALLMONITOR_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or "FRITZ!Box Calllist",
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="FRITZ!Box Calllist"): str,
                vol.Required(CONF_CALLMONITOR_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=50,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Create the options flow."""
        return FritzboxCalllistOptionsFlow(config_entry)


class FritzboxCalllistOptionsFlow(config_entries.OptionsFlow):
    """Handle options for FRITZ!Box Calllist."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        """Manage reverse lookup cache."""
        cache_store = Store(
            self.hass,
            LOOKUP_CACHE_VERSION,
            f"{DOMAIN}_{self._config_entry.entry_id}_reverse_lookup_cache",
        )
        cache = await cache_store.async_load() or {}

        if user_input is not None:
            action = user_input.get(CONF_CACHE_ACTION, ACTION_NO_CHANGE)
            cache_changed = False
            if action == ACTION_CLEAR_ALL:
                cache = {}
                await cache_store.async_save(cache)
                cache_changed = True
            elif isinstance(action, str) and action.startswith(ACTION_DELETE_PREFIX):
                number = action.removeprefix(ACTION_DELETE_PREFIX)
                if number in cache:
                    cache.pop(number)
                    await cache_store.async_save(cache)
                    cache_changed = True

            if cache_changed:
                sensor = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {}).get("sensor")
                if sensor is not None:
                    sensor.async_replace_lookup_cache(cache)

            return self.async_create_entry(title="", data=dict(self._config_entry.options))

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CACHE_ACTION, default=ACTION_NO_CHANGE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._cache_action_options(cache),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )

    def _cache_action_options(self, cache: dict[str, str]) -> list[selector.SelectOptionDict]:
        """Return cache action options."""
        german = str(self.hass.config.language).lower().startswith("de")
        options: list[selector.SelectOptionDict] = [
            {
                "value": ACTION_NO_CHANGE,
                "label": "Keine Cache-Änderung" if german else "No cache change",
            },
        ]
        if not cache:
            return options

        options.append(
            {
                "value": ACTION_CLEAR_ALL,
                "label": "Alle gecachten Namen löschen" if german else "Delete all cached names",
            }
        )
        for number, name in sorted(cache.items(), key=lambda item: item[1].casefold()):
            options.append(
                {
                    "value": f"{ACTION_DELETE_PREFIX}{number}",
                    "label": (
                        f"{name} ({number}) löschen"
                        if german
                        else f"Delete {name} ({number})"
                    ),
                }
            )
        return options
