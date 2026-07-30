"""Tests for path finding, ranking, and helpers."""

from __future__ import annotations

from route_finder import (
    find_routes,
    find_shortest_by_time,
    clamp_max_stops,
    format_duration,
    format_routes,
    MAX_STOPS,
)


class TestClampMaxStops:
    def test_normal(self):
        assert clamp_max_stops(3) == 3

    def test_clamps_high(self):
        assert clamp_max_stops(100) == MAX_STOPS

    def test_clamps_low(self):
        assert clamp_max_stops(-5) == 0

    def test_bad_input(self):
        assert clamp_max_stops("nope") == 3  # type: ignore[arg-type]


class TestFindRoutes:
    def test_direct_flight(self, graph):
        routes = find_routes(graph, "KDTW", "KDEN", max_stops=0)
        assert any(r["stops"] == 0 and r["airports"] == ["KDTW", "KDEN"] for r in routes)

    def test_iata_query_maps_to_icao(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        assert routes
        assert routes[0]["airports"][0] == "KDTW"

    def test_one_stop_connection(self, graph):
        routes = find_routes(graph, "KDTW", "KDEN", max_stops=1)
        paths = [r["airports"] for r in routes]
        assert ["KDTW", "KDEN"] in paths
        assert ["KDTW", "KORD", "KDEN"] in paths

    def test_sorted_by_stops_then_duration(self, graph):
        routes = find_routes(graph, "KDTW", "KDEN", max_stops=2)
        assert routes[0]["stops"] <= routes[-1]["stops"]
        assert routes[0]["stops"] == 0

    def test_unknown_airport(self, graph):
        assert find_routes(graph, "XXXX", "KDEN") == []
        assert find_routes(graph, "KDTW", "XXXX") == []

    def test_same_airport(self, graph):
        routes = find_routes(graph, "KDTW", "KDTW")
        assert len(routes) == 1
        assert routes[0]["stops"] == 0
        assert routes[0]["airports"] == ["KDTW"]

    def test_max_stops_clamped(self, graph):
        routes = find_routes(graph, "KDTW", "KLAX", max_stops=99)
        assert isinstance(routes, list)
        for r in routes:
            assert r["stops"] <= MAX_STOPS

    def test_sanitizes_input_codes(self, graph):
        routes = find_routes(graph, "kdtw", "kden", max_stops=1)
        assert len(routes) >= 1


class TestShortestByTime:
    def test_prefers_faster_path(self, graph):
        best = find_shortest_by_time(graph, "KDTW", "KDEN")
        assert best is not None
        assert best["airports"] == ["KDTW", "KDEN"]
        assert best["total_duration"] is not None

    def test_multi_leg_when_needed(self, graph):
        best = find_shortest_by_time(graph, "KDTW", "KLAX")
        assert best is not None
        assert best["airports"][0] == "KDTW"
        assert best["airports"][-1] == "KLAX"
        assert best["total_duration"] is not None

    def test_unreachable(self, graph):
        assert find_shortest_by_time(graph, "KDTW", "XXXX") is None


class TestFormatting:
    def test_format_duration(self):
        assert format_duration(None) == "?"
        assert format_duration(45) == "45m"
        assert format_duration(60) == "1h"
        assert format_duration(90) == "1h 30m"

    def test_format_routes_empty(self):
        assert "No routes" in format_routes([])

    def test_format_routes_content(self, graph):
        routes = find_routes(graph, "KDTW", "KDEN", max_stops=1)
        text = format_routes(routes, limit=2)
        assert "KDTW" in text
        assert "KDEN" in text
