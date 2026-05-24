# Telefon Feed

A HACS-compatible Home Assistant custom integration for FRITZ!Box call monitor sensors.

Telefon Feed turns an existing call monitor sensor into a small phone dashboard:

- live call state for ringing, dialing and active calls
- persistent call history
- call duration for live and completed calls
- a native Lovelace card, without Markdown templates

## Installation

1. Add this repository to HACS as a custom repository.
2. Select the `Integration` category.
3. Install `Telefon Feed`.
4. Restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration**.
6. Search for `Telefon Feed`.
7. Select your FRITZ!Box call monitor sensor.

Telefon Feed is a regular Home Assistant integration. It is not registered as a helper.

## Lovelace Card

The card module is registered by the integration. After setup, reload Home Assistant in your browser.

If the card does not appear, add this JavaScript module resource manually under **Settings > Dashboards > Resources**:

```text
/telefon_feed/telefon-feed-card.js
```

Then add the card to your dashboard:

```yaml
type: custom:telefon-feed-card
entity: sensor.telefon_feed
title: Phone
max_items: 4
```

When a live call is active, the card automatically shows one fewer history item.

## Configuration

The setup dialog asks for:

- the call monitor sensor entity
- the number of stored call entries

The integration creates a Telefon Feed device and one feed sensor entity.

## Sensor Attributes

The feed sensor exposes these attributes:

- `history`: stored call entries
- `live`: current live call information
- `is_active`: whether a call is currently ringing, dialing or active
- `callmonitor_entity`: the configured source sensor

## Supported Call States

Telefon Feed expects a call monitor sensor using these states:

- `ringing`
- `dialing`
- `talking`
- `idle`
