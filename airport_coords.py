"""Airport coordinates for geographic route maps (lat, lon).

Approximate WGS84 reference points for IATA codes used in sample data.
Extend this dict when adding airports to flights.csv.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

AIRPORT_COORDS: Dict[str, Tuple[float, float]] = {
    "DTW": (42.2124, -83.3534),   # Detroit Metro
    "ORD": (41.9742, -87.9073),   # Chicago O'Hare
    "DEN": (39.8561, -104.6737),  # Denver International
    "LAX": (33.9425, -118.4081),  # Los Angeles
    "ATL": (33.6407, -84.4277),   # Atlanta Hartsfield-Jackson
    "MIA": (25.7959, -80.2870),   # Miami
    "SEA": (47.4502, -122.3088),  # Seattle-Tacoma
    "SFO": (37.6213, -122.3790),  # San Francisco
    "MSP": (44.8848, -93.2223),   # Minneapolis-St Paul
}


def get_airport_coords(code: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for an IATA code, or None if unknown."""
    if not code:
        return None
    return AIRPORT_COORDS.get(str(code).upper().strip())
