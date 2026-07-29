"""Shared fixtures for airline-route-chat tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from route_finder import load_graph


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Minimal valid flights CSV used by most tests."""
    content = textwrap.dedent(
        """\
        Originating Airport,Destination Airport,Airplane Type,DurationMinutes
        DTW,ORD,A320,70
        ORD,DEN,B737,145
        DTW,DEN,A321,175
        ORD,LAX,B757,250
        DEN,LAX,A320,130
        """
    )
    path = tmp_path / "flights.csv"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def graph(sample_csv: Path):
    return load_graph(sample_csv)


@pytest.fixture
def repo_flights_csv() -> Path:
    """Path to the real sample flights.csv in the repo root."""
    return Path(__file__).resolve().parent.parent / "flights.csv"
