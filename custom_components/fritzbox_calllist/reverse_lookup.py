"""Reverse lookup support for FRITZ!Box Calllist."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from html import unescape
from urllib.parse import quote

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_REVERSE_LOOKUP_PROVIDERS

_LOGGER = logging.getLogger(__name__)

_UNKNOWN_NAMES = {"", "unbekannt", "unknown"}
_USER_AGENT = "Mozilla/5.0 HomeAssistant FRITZBoxCalllist/0"


@dataclass(frozen=True)
class LookupProvider:
    """Reverse lookup provider definition."""

    key: str
    url: str
    patterns: tuple[str, ...]
    skip_prefixes: tuple[str, ...] = ()


_COMMON_PATTERNS = (
    r'itemprop=["\']name["\'][^>]*>(?P<name>[^<]+)',
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](?P<name>[^"\']+)',
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](?P<name>[^"\']+)',
    r'class=["\'][^"\']*(?:hitlnk_name|namelink|name|entry-title|title)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
)

_PROVIDERS: dict[str, LookupProvider] = {
    "dasoertliche.de": LookupProvider(
        key="dasoertliche.de",
        url="https://www.dasoertliche.de/?form_name=search_inv&ph={number}",
        patterns=(
            r'itemprop=["\']name["\'][^>]*>(?P<name>[^<]+)',
            r'class=["\'][^"\']*(?:hitlnk_name|namelink|name)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            r'<a[^>]+href=["\'][^"\']*/Detail/[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            *_COMMON_PATTERNS,
        ),
    ),
    "11880.com": LookupProvider(
        key="11880.com",
        url="https://www.11880.com/rueckwaertssuche/{number}",
        patterns=(
            r'class=["\'][^"\']*(?:result-list-entry__name|result__name|name|headline)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            *_COMMON_PATTERNS,
        ),
    ),
    "search.ch": LookupProvider(
        key="search.ch",
        url="https://tel.search.ch/?was={number}",
        patterns=(
            r'class=["\'][^"\']*(?:tel-name|tel-result-title|name)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            *_COMMON_PATTERNS,
        ),
        skip_prefixes=("+49", "+43"),
    ),
    "dasschnelle.at": LookupProvider(
        key="dasschnelle.at",
        url="https://www.dasschnelle.at/ergebnisse?what={number}",
        patterns=(
            r'class=["\'][^"\']*(?:result-name|name|headline)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            *_COMMON_PATTERNS,
        ),
        skip_prefixes=("+49", "+41"),
    ),
    "herold.at": LookupProvider(
        key="herold.at",
        url="https://www.herold.at/telefonbuch/telefonnummer/{number}",
        patterns=(
            r'class=["\'][^"\']*(?:name|company-name|heading|headline)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            *_COMMON_PATTERNS,
        ),
        skip_prefixes=("+49", "+41"),
    ),
    "tellows.de": LookupProvider(
        key="tellows.de",
        url="https://www.tellows.de/num/{number}",
        patterns=(
            r'<h1[^>]*>(?P<name>[^<]+)</h1>',
            r'class=["\'][^"\']*(?:caller-name|name|headline)[^"\']*["\'][^>]*>(?P<name>[^<]+)',
            *_COMMON_PATTERNS,
        ),
    ),
}


async def async_reverse_lookup(
    hass: HomeAssistant,
    number: str,
    providers: list[str] | None = None,
) -> str | None:
    """Look up a number using the configured provider chain."""
    normalized = _normalize_number(number)
    if not normalized:
        return None

    provider_keys = normalize_provider_list(providers)
    session = async_get_clientsession(hass)

    for provider_key in provider_keys:
        provider = _PROVIDERS.get(provider_key)
        if provider is None:
            _LOGGER.debug("Skipping unknown reverse lookup provider %s", provider_key)
            continue
        if _should_skip_provider(provider, normalized):
            continue

        url = provider.url.format(number=quote(normalized))
        try:
            async with session.get(
                url,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
                },
                timeout=8,
            ) as response:
                response.raise_for_status()
                html = await response.text()
        except (ClientError, TimeoutError) as err:
            _LOGGER.debug(
                "Reverse lookup with %s failed for %s: %s",
                provider.key,
                _mask_number(normalized),
                err,
            )
            continue

        if name := _extract_name(html, provider.patterns):
            _LOGGER.debug(
                "Reverse lookup with %s found a name for %s",
                provider.key,
                _mask_number(normalized),
            )
            return name

    return None


def normalize_provider_list(providers: list[str] | str | None) -> list[str]:
    """Normalize configured provider order."""
    if providers is None:
        return list(DEFAULT_REVERSE_LOOKUP_PROVIDERS)

    if isinstance(providers, str):
        raw_providers = providers.split(",")
    else:
        raw_providers = providers

    normalized: list[str] = []
    for provider in raw_providers:
        key = str(provider).strip().casefold()
        if key and key in _PROVIDERS and key not in normalized:
            normalized.append(key)

    return normalized or list(DEFAULT_REVERSE_LOOKUP_PROVIDERS)


def supported_providers() -> list[str]:
    """Return supported reverse lookup provider keys."""
    return list(_PROVIDERS)


def is_unknown_name(name: str | None) -> bool:
    """Return true if the display name is unknown."""
    return name is None or name.strip().casefold() in _UNKNOWN_NAMES


def _extract_name(html: str, patterns: tuple[str, ...]) -> str | None:
    """Extract the first useful result name from provider HTML."""
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
    name = re.sub(r"<[^>]+>", " ", value)
    name = re.sub(r"\s+", " ", unescape(name)).strip(" -|\t\r\n")
    if not name:
        return None

    blocked_parts = (
        "Das Telefonbuch",
        "Das Örtliche",
        "Das Schnelle",
        "HEROLD",
        "tellows",
        "Rückwärtssuche",
        "Rueckwaertssuche",
        "Telefonnummer",
        "phone number",
        "Wer ruft an",
    )
    if any(part.casefold() in name.casefold() for part in blocked_parts):
        return None
    return name


def _normalize_number(number: str) -> str:
    """Normalize a phone number for lookup."""
    return re.sub(r"[^\d+]", "", number or "")


def _should_skip_provider(provider: LookupProvider, number: str) -> bool:
    """Return true if a country-specific provider should be skipped."""
    return any(number.startswith(prefix) for prefix in provider.skip_prefixes)


def _mask_number(number: str) -> str:
    """Mask a phone number for logs."""
    if len(number) <= 4:
        return "****"
    return f"{number[:3]}***{number[-2:]}"
