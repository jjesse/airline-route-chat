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
    def test_sample_airports_have_coords(self):
        for code in ("DTW", "ORD", "DEN", "LAX", "ATL", "MIA", "SEA", "SFO", "MSP"):
            c = get_airport_coords(code)
            assert c is not None
            lat, lon = c
            assert 24 <= lat <= 50
            assert -130 <= lon <= -65


class TestPlotlyVisualization:
    def test_route_plotly_geo(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        assert routes
        fig = visualize_route_plotly(graph, routes[0], title="DTW → DEN")
        assert fig is not None
        assert len(fig.data) >= 1
        # Geographic maps use Scattergeo traces
        assert any(getattr(t, "type", None) == "scattergeo" or "geo" in t.__class__.__name__.lower()
                   or hasattr(t, "lat") for t in fig.data)

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
