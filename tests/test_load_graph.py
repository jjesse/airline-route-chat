"""Tests for CSV loading, validation, and resource limits."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from route_finder import load_graph, MAX_CSV_ROWS


class TestLoadGraphHappyPath:
    def test_loads_sample(self, sample_csv: Path):
        G = load_graph(sample_csv)
        assert G.number_of_nodes() >= 4
        assert G.has_edge("KDTW", "KORD")
        assert G.has_edge("KORD", "KDEN")
        assert "A320" in G["KDTW"]["KORD"]["planes"]
        assert G["KDTW"]["KORD"]["duration"] is not None

    def test_loads_repo_csv(self, repo_flights_csv: Path):
        if not repo_flights_csv.exists():
            pytest.skip("repo flights.csv not present")
        G = load_graph(repo_flights_csv)
        assert G.number_of_nodes() > 5
        assert G.number_of_edges() > 10

    def test_merges_duplicate_edges(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Org Airport Code,Dest Airport Code,Aircraft,Distance (mi)
            KDTW,KORD,A320,228
            KDTW,KORD,B737,228
            """
        )
        path = tmp_path / "dup.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert set(G["KDTW"]["KORD"]["planes"]) == {"A320", "B737"}


class TestLoadGraphValidation:
    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(ValueError, match="not found"):
            load_graph(tmp_path / "nope.csv")

    def test_missing_columns(self, tmp_path: Path):
        path = tmp_path / "bad.csv"
        path.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="origin and destination"):
            load_graph(path)

    def test_rejects_oversized_row_count(self, tmp_path: Path, monkeypatch):
        import route_finder as rf

        monkeypatch.setattr(rf, "MAX_CSV_ROWS", 3)

        lines = ["Org Airport Code,Dest Airport Code,Aircraft"]
        for i in range(5):
            o = f"K{i:02d}A"
            d = f"K{i:02d}B"
            lines.append(f"{o},{d},A320")

        path = tmp_path / "big.csv"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="maximum allowed"):
            load_graph(path)

    def test_skips_invalid_airport_codes(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Org Airport Code,Dest Airport Code,Aircraft,Distance (mi)
            KDTW,KORD,A320,228
            BADCODE,KORD,A320,50
            KDTW,ZZ,A320,50
            """
        )
        path = tmp_path / "dirty.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert G.number_of_edges() == 1
        assert G.has_edge("KDTW", "KORD")

    def test_invalid_duration_ignored(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Org Airport Code,Dest Airport Code,Aircraft,DurationMinutes
            KDTW,KORD,A320,-10
            KORD,KDEN,B737,999999
            KDEN,KLAX,A320,130
            """
        )
        path = tmp_path / "dur.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert G["KDEN"]["KLAX"]["duration"] == 130
