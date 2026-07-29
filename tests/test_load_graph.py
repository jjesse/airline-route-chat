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
        assert G.has_edge("DTW", "ORD")
        assert G.has_edge("ORD", "DEN")
        assert "A320" in G["DTW"]["ORD"]["planes"]
        assert G["DTW"]["ORD"]["duration"] == 70

    def test_loads_repo_csv(self, repo_flights_csv: Path):
        if not repo_flights_csv.exists():
            pytest.skip("repo flights.csv not present")
        G = load_graph(repo_flights_csv)
        assert G.number_of_nodes() > 5
        assert G.number_of_edges() > 10

    def test_merges_duplicate_edges(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,DurationMinutes
            DTW,ORD,A320,70
            DTW,ORD,B737,65
            """
        )
        path = tmp_path / "dup.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert set(G["DTW"]["ORD"]["planes"]) == {"A320", "B737"}
        # shortest duration kept
        assert G["DTW"]["ORD"]["duration"] == 65


class TestLoadGraphValidation:
    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(ValueError, match="not found"):
            load_graph(tmp_path / "nope.csv")

    def test_missing_columns(self, tmp_path: Path):
        path = tmp_path / "bad.csv"
        path.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must contain columns"):
            load_graph(path)

    def test_rejects_oversized_row_count(self, tmp_path: Path, monkeypatch):
        # Temporarily lower the limit so the test stays fast
        import route_finder as rf

        monkeypatch.setattr(rf, "MAX_CSV_ROWS", 3)

        lines = ["Originating Airport,Destination Airport,Airplane Type"]
        for i in range(5):
            lines.append(f"A{i:02d},B{i:02d},A320")
        # Need valid 3-letter codes
        lines = ["Originating Airport,Destination Airport,Airplane Type"]
        codes = [f"A{i:02d}" for i in range(10)]  # A00 etc not valid 3-char pure
        # Use proper codes
        lines = ["Originating Airport,Destination Airport,Airplane Type"]
        for i in range(5):
            o = f"X{i:02d}"
            d = f"Y{i:02d}"
            lines.append(f"{o},{d},A320")

        path = tmp_path / "big.csv"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="maximum allowed"):
            load_graph(path)

    def test_skips_invalid_airport_codes(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,DurationMinutes
            DTW,ORD,A320,70
            BADCODE,ORD,A320,50
            DTW,ZZ,A320,50
            ../X,ORD,A320,50
            """
        )
        path = tmp_path / "dirty.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        # Only the valid DTW->ORD edge should exist
        assert G.number_of_edges() == 1
        assert G.has_edge("DTW", "ORD")

    def test_invalid_duration_ignored(self, tmp_path: Path):
        content = textwrap.dedent(
            """\
            Originating Airport,Destination Airport,Airplane Type,DurationMinutes
            DTW,ORD,A320,-10
            ORD,DEN,B737,999999
            DEN,LAX,A320,130
            """
        )
        path = tmp_path / "dur.csv"
        path.write_text(content, encoding="utf-8")
        G = load_graph(path)
        assert "duration" not in G["DTW"]["ORD"] or G["DTW"]["ORD"].get("duration") is None
        assert G["DEN"]["LAX"]["duration"] == 130
