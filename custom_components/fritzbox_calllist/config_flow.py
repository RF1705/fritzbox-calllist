"""Config flow for FRITZ!Box Calllist."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from .sensor import FritzboxCalllistSensor

CONF_CACHE_ACTION = "cache_action"
ACTION_NO_CHANGE = "__no_change__"
ACTION_CLEAR_ALL = "__clear_all__"
ACTION_DELETE_PREFIX = "delete:"
CACHE_LABELS = {
    "de": {
        "no_change": "Keine Cache-Änderung",
        "clear_all": "Alle gecachten Namen löschen",
        "delete": "{name} ({number}) löschen",
    },
    "en": {
        "no_change": "No cache change",
        "clear_all": "Delete all cached names",
        "delete": "Delete {name} ({number})",
    },
    "fr": {
        "no_change": "Aucune modification du cache",
        "clear_all": "Supprimer tous les noms en cache",
        "delete": "Supprimer {name} ({number})",
    },
    "es": {
        "no_change": "Sin cambios en la caché",
        "clear_all": "Eliminar todos los nombres en caché",
        "delete": "Eliminar {name} ({number})",
    },
    "it": {
        "no_change": "Nessuna modifica della cache",
        "clear_all": "Elimina tutti i nomi nella cache",
        "delete": "Elimina {name} ({number})",
    },
    "nl": {
        "no_change": "Geen cachewijziging",
        "clear_all": "Alle namen in de cache verwijderen",
        "delete": "{name} ({number}) verwijderen",
    },
    "pl": {
        "no_change": "Bez zmian w pamięci podręcznej",
        "clear_all": "Usuń wszystkie nazwy z pamięci podręcznej",
        "delete": "Usuń {name} ({number})",
    },
    "cs": {
        "no_change": "Bez změny mezipaměti",
        "clear_all": "Smazat všechna jména v mezipaměti",
        "delete": "Smazat {name} ({number})",
    },
}


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
        """Manage the call monitor entity and reverse lookup cache."""
        cache_store = Store(
            self.hass,
            LOOKUP_CACHE_VERSION,
            f"{DOMAIN}_{self._config_entry.entry_id}_reverse_lookup_cache",
        )
        cache = await cache_store.async_load() or {}
        errors: dict[str, str] = {}

        if user_input is not None:
            callmonitor_entity = user_input[CONF_CALLMONITOR_ENTITY]
            callmonitor_changed = (
                callmonitor_entity
                != self._config_entry.data[CONF_CALLMONITOR_ENTITY]
            )
            if self._callmonitor_is_configured(callmonitor_entity):
                errors["base"] = "callmonitor_already_configured"
            else:
                data = dict(self._config_entry.data)
                data[CONF_CALLMONITOR_ENTITY] = callmonitor_entity
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=data,
                    unique_id=callmonitor_entity,
                )
                if callmonitor_changed:
                    sensor = self._sensor
                    if sensor is not None:
                        sensor.async_set_callmonitor_entity(callmonitor_entity)

            action = user_input.get(CONF_CACHE_ACTION, ACTION_NO_CHANGE)
            cache_changed = False
            if not errors and action == ACTION_CLEAR_ALL:
                cache = {}
                await cache_store.async_save(cache)
                cache_changed = True
            elif (
                not errors
                and isinstance(action, str)
                and action.startswith(ACTION_DELETE_PREFIX)
            ):
                number = action.removeprefix(ACTION_DELETE_PREFIX)
                if number in cache:
                    cache.pop(number)
                    await cache_store.async_save(cache)
                    cache_changed = True

            if cache_changed:
                sensor = self._sensor
                if sensor is not None:
                    sensor.async_replace_lookup_cache(cache)

            if not errors:
                return self.async_create_entry(
                    title="",
                    data=dict(self._config_entry.options),
                )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CALLMONITOR_ENTITY,
                    default=self._config_entry.data[CONF_CALLMONITOR_ENTITY],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
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
            errors=errors,
        )

    def _callmonitor_is_configured(self, entity_id: str) -> bool:
        """Return whether another entry already uses the call monitor."""
        return any(
            entry.entry_id != self._config_entry.entry_id
            and entry.data.get(CONF_CALLMONITOR_ENTITY) == entity_id
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        )

    @property
    def _sensor(self) -> FritzboxCalllistSensor | None:
        """Return the loaded call list sensor."""
        return (
            self.hass.data.get(DOMAIN, {})
            .get(self._config_entry.entry_id, {})
            .get("sensor")
        )

    def _cache_action_options(self, cache: dict[str, str]) -> list[selector.SelectOptionDict]:
        """Return cache action options."""
        labels = self._cache_labels()
        options: list[selector.SelectOptionDict] = [
            {
                "value": ACTION_NO_CHANGE,
                "label": labels["no_change"],
            },
        ]
        if not cache:
            return options

        options.append(
            {
                "value": ACTION_CLEAR_ALL,
                "label": labels["clear_all"],
            }
        )
        for number, name in sorted(cache.items(), key=lambda item: item[1].casefold()):
            options.append(
                {
                    "value": f"{ACTION_DELETE_PREFIX}{number}",
                    "label": labels["delete"].format(name=name, number=number),
                }
            )
        return options

    def _cache_labels(self) -> dict[str, str]:
        """Return localized cache action labels."""
        language = str(self.hass.config.language).lower().split("-")[0]
        return CACHE_LABELS.get(language, CACHE_LABELS["en"])
