"""Reverse lookup support for FRITZ!Box Calllist."""

from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import quote

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_LOOKUP_URL = "https://www.dasoertliche.de/?form_name=search_inv&ph={number}"
_UNKNOWN_NAMES = {"", "unbekannt", "unknown"}


async def async_reverse_lookup(hass: HomeAssistant, number: str) -> str | None:
    """Look up a number using Das Oertliche."""
    normalized = _normalize_number(number)
    if not normalized:
        return None

    session = async_get_clientsession(hass)
    url = _LOOKUP_URL.format(number=quote(normalized))

    try:
        async with session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 HomeAssistant FRITZBoxCalllist/0",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
            },
            timeout=8,
        ) as response:
            response.raise_for_status()
            html = await response.text()
    except (ClientError, TimeoutError) as err:
        _LOGGER.debug("Reverse lookup failed for %s: %s", _mask_number(normalized), err)
        return None

    return _extract_name(html)


def is_unknown_name(name: str | None) -> bool:
    """Return true if the display name is unknown."""
    return name is None or name.strip().casefold() in _UNKNOWN_NAMES


def _extract_name(html: str) -> str | None:
    """Extract the first useful result name from Das Oertliche HTML."""
    patterns = [
        r'itemprop=["\']name["\'][^>]*>(?P<name>[^<]+)',
        r'class=["\'][^"\']*(?:hitlnk_name|namelink|name)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
        r'<a[^>]+href=["\'][^"\']*/Detail/[^"\']*["\'][^>]*>(?P<name>[^<]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if not match:
            continue
        name = _clean_name(match.group("name"))
        if name:
            return name
    return None


def _clean_name(value: str) -> str | None:
    """Clean a result name."""
    name = re.sub(r"\s+", " ", unescape(value)).strip()
    if not name or "Das Telefonbuch" in name or "Das Örtliche" in name:
        return None
    return name


def _normalize_number(number: str) -> str:
    """Normalize a phone number for lookup."""
    return re.sub(r"[^\d+]", "", number or "")


def _mask_number(number: str) -> str:
    """Mask a phone number for logs."""
    if len(number) <= 4:
        return "****"
    return f"{number[:3]}***{number[-2:]}"
