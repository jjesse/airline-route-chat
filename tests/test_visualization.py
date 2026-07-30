"""Smoke tests for visualization helpers (must not crash)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CI / headless

from route_finder import find_routes, visualize_route, visualize_full_network, visualize_route_timeline_plotly
from geo_viz import visualize_route_plotly, visualize_full_network_plotly
from airport_coords import get_airport_coords


class TestMatplotlibVisualization:
    def test_visualize_route_returns_figure(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        assert routes
        fig = visualize_route(graph, routes[0], title="DTW → DEN")
        assert fig is not None
        assert len(fig.axes) >= 1

    def test_visualize_empty_route(self, graph):
        empty = {"airports": [], "route": "", "legs": [], "stops": 0}
        fig = visualize_route(graph, empty)
        assert fig is not None

    def test_visualize_full_network(self, graph):
        fig = visualize_full_network(graph)
        assert fig is not None
        assert len(fig.axes) >= 1


class TestGeoCoords:
    def test_dtw_coords(self):
        # Detroit Metro: ~42.21 N, 83.35 W
        c = get_airport_coords("DTW")
        assert c is not None
        lat, lon = c
        assert abs(lat - 42.21) < 0.05
        assert abs(lon - (-83.35)) < 0.05

    def test_sample_and_extra_airports(self):
        # Sample CSV airports + a few not in the sample fallback table
        for code in ("DTW", "ORD", "DEN", "LAX", "ATL", "MIA", "SEA", "SFO", "MSP", "JFK", "LHR", "NRT"):
            c = get_airport_coords(code)
            assert c is not None, f"missing coords for {code}"
            lat, lon = c
            assert -90 <= lat <= 90
            assert -180 <= lon <= 180

    def test_unknown_code(self):
        assert get_airport_coords("ZZZ") is None
        assert get_airport_coords("") is None
        assert get_airport_coords("AB") is None


class TestPlotlyVisualization:
    def test_route_plotly_geo(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        assert routes
        fig = visualize_route_plotly(graph, routes[0], title="DTW → DEN")
        assert fig is not None
        assert len(fig.data) >= 1
        assert any(hasattr(t, "lat") for t in fig.data)

    def test_route_plotly_empty(self, graph):
        empty = {"airports": [], "route": "", "legs": [], "stops": 0}
        fig = visualize_route_plotly(graph, empty)
        assert fig is not None

    def test_timeline_plotly(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        assert routes
        fig = visualize_route_timeline_plotly(routes[0])
        assert fig is not None
        assert len(fig.data) >= 1

    def test_timeline_empty(self):
        fig = visualize_route_timeline_plotly({"legs": []})
        assert fig is not None

    def test_full_network_plotly_geo(self, graph):
        fig = visualize_full_network_plotly(graph)
        assert fig is not None
        assert len(fig.data) >= 1
