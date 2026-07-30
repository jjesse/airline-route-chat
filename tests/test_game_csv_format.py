"""Tests for airline-sim game CSV column layout (ICAO)."""

from __future__ import annotations

import textwrap
from pathlib import Path

from route_finder import load_graph, find_routes


def test_game_csv_columns(tmp_path: Path):
    content = textwrap.dedent(
        """\
        Originating Airport,Org Airport Code,Destination Airport,Dest Airport Code,Distance (mi),Aircraft,Some Extra,Ignored
        Detroit,KDTW,Chicago,KORD,228,B737,foo,bar
        Chicago,KORD,Denver,KDEN,888,A320,baz,qux
        Detroit,KDTW,Denver,KDEN,1124,A321,x,y
        """
    )
    path = tmp_path / "game.csv"
    path.write_text(content, encoding="utf-8")

    G = load_graph(path)
    assert G.has_edge("KDTW", "KORD")
    assert G.has_edge("KORD", "KDEN")
    assert G.has_edge("KDTW", "KDEN")
    assert "B737" in G["KDTW"]["KORD"]["planes"]
    assert G["KDTW"]["KORD"]["distance"] == 228
    assert G["KDTW"]["KORD"]["duration"] is not None

    routes = find_routes(G, "KDTW", "KDEN", max_stops=2)
    assert routes
    paths = {r["route"] for r in routes}
    assert any("KDTW → KDEN" == p for p in paths)
    assert any("KORD" in p for p in paths)


def test_iata_query_against_icao_graph(tmp_path: Path):
    """Chat can use DTW while the graph stores KDTW."""
    content = textwrap.dedent(
        """\
        Org Airport Code,Dest Airport Code,Aircraft,Distance (mi)
        KDTW,KORD,B737,228
        KORD,KDEN,A320,888
        """
    )
    path = tmp_path / "icao.csv"
    path.write_text(content, encoding="utf-8")
    G = load_graph(path)
    routes = find_routes(G, "DTW", "DEN", max_stops=2)
    assert routes
    assert routes[0]["airports"][0] == "KDTW"
