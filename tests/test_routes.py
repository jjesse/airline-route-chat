"""Tests for path finding, ranking, and helpers."""

from __future__ import annotations

import pytest

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
        routes = find_routes(graph, "DTW", "DEN", max_stops=0)
        # With max_stops=0 only the direct edge is allowed
        assert any(r["stops"] == 0 and r["airports"] == ["DTW", "DEN"] for r in routes)

    def test_one_stop_connection(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        paths = [r["airports"] for r in routes]
        assert ["DTW", "DEN"] in paths
        assert ["DTW", "ORD", "DEN"] in paths

    def test_sorted_by_stops_then_duration(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=2)
        assert routes[0]["stops"] <= routes[-1]["stops"]
        # Direct should come first
        assert routes[0]["stops"] == 0

    def test_unknown_airport(self, graph):
        assert find_routes(graph, "XXX", "DEN") == []
        assert find_routes(graph, "DTW", "XXX") == []

    def test_same_airport(self, graph):
        routes = find_routes(graph, "DTW", "DTW")
        assert len(routes) == 1
        assert routes[0]["stops"] == 0
        assert routes[0]["airports"] == ["DTW"]

    def test_max_stops_clamped(self, graph):
        # Even if caller passes a huge number, search still works and is bounded
        routes = find_routes(graph, "DTW", "LAX", max_stops=99)
        assert isinstance(routes, list)
        for r in routes:
            assert r["stops"] <= MAX_STOPS

    def test_sanitizes_input_codes(self, graph):
        routes = find_routes(graph, "dtw", "den", max_stops=1)
        assert len(routes) >= 1


class TestShortestByTime:
    def test_prefers_faster_path(self, graph):
        # Direct DTW-DEN is 175 min
        # DTW-ORD-DEN is 70+145 = 215 min
        best = find_shortest_by_time(graph, "DTW", "DEN")
        assert best is not None
        assert best["airports"] == ["DTW", "DEN"]
        assert best["total_duration"] == 175

    def test_multi_leg_when_needed(self, graph):
        # No direct DTW-LAX in the tiny sample fixture... wait, sample doesn't have DTW-LAX
        # ORD-LAX exists. DTW-ORD-LAX = 70+250 = 320
        best = find_shortest_by_time(graph, "DTW", "LAX")
        assert best is not None
        assert best["airports"][0] == "DTW"
        assert best["airports"][-1] == "LAX"
        assert best["total_duration"] is not None

    def test_unreachable(self, graph):
        # Add nothing that reaches a fake node — node not in graph
        assert find_shortest_by_time(graph, "DTW", "XXX") is None


class TestFormatting:
    def test_format_duration(self):
        assert format_duration(None) == "?"
        assert format_duration(45) == "45m"
        assert format_duration(60) == "1h"
        assert format_duration(90) == "1h 30m"

    def test_format_routes_empty(self):
        assert "No routes" in format_routes([])

    def test_format_routes_content(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        text = format_routes(routes, limit=2)
        assert "DTW" in text
        assert "DEN" in text
