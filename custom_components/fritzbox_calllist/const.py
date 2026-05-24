"""Constants for the FRITZ!Box Calllist integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "fritzbox_calllist"

CONF_CALLMONITOR_ENTITY = "callmonitor_entity"
CONF_MAX_ITEMS = "max_items"

DEFAULT_MAX_ITEMS = 10

CALL_STATES = {"ringing", "dialing", "talking"}
ENDED_STATE = "idle"
