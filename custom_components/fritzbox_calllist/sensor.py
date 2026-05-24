"""Sensor platform for FRITZ!Box Calllist."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CALL_STATES,
    CONF_CALLMONITOR_ENTITY,
    CONF_MAX_ITEMS,
    DEFAULT_MAX_ITEMS,
    DOMAIN,
    ENDED_STATE,
)


@dataclass
class CallEntry:
    """A stored call entry."""

    time: float
    text: str
    call_type: str
    number: str
    name: str
    duration: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant attribute friendly dict."""
        data: dict[str, Any] = {
            "time": self.time,
            "text": self.text,
            "type": self.call_type,
            "number": self.number,
            "name": self.name,
        }
        if self.duration is not None:
            data["duration"] = self.duration
        return data


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FRITZ!Box Calllist sensor."""
    async_add_entities([FritzboxCalllistSensor(hass, entry)], True)


class FritzboxCalllistSensor(SensorEntity, RestoreEntity):
    """FRITZ!Box Calllist sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:phone-log"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self._attr_name = None
        self._attr_suggested_object_id = "fritzbox_calllist"
        self._attr_unique_id = f"{entry.entry_id}_fritzbox_calllist"
        self._callmonitor_entity = entry.data[CONF_CALLMONITOR_ENTITY]
        self._max_items = int(entry.data.get(CONF_MAX_ITEMS, DEFAULT_MAX_ITEMS))
        self._history: list[dict[str, Any]] = []
        self._state = datetime.now(timezone.utc).timestamp()
        self._remove_listener = None

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
    def native_value(self) -> float:
        """Return the current timestamp as sensor state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return feed attributes."""
        live = self._build_live_call()
        return {
            "callmonitor_entity": self._callmonitor_entity,
            "history": self._history,
            "live": live,
            "is_active": live is not None,
        }

    async def async_added_to_hass(self) -> None:
        """Restore and start listening."""
        if last_state := await self.async_get_last_state():
            restored_history = last_state.attributes.get("history")
            if isinstance(restored_history, list):
                self._history = restored_history[: self._max_items]

        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self._callmonitor_entity],
            self._async_callmonitor_changed,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listener."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _async_callmonitor_changed(self, event: Event) -> None:
        """Handle callmonitor state changes."""
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        if new_state is None:
            return

        if new_state.state == ENDED_STATE and old_state is not None:
            entry = self._entry_from_finished_call(old_state)
            if entry is not None:
                self._history = [entry.as_dict(), *self._history][: self._max_items]

        self._state = datetime.now(timezone.utc).timestamp()
        self.async_write_ha_state()

    def _build_live_call(self) -> dict[str, Any] | None:
        """Build live call data from the current callmonitor state."""
        state = self.hass.states.get(self._callmonitor_entity)
        if state is None or state.state not in CALL_STATES:
            return None

        attrs = state.attributes
        call_type = _call_type_from_state(state.state, attrs)
        number = _number_from_attrs(attrs, call_type)
        name = _name_from_attrs(attrs, call_type, number)
        started_at = state.last_changed.timestamp()

        return {
            "state": state.state,
            "type": call_type,
            "number": number,
            "name": name,
            "started_at": started_at,
            "duration": max(0, int(datetime.now(timezone.utc).timestamp() - started_at)),
        }

    def _entry_from_finished_call(self, previous: State) -> CallEntry | None:
        """Create a feed entry from the state before idle."""
        call_type = _call_type_from_state(previous.state, previous.attributes)
        if call_type is None:
            return None

        number = _number_from_attrs(previous.attributes, call_type)
        name = _name_from_attrs(previous.attributes, call_type, number)
        duration = None

        if previous.state == "talking":
            duration = max(
                0,
                int(datetime.now(timezone.utc).timestamp() - previous.last_changed.timestamp()),
            )

        return CallEntry(
            time=datetime.now(timezone.utc).timestamp(),
            text=_text_for_call(call_type, name, number, duration),
            call_type=call_type,
            number=number,
            name=name,
            duration=duration,
        )


def _call_type_from_state(state: str, attrs: dict[str, Any]) -> str | None:
    """Resolve feed call type from FRITZ!Box callmonitor state."""
    if state == "talking":
        if attrs.get("from") == attrs.get("local_number"):
            return "outgoing"
        return "incoming"
    if state == "ringing":
        return "missed"
    if state == "dialing":
        return "not_answered"
    return None


def _number_from_attrs(attrs: dict[str, Any], call_type: str | None) -> str:
    """Pick the relevant phone number."""
    if call_type == "missed":
        return attrs.get("from") or attrs.get("with") or attrs.get("to") or "Unbekannt"
    if call_type == "not_answered":
        return attrs.get("to") or attrs.get("with") or attrs.get("from") or "Unbekannt"
    return attrs.get("with") or attrs.get("from") or attrs.get("to") or "Unbekannt"


def _name_from_attrs(attrs: dict[str, Any], call_type: str | None, number: str) -> str:
    """Pick the best available display name."""
    candidates: list[Any]
    if call_type == "missed":
        candidates = [attrs.get("from_name"), attrs.get("with_name"), attrs.get("to_name")]
    elif call_type == "not_answered":
        candidates = [attrs.get("to_name"), attrs.get("with_name"), attrs.get("from_name")]
    else:
        candidates = [attrs.get("with_name"), attrs.get("from_name"), attrs.get("to_name")]

    for candidate in candidates:
        if candidate and candidate not in {"Unbekannt", number}:
            return str(candidate)
    return "Unbekannt"


def _text_for_call(call_type: str, name: str, number: str, duration: int | None) -> str:
    """Return a readable call text."""
    duration_text = f" ({_format_duration(duration)})" if duration is not None else ""
    if call_type == "outgoing":
        return f"Gespräch mit {name} ({number}){duration_text}"
    if call_type == "incoming":
        return f"Anruf von {name} ({number}){duration_text}"
    if call_type == "missed":
        return f"Verpasster Anruf von {name} ({number})"
    return f"Nicht angenommen an {name} ({number})"


def _format_duration(seconds: int) -> str:
    """Format call duration."""
    minutes, rest = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:d}:{rest:02d}"
