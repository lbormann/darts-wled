# WLED Data JSON Structure

This document describes the current structure of `wled_data.json`.

## Purpose

`wled_data.json` stores cached WLED metadata for all configured endpoints from `-WEPS`.
Each endpoint is stored separately so effect lists, presets, palettes, info and state can be tracked per controller.

## Schema Overview

The current schema version is `2`.

```json
{
  "schema_version": 2,
  "primary_endpoint": "192.168.1.144",
  "configured_endpoints": [
    "192.168.1.144",
    "192.168.1.20"
  ],
  "endpoints": {
    "192.168.1.144": {
      "endpoint": "192.168.1.144",
      "effects": {
        "names": ["solid", "blink"],
        "ids": [0, 1]
      },
      "presets": {
        "1": {
          "n": "Game Won"
        }
      },
      "palettes": {
        "names": ["Default", "Random Cycle"],
        "ids": [0, 1]
      },
      "info": {
        "ver": "0.15.0",
        "leds": {
          "count": 270
        }
      },
      "state": {
        "on": true,
        "seg": []
      },
      "segments": [],
      "data_hash": "...",
      "last_updated": "2026-04-09T20:15:00.000000"
    },
    "192.168.1.20": {
      "endpoint": "192.168.1.20",
      "effects": {
        "names": ["solid", "dynamic"],
        "ids": [0, 1]
      },
      "presets": {},
      "palettes": {
        "names": ["Default"],
        "ids": [0]
      },
      "info": {},
      "state": {},
      "segments": [],
      "data_hash": "...",
      "last_updated": "2026-04-09T20:15:01.000000"
    }
  },
  "last_updated": "2026-04-09T20:15:01.000000"
}
```

## Top-Level Fields

- `schema_version`: Version of the JSON layout.
- `primary_endpoint`: The master endpoint. This is usually the first configured `-WEPS` entry.
- `configured_endpoints`: Normalized list of all configured WLED endpoints.
- `endpoints`: Object containing one cache entry per endpoint.
- `last_updated`: Timestamp of the last overall sync attempt.

## Endpoint Entry Fields

Each item inside `endpoints` contains:

- `endpoint`: Endpoint identifier / host.
- `effects.names`: All available effect names from `/json/eff`.
- `effects.ids`: Generated numeric IDs matching the effect order.
- `presets`: Raw preset data from `/presets.json`.
- `palettes.names`: Palette names from `/json/pal`.
- `palettes.ids`: Generated numeric IDs matching the palette order.
- `info`: Raw controller info from `/json/info`.
- `state`: Raw controller state from `/json/state`.
- `segments`: Extracted segment list from `state.seg`.
- `data_hash`: Hash used to detect changes for this endpoint.
- `last_updated`: Timestamp of the last successful refresh for this endpoint.

## Behavior Notes

- The file stores data for every configured endpoint separately.
- The manager still treats the first configured endpoint as the primary source for default effect lookups.
- If one endpoint is temporarily unreachable, previously cached data for that endpoint is kept instead of being discarded.
- Older single-endpoint `wled_data.json` files are migrated automatically into the new schema.

## Migration From Old Format

Older files used a flat structure like this:

```json
{
  "endpoint": "192.168.1.144",
  "effects": { "names": [], "ids": [] },
  "presets": {},
  "palettes": { "names": [], "ids": [] },
  "info": {},
  "state": {},
  "segments": [],
  "data_hash": "",
  "last_updated": ""
}
```

This old format is automatically wrapped into the new `endpoints` object on load.