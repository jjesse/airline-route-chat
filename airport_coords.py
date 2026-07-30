"""Airport coordinates for geographic route maps (lat, lon).

Looks up latitude/longitude from ICAO (preferred) or IATA codes using the
offline `airportsdata` database.
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


def get_airport_coords(code: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for an ICAO or IATA code, or None if unknown."""
    if not code or not isinstance(code, str):
        return None

    key = code.upper().strip()
    if not (3 <= len(key) <= 4) or not key.isalnum():
        return None

    if key in LOCAL_OVERRIDES:
        return LOCAL_OVERRIDES[key]

    # Prefer ICAO database for 4-letter codes
    if len(key) == 4:
        entry = _icao_db().get(key)
        if entry:
            try:
                return (float(entry["lat"]), float(entry["lon"]))
            except (KeyError, TypeError, ValueError):
                pass

    # IATA database for 3-letter codes
    if len(key) == 3:
        entry = _iata_db().get(key)
        if entry:
            try:
                return (float(entry["lat"]), float(entry["lon"]))
            except (KeyError, TypeError, ValueError):
                pass
        # US convention: try K + IATA as ICAO
        k_code = "K" + key
        entry = _icao_db().get(k_code)
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
    entry = _icao_db().get(key) or _iata_db().get(key)
    if entry:
        return entry.get("name") or entry.get("city")
    if len(key) == 3:
        entry = _icao_db().get("K" + key)
        if entry:
            return entry.get("name") or entry.get("city")
    return None


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
    # Common US fallback
    return "K" + key
