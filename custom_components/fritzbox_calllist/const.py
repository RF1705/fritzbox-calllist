"""Constants for the FRITZ!Box Calllist integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "fritzbox_calllist"

CONF_CALLMONITOR_ENTITY = "callmonitor_entity"
CONF_MAX_ITEMS = "max_items"
CONF_REVERSE_LOOKUP = "reverse_lookup"

DEFAULT_MAX_ITEMS = 10
DEFAULT_REVERSE_LOOKUP = False
REVERSE_LOOKUP_PROVIDER = "Das Oertliche"

CALL_STATES = {"ringing", "dialing", "talking"}
ENDED_STATE = "idle"
