"""Smoke tests for visualization helpers (must not crash)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CI / headless

from route_finder import (
    find_routes,
    visualize_route,
    visualize_full_network,
    visualize_route_plotly,
    visualize_route_timeline_plotly,
    visualize_full_network_plotly,
)


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


class TestPlotlyVisualization:
    def test_route_plotly(self, graph):
        routes = find_routes(graph, "DTW", "DEN", max_stops=1)
        assert routes
        fig = visualize_route_plotly(graph, routes[0], title="DTW → DEN")
        assert fig is not None
        assert len(fig.data) >= 1

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

    def test_full_network_plotly(self, graph):
        fig = visualize_full_network_plotly(graph)
        assert fig is not None
        assert len(fig.data) >= 1
