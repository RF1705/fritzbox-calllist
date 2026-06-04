"""Constants for the FRITZ!Box Calllist integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "fritzbox_calllist"

CONF_CALLMONITOR_ENTITY = "callmonitor_entity"
CONF_MAX_ITEMS = "max_items"
CONF_REVERSE_LOOKUP_ENABLED_PROVIDERS = "reverse_lookup_enabled_providers"

DEFAULT_MAX_ITEMS = 10
DEFAULT_REVERSE_LOOKUP_PROVIDERS = [
    "dasoertliche.de",
    "11880.com",
    "dasschnelle.at",
    "herold.at",
    "search.ch",
    "tellows.de",
]

CALL_STATES = {"ringing", "dialing", "talking"}
ENDED_STATE = "idle"
