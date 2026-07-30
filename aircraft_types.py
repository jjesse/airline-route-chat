"""Classify aircraft types for passenger vs cargo routing."""

from __future__ import annotations

import re

# Words that mark an aircraft string as cargo / freighter.
_CARGO_WORDS = re.compile(
    r"\b(freighter|freight|cargo|all[\s-]?cargo|belly[\s-]?cargo)\b",
    re.IGNORECASE,
)

# Common freighter model codes ending in F (B777F, 747-8F, A330F, MD-11F, …).
_CARGO_MODEL_F = re.compile(
    r"^(?:B?7(?:37|47|57|67|77)|A3(?:00|10|30|50)|MD[\s-]?1?1|DC[\s-]?10)"
    r"[A-Z0-9\-]*F$",
    re.IGNORECASE,
)


def is_cargo_aircraft(plane: str) -> bool:
    """Return True if this aircraft type is a freighter / cargo-only type.

    Passenger routes must never use these. Examples matched:
      - "B777 Freighter", "Boeing 777 Freighter"
      - "A330 Cargo", "MD-11 Freight"
      - "B777F", "777F", "747-8F", "A330F"
    """
    if not plane or not isinstance(plane, str):
        return False

    text = plane.strip()
    if not text:
        return False

    if _CARGO_WORDS.search(text):
        return True

    compact = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    # Re-check model+F on compact form (B777F, 7478F, A330F, MD11F)
    if re.match(
        r"^(?:B?7(?:37|47|57|67|77)|A3(?:00|10|30|50)|MD1?1|DC10)[A-Z0-9]*F$",
        compact,
    ):
        return True

    # Spaced original model+F ("747-8F")
    spaced = re.sub(r"\s+", "", text)
    if _CARGO_MODEL_F.match(spaced):
        return True

    return False
