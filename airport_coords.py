"""Airport coordinates for geographic route maps (lat, lon).

Looks up latitude/longitude from the IATA code using the offline
`airportsdata` database (thousands of airports worldwide).

A small local override table is kept for deliberate overrides or when
the package is not installed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional, Tuple

# Optional local overrides (always win over the package database).
# Values are (lat, lon) with West longitudes negative — e.g. DTW is
# 42.2124 N, 83.3534 W → (42.2124, -83.3534).
LOCAL_OVERRIDES: Dict[str, Tuple[float, float]] = {
    # Intentionally empty by default; add entries only if you need to
    # force a specific point (e.g. a preferred terminal / ARP).
}

# Minimal fallback if airportsdata is not installed (sample CSV airports).
_FALLBACK: Dict[str, Tuple[float, float]] = {
    "DTW": (42.2124, -83.3534),
    "ORD": (41.9742, -87.9073),
    "DEN": (39.8561, -104.6737),
    "LAX": (33.9425, -118.4081),
    "ATL": (33.6407, -84.4277),
    "MIA": (25.7959, -80.2870),
    "SEA": (47.4502, -122.3088),
    "SFO": (37.6213, -122.3790),
    "MSP": (44.8848, -93.2223),
}


@lru_cache(maxsize=1)
def _iata_db() -> Dict[str, dict]:
    """Load the IATA-keyed airport database once."""
    try:
        import airportsdata

        return airportsdata.load("IATA")
    except Exception:
        return {}


def get_airport_coords(code: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for an IATA code, or None if unknown.

    Lookup order:
      1. LOCAL_OVERRIDES
      2. airportsdata offline database (by IATA)
      3. Built-in sample fallback
    """
    if not code or not isinstance(code, str):
        return None

    key = code.upper().strip()
    if len(key) != 3 or not key.isalnum():
        return None

    if key in LOCAL_OVERRIDES:
        return LOCAL_OVERRIDES[key]

    db = _iata_db()
    if key in db:
        entry = db[key]
        try:
            lat = float(entry["lat"])
            lon = float(entry["lon"])
            return (lat, lon)
        except (KeyError, TypeError, ValueError):
            pass

    return _FALLBACK.get(key)


def airport_name(code: str) -> Optional[str]:
    """Optional helper: official airport name from the database."""
    if not code:
        return None
    key = str(code).upper().strip()
    entry = _iata_db().get(key)
    if entry:
        return entry.get("name") or entry.get("city")
    return None
