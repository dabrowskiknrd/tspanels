import dataclasses
import subprocess
import sys

import pytest

from tspanels import DEFAULT_STYLE, Style, get_default_style, set_default_style
from tspanels.style import resolve_style


def test_default_values_match_source():
    s = Style()
    assert s.series == ("#2a78d6", "#eb6834", "#1baf7a", "#8a8984")
    assert (s.ink, s.ink_muted, s.axis, s.grid) == ("#0b0b0b", "#52514e", "#b5b4ae", "#e5e4e0")
    assert (s.reference, s.shade, s.alert, s.background) == ("#8a8984", "#8a8984", "#d03b3b", "white")


def test_style_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Style().alert = "#000"


def test_set_and_get_default_style():
    assert get_default_style() is DEFAULT_STYLE
    custom = Style(alert="#c00")
    set_default_style(custom)
    assert get_default_style() is custom
    assert resolve_style(None) is custom
    assert resolve_style(DEFAULT_STYLE) is DEFAULT_STYLE


def test_import_without_polars():
    code = "import sys; sys.modules['polars'] = None; import tspanels"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0


def test_color_returns_the_field_named_by_a_string():
    s = Style(alert="#c00000", reference="#333333")
    assert s.color("alert") == "#c00000"
    assert s.color("reference") == "#333333"
    assert s.color("ink_muted") == Style().ink_muted


def test_color_returns_a_series_color_by_position():
    s = Style(series=("#111111", "#222222", "#333333"))
    assert s.color("series[0]") == "#111111"
    assert s.color("series[2]") == "#333333"


def test_color_beyond_the_series_takes_the_last_series_color():
    assert Style(series=("#111111", "#222222")).color("series[5]") == "#222222"


def test_color_passes_other_values_unchanged():
    s = Style()
    assert s.color("#abcdef") == "#abcdef"
    assert s.color("red") == "red"
    assert s.color(None) is None
    assert s.color((0.1, 0.2, 0.3)) == (0.1, 0.2, 0.3)
