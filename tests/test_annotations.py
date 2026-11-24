import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from tspanels import Note, Points, RefLine, Span, Style, VLine


@pytest.fixture
def ax():
    return plt.subplots()[1]


@pytest.fixture
def data():
    idx = pd.date_range("2024-01-01", periods=24, freq="h")
    return pd.DataFrame({"a": np.arange(24, dtype=float), "flag": [i % 5 == 0 for i in range(24)]}, index=idx)


def test_refline_falls_back_to_style_reference(ax, data):
    RefLine(1.0, "lvl").draw(ax, data, Style(reference="#123456"))
    assert ax.lines[0].get_color() == "#123456"
    assert ax.texts[0].get_color() == Style().ink_muted


def test_explicit_color_wins_over_style(ax, data):
    VLine(data.index[3], color="#abcdef").draw(ax, data, Style(reference="#123456"))
    assert ax.lines[0].get_color() == "#abcdef"


def test_points_mask_as_column_name(ax, data):
    Points("flag", "a").draw(ax, data, Style())
    assert len(ax.lines[0].get_xdata()) == int(data["flag"].sum())
    assert ax.lines[0].get_color() == Style().alert


def test_points_mask_as_series(ax, data):
    Points(data["a"] > 20, "a", color="#000000").draw(ax, data, Style())
    assert len(ax.lines[0].get_xdata()) == 3
    assert ax.lines[0].get_color() == "#000000"


def test_span_uses_shade(ax, data):
    Span(data.index[1], data.index[4]).draw(ax, data, Style(shade="#00ff00"))
    assert mcolors.to_hex(ax.patches[0].get_facecolor()) == "#00ff00"


def test_note_marker_edge_is_background_and_text_formatted(ax, data):
    Note(data.index[2], "v={y:.1f}", column="a").draw(ax, data, Style(background="#fafafa"))
    assert ax.lines[0].get_markeredgecolor() == "#fafafa"
    assert ax.lines[0].get_color() == Style().series[0]
    assert ax.texts[0].get_text() == f"v={data['a'].iloc[2]:.1f}"
    assert ax.texts[0].get_color() == Style().ink


def test_note_left_of_point_in_right_third(ax, data):
    Note(data.index[-2], "x", column="a").draw(ax, data, Style())
    assert ax.texts[0].get_horizontalalignment() == "right"


def test_note_missing_time_raises_key_error(ax, data):
    with pytest.raises(KeyError, match="2030"):
        Note("2030-01-01", "x", column="a").draw(ax, data, Style())


def test_naive_times_on_aware_index(ax, data):
    aware = data.tz_localize("UTC")
    VLine(str(data.index[3])).draw(ax, aware, Style())
    Span(str(data.index[1]), str(data.index[2])).draw(ax, aware, Style())
    Note(str(data.index[3]), "x", column="a").draw(ax, aware, Style())
    assert ax.texts[0].get_text() == "x"


def test_note_without_column_or_y_raises_value_error():
    with pytest.raises(ValueError, match="column= or y="):
        Note("2024-01-01", "x")


def test_note_on_duplicated_time_raises_value_error(ax, data):
    dup = pd.concat([data.iloc[:3], data.iloc[2:3], data.iloc[3:]])
    with pytest.raises(ValueError, match="2 times"):
        Note(dup.index[2], "x", column="a").draw(ax, dup, Style())
    Note(dup.index[2], "x", y=1.0).draw(ax, dup, Style())  # with y the duplicate is irrelevant
    assert ax.texts[0].get_text() == "x"


def test_band_between_columns_is_filled_in_shade(ax, data):
    from tspanels import Band

    d = data.assign(lo=data["a"] - 1, hi=data["a"] + 1)
    Band("lo", "hi", "limits").draw(ax, d, Style(shade="#123456"))
    (poly,) = ax.collections
    assert poly.get_label() == "limits"
    assert mcolors.to_hex(poly.get_facecolor()[0]) == "#123456"


def test_band_without_fill_draws_two_edges_with_one_legend_entry(ax, data):
    from tspanels import Band

    Band(-1.0, "a", "limits", fill=False).draw(ax, data, Style(reference="#654321"))
    assert len(ax.lines) == 2
    assert [ln.get_label() for ln in ax.lines] == ["limits", "_nolegend_"]
    assert all(mcolors.to_hex(ln.get_color()) == "#654321" for ln in ax.lines)
    assert list(ax.lines[0].get_ydata()) == [-1.0] * len(data)


def test_band_columns_lists_only_column_edges():
    from tspanels import Band

    assert Band("lo", 2.0).columns() == ["lo"]
    assert Band(0, 1).columns() == []


@pytest.mark.parametrize("make", [
    lambda c: RefLine(1.0, color=c),
    lambda c: VLine("2024-01-01 03:00", color=c),
    lambda c: Points("flag", "a", color=c),
    lambda c: Note("2024-01-01 03:00", "x", column="a", color=c),
])
def test_annotation_color_may_name_a_style_field(ax, data, make):
    make("alert").draw(ax, data, Style(alert="#c00000"))
    assert ax.lines[0].get_color() == "#c00000"


def test_span_color_may_name_a_style_field(ax, data):
    Span(data.index[2], data.index[5], color="series[1]").draw(ax, data, Style(series=("#111111", "#222222")))
    assert mcolors.to_hex(ax.patches[0].get_facecolor()) == "#222222"


def test_band_color_may_name_a_style_field(ax, data):
    from tspanels import Band
    Band(0, "a", fill=False, color="alert").draw(ax, data, Style(alert="#c00000"))
    assert {ln.get_color() for ln in ax.lines} == {"#c00000"}
