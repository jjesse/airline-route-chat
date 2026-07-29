"""Tests for resolve_airport, extract_airports, and sanitization."""

from route_finder import resolve_airport, extract_airports, _sanitize_code


class TestSanitizeCode:
    def test_valid_codes(self):
        assert _sanitize_code("DTW") == "DTW"
        assert _sanitize_code("ord") == "ORD"
        assert _sanitize_code("  lax  ") == "LAX"

    def test_strips_non_alnum_when_result_is_valid(self):
        # Non-alnum is removed; remaining exactly-3-char codes are accepted
        assert _sanitize_code("DTW!") == "DTW"
        assert _sanitize_code("LAX.") == "LAX"
        # "../etc" strips to "ETC" which is a valid 3-char code shape
        assert _sanitize_code("../etc") == "ETC"

    def test_rejects_bad(self):
        assert _sanitize_code("") is None
        assert _sanitize_code("AB") is None          # too short
        assert _sanitize_code("ABCD") is None        # too long
        assert _sanitize_code("../passwd") is None   # strips to PASSWD (6 chars)
        assert _sanitize_code(None) is None  # type: ignore[arg-type]


class TestResolveAirport:
    def test_iata_codes(self):
        assert resolve_airport("DTW") == "DTW"
        assert resolve_airport("ord") == "ORD"

    def test_city_names(self):
        assert resolve_airport("Detroit") == "DTW"
        assert resolve_airport("Chicago") == "ORD"
        assert resolve_airport("Los Angeles") == "LAX"
        assert resolve_airport("LA") == "LAX"
        assert resolve_airport("Seattle") == "SEA"
        assert resolve_airport("San Francisco") == "SFO"

    def test_rejects_garbage(self):
        assert resolve_airport("") is None
        assert resolve_airport("notanairport") is None
        assert resolve_airport("A" * 100) is None
        assert resolve_airport("../../passwd") is None


class TestExtractAirports:
    def test_from_to_codes(self):
        assert extract_airports("How do I get from DTW to DEN?") == ("DTW", "DEN")

    def test_from_to_cities(self):
        assert extract_airports("from Detroit to Denver") == ("DTW", "DEN")
        assert extract_airports("How do I get from Chicago to Los Angeles?") == ("ORD", "LAX")
        assert extract_airports("from San Francisco to Minneapolis") == ("SFO", "MSP")

    def test_simple_to(self):
        assert extract_airports("ORD to LAX") == ("ORD", "LAX")
        assert extract_airports("DTW-DEN") == ("DTW", "DEN")

    def test_between_and(self):
        assert extract_airports("route between Atlanta and Seattle") == ("ATL", "SEA")

    def test_rejects_empty_or_long(self):
        assert extract_airports("") == (None, None)
        assert extract_airports("hello world") == (None, None)
        assert extract_airports("x" * 600) == (None, None)

    def test_case_insensitive(self):
        o, d = extract_airports("from detroit to DENVER")
        assert o == "DTW"
        assert d == "DEN"
