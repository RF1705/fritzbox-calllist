"""Constants for the FRITZ!Box Calllist integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

DOMAIN: Final = "fritzbox_calllist"

MANIFEST_PATH = Path(__file__).parent / "manifest.json"
with open(MANIFEST_PATH, encoding="utf-8") as manifest_file:
    INTEGRATION_VERSION: Final = json.load(manifest_file).get("version", "0.0.0")

FRONTEND_URL_BASE: Final = "/fritzbox_calllist"
FRONTEND_MODULES: Final = [
    {
        "name": "FRITZ!Box Calllist Card",
        "filename": "fritzbox-calllist-card.js",
        "version": INTEGRATION_VERSION,
    }
]

CONF_CALLMONITOR_ENTITY = "callmonitor_entity"
CONF_MAX_ITEMS = "max_items"

DEFAULT_MAX_ITEMS = 10

CALL_STATES = {"ringing", "dialing", "talking"}
ENDED_STATE = "idle"
