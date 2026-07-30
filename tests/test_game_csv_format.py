"""Tests for airline-sim game CSV column layout."""

from __future__ import annotations

import textwrap
from pathlib import Path

from route_finder import load_graph, find_routes


def test_game_csv_columns(tmp_path: Path):
    """Org/Dest Airport Code + Aircraft + Distance (mi); extra cols ignored."""
    content = textwrap.dedent(
        """\
        Originating Airport,Org Airport Code,Destination Airport,Dest Airport Code,Distance (mi),Aircraft,Some Extra,Ignored
        Detroit,DTW,Chicago,ORD,228,B737,foo,bar
        Chicago,ORD,Denver,DEN,888,A320,baz,qux
        Detroit,DTW,Denver,DEN,1124,A321,x,y
        """
    )
    path = tmp_path / "game.csv"
    path.write_text(content, encoding="utf-8")

    G = load_graph(path)
    assert G.has_edge("DTW", "ORD")
    assert G.has_edge("ORD", "DEN")
    assert G.has_edge("DTW", "DEN")
    assert "B737" in G["DTW"]["ORD"]["planes"]
    assert G["DTW"]["ORD"]["distance"] == 228
    assert G["DTW"]["ORD"]["duration"] is not None  # estimated from miles

    routes = find_routes(G, "DTW", "DEN", max_stops=2)
    assert routes
    # Direct + one-stop should both appear
    paths = {r["route"] for r in routes}
    assert any("DTW → DEN" == p for p in paths)
    assert any("ORD" in p for p in paths)


def test_prefers_code_columns_over_city_names(tmp_path: Path):
    content = textwrap.dedent(
        """\
        Originating Airport,Org Airport Code,Destination Airport,Dest Airport Code,Aircraft
        NotACity,SEA,AlsoFake,SFO,B737
        """
    )
    path = tmp_path / "codes.csv"
    path.write_text(content, encoding="utf-8")
    G = load_graph(path)
    assert G.has_edge("SEA", "SFO")
