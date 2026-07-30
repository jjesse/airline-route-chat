"""Airport coordinates and names for geographic route maps.

Looks up latitude/longitude and official names from ICAO (preferred) or
IATA codes using the offline `airportsdata` database.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional, Tuple

# Optional local overrides (always win). Keys may be ICAO or IATA.
LOCAL_OVERRIDES: Dict[str, Tuple[float, float]] = {}

# Minimal fallback for sample network (ICAO + IATA).
_FALLBACK: Dict[str, Tuple[float, float]] = {
    "KDTW": (42.2124, -83.3534), "DTW": (42.2124, -83.3534),
    "KORD": (41.9742, -87.9073), "ORD": (41.9742, -87.9073),
    "KDEN": (39.8561, -104.6737), "DEN": (39.8561, -104.6737),
    "KLAX": (33.9425, -118.4081), "LAX": (33.9425, -118.4081),
    "KATL": (33.6407, -84.4277), "ATL": (33.6407, -84.4277),
    "KMIA": (25.7959, -80.2870), "MIA": (25.7959, -80.2870),
    "KSEA": (47.4502, -122.3088), "SEA": (47.4502, -122.3088),
    "KSFO": (37.6213, -122.3790), "SFO": (37.6213, -122.3790),
    "KMSP": (44.8848, -93.2223), "MSP": (44.8848, -93.2223),
}

_FALLBACK_NAMES: Dict[str, str] = {
    "KDTW": "Detroit Metropolitan Wayne County Airport",
    "DTW": "Detroit Metropolitan Wayne County Airport",
    "KORD": "Chicago O'Hare International Airport",
    "ORD": "Chicago O'Hare International Airport",
    "KDEN": "Denver International Airport",
    "DEN": "Denver International Airport",
    "KLAX": "Los Angeles International Airport",
    "LAX": "Los Angeles International Airport",
    "KATL": "Hartsfield-Jackson Atlanta International Airport",
    "ATL": "Hartsfield-Jackson Atlanta International Airport",
    "KMIA": "Miami International Airport",
    "MIA": "Miami International Airport",
    "KSEA": "Seattle-Tacoma International Airport",
    "SEA": "Seattle-Tacoma International Airport",
    "KSFO": "San Francisco International Airport",
    "SFO": "San Francisco International Airport",
    "KMSP": "Minneapolis-Saint Paul International Airport",
    "MSP": "Minneapolis-Saint Paul International Airport",
    "SCEL": "Arturo Merino Benítez International Airport",
}


@lru_cache(maxsize=1)
def _icao_db() -> Dict[str, dict]:
    try:
        import airportsdata

        return airportsdata.load("ICAO")
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _iata_db() -> Dict[str, dict]:
    try:
        import airportsdata

        return airportsdata.load("IATA")
    except Exception:
        return {}


def _lookup_entry(code: str) -> Optional[dict]:
    """Return airportsdata entry for ICAO or IATA code."""
    key = str(code).upper().strip()
    if not key:
        return None
    entry = _icao_db().get(key)
    if entry:
        return entry
    entry = _iata_db().get(key)
    if entry:
        return entry
    if len(key) == 3:
        return _icao_db().get("K" + key)
    return None


def get_airport_coords(code: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for an ICAO or IATA code, or None if unknown."""
    if not code or not isinstance(code, str):
        return None

    key = code.upper().strip()
    if not (3 <= len(key) <= 4) or not key.isalnum():
        return None

    if key in LOCAL_OVERRIDES:
        return LOCAL_OVERRIDES[key]

    entry = _lookup_entry(key)
    if entry:
        try:
            return (float(entry["lat"]), float(entry["lon"]))
        except (KeyError, TypeError, ValueError):
            pass

    return _FALLBACK.get(key)


def airport_name(code: str) -> Optional[str]:
    """Official airport name from the offline database."""
    if not code:
        return None
    key = str(code).upper().strip()
    entry = _lookup_entry(key)
    if entry:
        name = entry.get("name") or entry.get("city")
        if name:
            return str(name)
    return _FALLBACK_NAMES.get(key)


def airport_city(code: str) -> Optional[str]:
    """City name for an airport code, if available."""
    if not code:
        return None
    key = str(code).upper().strip()
    entry = _lookup_entry(key)
    if entry and entry.get("city"):
        return str(entry["city"])
    return None


def format_airport_label(code: str) -> str:
    """Human-readable label: 'SCEL — Arturo Merino Benítez International Airport'."""
    if not code:
        return ""
    key = str(code).upper().strip()
    name = airport_name(key)
    if name:
        return f"{key} — {name}"
    return key


def iata_to_icao(iata: str) -> Optional[str]:
    """Best-effort IATA → ICAO using airportsdata."""
    if not iata:
        return None
    key = str(iata).upper().strip()
    if len(key) != 3:
        return None
    entry = _iata_db().get(key)
    if entry and entry.get("icao"):
        return str(entry["icao"]).upper()
    return "K" + key
