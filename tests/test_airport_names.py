"""Tests for airport name lookup used on map hovers."""

from airport_coords import airport_name, format_airport_label, get_airport_coords


def test_scel_name():
    name = airport_name("SCEL")
    assert name is not None
    assert "santiago" in name.lower() or "merino" in name.lower()


def test_kdtw_name():
    name = airport_name("KDTW")
    assert name is not None
    assert "detroit" in name.lower() or "wayne" in name.lower()


def test_format_label_includes_code_and_name():
    label = format_airport_label("SCEL")
    assert label.startswith("SCEL")
    assert "—" in label or "-" in label
    assert len(label) > 6


def test_scel_coords():
    c = get_airport_coords("SCEL")
    assert c is not None
    lat, lon = c
    # Santiago, Chile
    assert -34 < lat < -32
    assert -72 < lon < -70
