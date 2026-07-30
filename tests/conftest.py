"""Shared fixtures for airline-route-chat tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from route_finder import load_graph


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Minimal valid flights CSV (ICAO codes) used by most tests."""
    content = textwrap.dedent(
        """\
        Originating Airport,Org Airport Code,Destination Airport,Dest Airport Code,Distance (mi),Aircraft
        Detroit,KDTW,Chicago,KORD,228,A320
        Chicago,KORD,Denver,KDEN,888,B737
        Detroit,KDTW,Denver,KDEN,1124,A321
        Chicago,KORD,Los Angeles,KLAX,1744,B757
        Denver,KDEN,Los Angeles,KLAX,862,A320
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
