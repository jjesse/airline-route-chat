"""Tests for resolve_airport, extract_airports, and sanitization (ICAO-first)."""

from route_finder import resolve_airport, extract_airports, _sanitize_code, match_graph_airport
import networkx as nx


class TestSanitizeCode:
    def test_icao_codes(self):
        assert _sanitize_code("KDTW") == "KDTW"
        assert _sanitize_code("kord") == "KORD"
        assert _sanitize_code("  KSFO  ") == "KSFO"

    def test_iata_still_accepted(self):
        assert _sanitize_code("DTW") == "DTW"
        assert _sanitize_code("ord") == "ORD"

    def test_strips_non_alnum_when_result_is_valid(self):
        assert _sanitize_code("KDTW!") == "KDTW"
        assert _sanitize_code("DTW!") == "DTW"

    def test_rejects_bad(self):
        assert _sanitize_code("") is None
        assert _sanitize_code("AB") is None
        assert _sanitize_code("ABCDE") is None  # too long
        assert _sanitize_code(None) is None  # type: ignore[arg-type]


class TestResolveAirport:
    def test_icao_codes(self):
        assert resolve_airport("KDTW") == "KDTW"
        assert resolve_airport("kord") == "KORD"

    def test_iata_codes(self):
        assert resolve_airport("DTW") == "DTW"
        assert resolve_airport("ord") == "ORD"

    def test_city_names_to_icao(self):
        assert resolve_airport("Detroit") == "KDTW"
        assert resolve_airport("Chicago") == "KORD"
        assert resolve_airport("Los Angeles") == "KLAX"
        assert resolve_airport("Seattle") == "KSEA"
        assert resolve_airport("San Francisco") == "KSFO"

    def test_rejects_garbage(self):
        assert resolve_airport("") is None
        assert resolve_airport("notanairport") is None
        assert resolve_airport("A" * 100) is None


class TestMatchGraphAirport:
    def test_icao_to_iata_and_back(self):
        G = nx.DiGraph()
        G.add_edge("KDTW", "KDEN")
        assert match_graph_airport(G, "KDTW") == "KDTW"
        assert match_graph_airport(G, "DTW") == "KDTW"

    def test_iata_graph_accepts_icao_query(self):
        G = nx.DiGraph()
        G.add_edge("DTW", "DEN")
        assert match_graph_airport(G, "KDTW") == "DTW"
        assert match_graph_airport(G, "DTW") == "DTW"


class TestExtractAirports:
    def test_from_to_icao(self):
        assert extract_airports("How do I get from KDTW to KDEN?") == ("KDTW", "KDEN")

    def test_from_to_iata(self):
        assert extract_airports("How do I get from DTW to DEN?") == ("DTW", "DEN")

    def test_from_to_cities(self):
        assert extract_airports("from Detroit to Denver") == ("KDTW", "KDEN")
        assert extract_airports("How do I get from Chicago to Los Angeles?") == ("KORD", "KLAX")

    def test_simple_to(self):
        assert extract_airports("KORD to KLAX") == ("KORD", "KLAX")
        assert extract_airports("ORD to LAX") == ("ORD", "LAX")

    def test_rejects_empty_or_long(self):
        assert extract_airports("") == (None, None)
        assert extract_airports("hello world") == (None, None)
        assert extract_airports("x" * 600) == (None, None)
