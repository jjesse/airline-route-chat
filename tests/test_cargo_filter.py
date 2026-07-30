"""Cargo aircraft must not appear on passenger routes."""

from __future__ import annotations

import textwrap
from pathlib import Path

from route_finder import is_cargo_aircraft, load_graph, find_routes


class TestIsCargoAircraft:
    def test_explicit_freighter(self):
        assert is_cargo_aircraft("B777 Freighter") is True
        assert is_cargo_aircraft("Boeing 777 Freighter") is True
        assert is_cargo_aircraft("747-8 Freighter") is True

    def test_cargo_keyword(self):
        assert is_cargo_aircraft("A330 Cargo") is True
        assert is_cargo_aircraft("MD-11 Freight") is True

    def test_f_suffix_models(self):
        assert is_cargo_aircraft("B777F") is True
        assert is_cargo_aircraft("777F") is True
        assert is_cargo_aircraft("A330F") is True
        assert is_cargo_aircraft("747-8F") is True

    def test_passenger_not_cargo(self):
        assert is_cargo_aircraft("B777") is False
        assert is_cargo_aircraft("B737") is False
        assert is_cargo_aircraft("A320") is False
        assert is_cargo_aircraft("A321neo") is False
        assert is_cargo_aircraft("E175") is False


class TestLoadGraphSkipsCargo:
    def test_cargo_only_edge_excluded(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Org Airport Code,Dest Airport Code,Aircraft,Distance (mi)
            KDTW,KORD,B777 Freighter,228
            KORD,KDEN,A320,888
            """
        )
        path = tmp_path / "cargo.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert not G.has_edge("KDTW", "KORD")
        assert G.has_edge("KORD", "KDEN")

    def test_passenger_kept_when_mixed_rows(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Org Airport Code,Dest Airport Code,Aircraft,Distance (mi)
            KDTW,KORD,B777 Freighter,228
            KDTW,KORD,B737,228
            """
        )
        path = tmp_path / "mixed.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert G.has_edge("KDTW", "KORD")
        planes = G["KDTW"]["KORD"]["planes"]
        assert "B737" in planes
        assert not any(is_cargo_aircraft(p) for p in planes)

    def test_routes_never_use_cargo_leg(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Org Airport Code,Dest Airport Code,Aircraft,Distance (mi)
            KDTW,KDEN,B777 Freighter,1124
            KDTW,KORD,B737,228
            KORD,KDEN,A320,888
            """
        )
        path = tmp_path / "routes.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        routes = find_routes(G, "KDTW", "KDEN", max_stops=2)
        assert routes
        # Direct freighter path must not exist; one-stop passenger should
        for r in routes:
            for leg in r["legs"]:
                for p in leg["planes"]:
                    assert not is_cargo_aircraft(p)
        paths = [r["airports"] for r in routes]
        assert ["KDTW", "KORD", "KDEN"] in paths
        assert ["KDTW", "KDEN"] not in paths
