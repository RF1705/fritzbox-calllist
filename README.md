# FRITZ!Box Calllist

A HACS-compatible Home Assistant custom integration for FRITZ!Box call monitor sensors.

FRITZ!Box Calllist turns an existing call monitor sensor into a small phone dashboard:

- live call state for ringing, dialing and active calls
- persistent call history
- call duration for live and completed calls
- a native Lovelace card, without Markdown templates

## Installation

1. Add this repository to HACS as a custom repository.
2. Select the `Integration` category.
3. Install `FRITZ!Box Calllist`.
4. Restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration**.
6. Search for `FRITZ!Box Calllist`.
7. Select your FRITZ!Box call monitor sensor.

FRITZ!Box Calllist is a regular Home Assistant integration. It is not registered as a helper.

## Migration From Telefon Feed

The integration domain was renamed from `telefon_feed` to `fritzbox_calllist`.

If you installed an older development version, remove the old `Telefon Feed` integration first, restart Home Assistant, then install and set up `FRITZ!Box Calllist`.

## Lovelace Card

The card module is registered by the integration. After setup, reload Home Assistant in your browser.

If the card does not appear, add this JavaScript module resource manually under **Settings > Dashboards > Resources**:

```text
/fritzbox_calllist/fritzbox-calllist-card.js
```

Then add the card to your dashboard:

```yaml
type: custom:fritzbox-calllist-card
entity: sensor.fritzbox_calllist
title: Phone
max_items: 4
```

When a live call is active, the card automatically shows one fewer history item.

## Configuration

The setup dialog asks for:

- the call monitor sensor entity
- the number of stored call entries

The integration creates a FRITZ!Box Calllist device and one feed sensor entity.

## Sensor Attributes

The feed sensor exposes these attributes:

- `history`: stored call entries
- `live`: current live call information
- `is_active`: whether a call is currently ringing, dialing or active
- `callmonitor_entity`: the configured source sensor

## Supported Call States

FRITZ!Box Calllist expects a call monitor sensor using these states:

- `ringing`
- `dialing`
- `talking`
- `idle`
