"""Smoke tests for visualization helpers (must not crash)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CI / headless

from route_finder import find_routes, visualize_route, visualize_full_network


class TestVisualization:
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
