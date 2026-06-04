"""Sensor platform for FRITZ!Box Calllist."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store

from .const import (
    CALL_STATES,
    CONF_CALLMONITOR_ENTITY,
    CONF_MAX_ITEMS,
    CONF_REVERSE_LOOKUP,
    DEFAULT_MAX_ITEMS,
    DEFAULT_REVERSE_LOOKUP,
    DOMAIN,
    ENDED_STATE,
    REVERSE_LOOKUP_PROVIDER,
)
from .reverse_lookup import async_reverse_lookup, is_unknown_name


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
    _attr_should_poll = False

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
        self._lookup_cache: dict[str, str] = {}
        self._lookup_tasks: dict[str, asyncio.Task[str | None]] = {}
        self._active_call_state: State | None = None
        self._last_updated = datetime.now(timezone.utc)
        self._remove_listener = None
        self._startup_refresh_unsub: list[Callable[[], None]] = []
        self._store: Store[list[dict[str, Any]]] = Store(
            hass,
            1,
            f"{DOMAIN}_{entry.entry_id}_history",
        )
        self._lookup_store: Store[dict[str, str]] = Store(
            hass,
            1,
            f"{DOMAIN}_{entry.entry_id}_reverse_lookup_cache",
        )

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
    def native_value(self) -> str:
        """Return a readable call list state."""
        state = self.hass.states.get(self._callmonitor_entity)
        if state is not None and state.state in CALL_STATES:
            return state.state
        return ENDED_STATE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return feed attributes."""
        live = self._build_live_call()
        return {
            "callmonitor_entity": self._callmonitor_entity,
            "history": self._history,
            "live": live,
            "is_active": live is not None,
            "last_updated": self._last_updated.isoformat(),
            "reverse_lookup_enabled": self._is_reverse_lookup_enabled,
            "reverse_lookup_provider": REVERSE_LOOKUP_PROVIDER,
        }

    async def async_added_to_hass(self) -> None:
        """Restore and start listening."""
        if stored_history := await self._store.async_load():
            self._history = stored_history[: self._max_items]
        elif last_state := await self.async_get_last_state():
            restored_history = last_state.attributes.get("history")
            if isinstance(restored_history, list):
                self._history = restored_history[: self._max_items]

        if stored_lookup_cache := await self._lookup_store.async_load():
            self._lookup_cache = stored_lookup_cache

        self._remove_listener = async_track_state_change_event(
            self.hass,
            [self._callmonitor_entity],
            self._async_callmonitor_changed,
        )
        self._async_refresh_current_callmonitor()
        for delay in (5, 15):
            self._startup_refresh_unsub.append(
                async_call_later(
                    self.hass,
                    delay,
                    lambda _now: self._async_refresh_current_callmonitor(),
                )
            )
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listener."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        while self._startup_refresh_unsub:
            self._startup_refresh_unsub.pop()()

    @callback
    def _async_refresh_current_callmonitor(self) -> None:
        """Refresh from the current callmonitor state after startup."""
        state = self.hass.states.get(self._callmonitor_entity)
        if state is not None and state.state in CALL_STATES:
            self._active_call_state = state
            self._async_start_live_lookup(state)
        self._last_updated = datetime.now(timezone.utc)
        self.async_write_ha_state()

    @callback
    def _async_callmonitor_changed(self, event: Event) -> None:
        """Handle callmonitor state changes."""
        self.hass.async_create_task(self._async_handle_callmonitor_changed(event))

    async def _async_handle_callmonitor_changed(self, event: Event) -> None:
        """Handle callmonitor state changes."""
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        if new_state is None:
            return

        if new_state.state in CALL_STATES:
            self._active_call_state = new_state
            self._async_start_live_lookup(new_state)

        if new_state.state == ENDED_STATE:
            previous = (
                old_state
                if old_state is not None and old_state.state in CALL_STATES
                else self._active_call_state
            )
            self._active_call_state = None
            entry = await self._entry_from_finished_call(previous) if previous is not None else None
            if entry is not None:
                self._history = [entry.as_dict(), *self._history][: self._max_items]
                self.hass.async_create_task(self._store.async_save(self._history))

        self._last_updated = datetime.now(timezone.utc)
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
        if is_unknown_name(name):
            name = self._lookup_cache.get(number, name)
        started_at = state.last_changed.timestamp()

        return {
            "state": state.state,
            "type": call_type,
            "number": number,
            "name": name,
            "started_at": started_at,
            "duration": max(0, int(datetime.now(timezone.utc).timestamp() - started_at)),
        }

    async def _entry_from_finished_call(self, previous: State) -> CallEntry | None:
        """Create a feed entry from the state before idle."""
        call_type = _call_type_from_state(previous.state, previous.attributes)
        if call_type is None:
            return None

        number = _number_from_attrs(previous.attributes, call_type)
        name = _name_from_attrs(previous.attributes, call_type, number)
        name = await self._async_resolve_name(name, number)
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

    async def _async_resolve_name(self, name: str, number: str) -> str:
        """Resolve a display name using cache and optional reverse lookup."""
        if not is_unknown_name(name):
            return name

        if cached_name := self._lookup_cache.get(number):
            return cached_name

        if not self._is_reverse_lookup_enabled:
            return name

        if lookup_name := await self._async_lookup_number(number):
            return lookup_name

        return name

    def _async_start_live_lookup(self, state: State) -> None:
        """Start live reverse lookup if needed."""
        call_type = _call_type_from_state(state.state, state.attributes)
        number = _number_from_attrs(state.attributes, call_type)
        name = _name_from_attrs(state.attributes, call_type, number)

        if not is_unknown_name(name) or self._lookup_cache.get(number):
            return

        if not self._is_reverse_lookup_enabled:
            return

        task = self._lookup_tasks.get(number)
        if task is None or task.done():
            task = self.hass.async_create_task(self._async_lookup_number(number))
            self._lookup_tasks[number] = task

        task.add_done_callback(lambda _: self.hass.loop.call_soon_threadsafe(self.async_write_ha_state))

    async def _async_lookup_number(self, number: str) -> str | None:
        """Look up and cache a phone number."""
        if cached_name := self._lookup_cache.get(number):
            return cached_name

        if task := self._lookup_tasks.get(number):
            if not task.done() and task is not asyncio.current_task():
                return await task

        self._lookup_tasks[number] = asyncio.current_task()
        try:
            lookup_name = await async_reverse_lookup(self.hass, number)
        finally:
            self._lookup_tasks.pop(number, None)

        if lookup_name:
            self._lookup_cache[number] = lookup_name
            await self._lookup_store.async_save(self._lookup_cache)
            return lookup_name
        return None

    @property
    def _is_reverse_lookup_enabled(self) -> bool:
        """Return true if reverse lookup is enabled."""
        return bool(self.entry.options.get(CONF_REVERSE_LOOKUP, DEFAULT_REVERSE_LOOKUP))


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
        if candidate and not is_unknown_name(str(candidate)) and candidate != number:
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
    return f"Nicht erreicht: {name} ({number})"


def _format_duration(seconds: int) -> str:
    """Format call duration."""
    minutes, rest = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:d}:{rest:02d}"
