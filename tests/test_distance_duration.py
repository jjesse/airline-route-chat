"""Tests for distance → duration conversion."""

from __future__ import annotations

import textwrap
from pathlib import Path

from route_finder import (
    distance_to_duration,
    cruise_speed_kts,
    load_graph,
    find_shortest_by_time,
    BLOCK_OVERHEAD_MINUTES,
)


class TestDistanceToDuration:
    def test_b737_statute_miles(self):
        # SEA–SFO is ~679 statute miles; expect roughly 1.5–2.5 hours block
        mins = distance_to_duration(679, "B737", unit="sm")
        assert mins is not None
        assert 90 < mins < 180

    def test_nm_unit(self):
        # 600 NM at 450 kts + 30 min overhead ≈ 110 min
        mins = distance_to_duration(600, "B737", unit="nm")
        assert mins is not None
        expected = BLOCK_OVERHEAD_MINUTES + (600 / 450) * 60
        assert abs(mins - expected) < 1.0

    def test_faster_widebody_shorter_time(self):
        slow = distance_to_duration(3000, "CRJ", unit="nm")
        fast = distance_to_duration(3000, "B787", unit="nm")
        assert slow is not None and fast is not None
        assert fast < slow

    def test_invalid_distance(self):
        assert distance_to_duration(0, "B737") is None
        assert distance_to_duration(-10, "B737") is None
        assert distance_to_duration(999999, "B737") is None

    def test_cruise_speed_known_types(self):
        assert cruise_speed_kts("B737") == 450
        assert cruise_speed_kts("A320") == 450
        assert cruise_speed_kts("unknown-thing") > 0


class TestLoadGraphFromDistance:
    def test_estimates_duration_from_miles(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,Distance
            SEA,SFO,B737,679
            SFO,LAX,A320,337
            """
        )
        path = tmp_path / "dist.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert G.has_edge("SEA", "SFO")
        assert "duration" in G["SEA"]["SFO"]
        assert G["SEA"]["SFO"]["duration"] > 60
        assert G["SEA"]["SFO"]["distance"] == 679

    def test_duration_column_wins_over_distance(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,DurationMinutes,Distance
            SEA,SFO,B737,110,679
            """
        )
        path = tmp_path / "both.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert G["SEA"]["SFO"]["duration"] == 110

    def test_nm_column(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,NM
            DTW,ORD,A320,200
            """
        )
        path = tmp_path / "nm.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert G["DTW"]["ORD"]["duration"] is not None
        assert G["DTW"]["ORD"]["distance_unit"] == "nm"

    def test_fastest_uses_estimated_duration(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,Miles
            AAA,BBB,B737,500
            AAA,CCC,B737,100
            CCC,BBB,B737,100
            """
        )
        # Use valid codes
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,Miles
            DTW,DEN,B737,1200
            DTW,ORD,B737,200
            ORD,DEN,B737,900
            """
        )
        path = tmp_path / "fast.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        best = find_shortest_by_time(G, "DTW", "DEN")
        assert best is not None
        assert best["total_duration"] is not None
