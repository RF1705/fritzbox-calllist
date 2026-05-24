"""Config flow for FRITZ!Box Calllist."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import CONF_CALLMONITOR_ENTITY, CONF_MAX_ITEMS, DEFAULT_MAX_ITEMS, DOMAIN


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
