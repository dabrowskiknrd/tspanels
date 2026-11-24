import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import pytest

from tspanels import (
    Line,
    Note,
    Panel,
    Points,
    Span,
    Style,
    VLine,
    plot_panels,
    set_default_style,
    style_axis,
)


@pytest.fixture
def data():
    idx = pd.date_range("2024-01-01", periods=48, freq="30min")
    rng = np.random.default_rng(0)
    df = pd.DataFrame({c: rng.normal(size=48) for c in "abcdefg"}, index=idx)
    df["missing"] = 0
    df.iloc[[5, 6, 30], df.columns.get_loc("missing")] = 1
    df["empty"] = np.nan
    return df


def crosses(ax):
    return [ln for ln in ax.lines if ln.get_marker() == "x"]


def legend_labels(ax):
    return ax.get_legend_handles_labels()[1]


def test_line_colors_skip_explicit_colors(data):
    _, (ax,) = plot_panels(data, [Panel([Line("a"), Line("b", color="#2a78d6"), Line("c")])])
    assert [ln.get_color() for ln in ax.lines[:3]] == ["#eb6834", "#2a78d6", "#1baf7a"]


def test_extra_lines_take_last_series_color(data):
    _, (ax,) = plot_panels(data, [Panel(list("abcdef"))])
    assert [ln.get_color() for ln in ax.lines[4:6]] == ["#8a8984", "#8a8984"]


def test_style_argument(data):
    _, (ax,) = plot_panels(data, ["a"], style=Style(series=("#111111",)))
    assert ax.lines[0].get_color() == "#111111"


def test_default_style_used_without_style_argument(data):
    set_default_style(Style(series=("#222222",)))
    _, (ax,) = plot_panels(data, ["a"])
    assert ax.lines[0].get_color() == "#222222"


def test_no_gap_markers_by_default(data):
    _, (ax,) = plot_panels(data, ["a"])
    assert crosses(ax) == []


def test_gaps_by_column_and_label_in_first_panel_only(data):
    _, axes = plot_panels(data, ["a", "b"], gaps="missing", gap_label="no reading")
    assert len(crosses(axes[0])[0].get_xdata()) == 3
    assert len(crosses(axes[1])[0].get_xdata()) == 3
    assert "no reading" in legend_labels(axes[0])
    assert "no reading" not in legend_labels(axes[1])


def test_gaps_by_boolean_series_in_alert_color(data):
    _, (ax,) = plot_panels(data, ["a"], gaps=data["a"] > 1, style=Style(alert="#ff0000"))
    assert len(crosses(ax)[0].get_xdata()) == int((data["a"] > 1).sum())
    assert crosses(ax)[0].get_color() == "#ff0000"


def test_gaps_missing_column_raises(data):
    with pytest.raises(KeyError, match="nope"):
        plot_panels(data, ["a"], gaps="nope")


def test_shared_annotation_legend_first_panel_only_custom_type(data):
    class Band:
        def draw(self, ax, data, style):
            ax.axhline(0, label="band")
            ax.text(0, 0, "visible")

    _, axes = plot_panels(data, ["a", "b"], annotations=[Band()])
    assert "band" in legend_labels(axes[0])
    assert "band" not in legend_labels(axes[1])
    assert any(t.get_text() == "visible" for t in axes[1].texts)


def test_shared_vline_label_text_in_every_panel(data):
    _, axes = plot_panels(data, ["a", "b"], annotations=[VLine(data.index[10], "event")])
    assert all(any(t.get_text() == "event" for t in ax.texts) for ax in axes)


def test_no_data_notice(data):
    _, (ax,) = plot_panels(data, ["empty"])
    assert any(t.get_text() == "no data in this period" for t in ax.texts)


def test_panel_title_rules(data):
    _, axes = plot_panels(data, [Panel([Line("a", "A label")]), "b", Panel(["c", "d"]), ("e", "E")])
    assert [ax.get_title(loc="left") for ax in axes] == ["A label", "b", "", "E"]


def test_panel_heights_and_figure_size(data):
    fig, axes = plot_panels(data, [Panel(["a"], height=2), "b"], width=10, panel_height=2)
    assert tuple(fig.get_size_inches()) == (10, 6)
    fig.canvas.draw()
    assert axes[0].get_position().height > 1.5 * axes[1].get_position().height


def test_missing_columns_raise(data):
    with pytest.raises(KeyError, match="zz"):
        plot_panels(data, [Panel(["a"], annotations=[Points("flagzz", "zz")])])


def test_zero_rows_raise(data):
    with pytest.raises(ValueError, match="no rows"):
        plot_panels(data.iloc[:0], ["a"])


def test_polars_input(data):
    pl = pytest.importorskip("polars")
    frame = pl.from_pandas(data.reset_index(names="t"))
    _, (ax,) = plot_panels(frame, ["a"], time="t")
    assert len(ax.lines[0].get_xdata()) == 48


def test_dict_input(data):
    _, (ax,) = plot_panels({"x": data["a"], "y": data["b"].iloc[:10]}, [Panel(["x", "y"])])
    assert len(ax.lines[1].get_xdata()) == 48


def test_background_applied(data):
    fig, (ax,) = plot_panels(data, ["a"], style=Style(background="#fafafa"))
    assert mcolors.to_hex(fig.get_facecolor()) == "#fafafa"
    assert mcolors.to_hex(ax.get_facecolor()) == "#fafafa"


def test_title_color_and_text(data):
    fig, _ = plot_panels(data, ["a"], title="Run 7\nweek 1", style=Style(ink="#010101"))
    assert fig._suptitle.get_text() == "Run 7\nweek 1"
    assert fig._suptitle.get_color() == "#010101"


def test_style_axis_standalone_uses_default_style(data):
    import matplotlib.pyplot as plt

    set_default_style(Style(axis="#0000ff"))
    ax = plt.subplots()[1]
    style_axis(ax)
    assert mcolors.to_hex(ax.spines["left"].get_edgecolor()) == "#0000ff"
    assert not ax.spines["top"].get_visible()


def test_shared_container_annotation_legend_first_panel_only(data):
    class Bars:
        def draw(self, ax, data, style):
            ax.bar(data.index[:3], [1, 2, 3], width=0.01, label="bars")

    _, axes = plot_panels(data, ["a", "b"], annotations=[Bars()])
    assert "bars" in legend_labels(axes[0])
    assert "bars" not in legend_labels(axes[1])


def test_rows_without_columns_report_missing_columns(data):
    with pytest.raises(KeyError, match="'a'"):
        plot_panels(pd.DataFrame(index=data.index), ["a"])


def test_error_during_drawing_closes_the_figure(data):
    import matplotlib.pyplot as plt

    class Broken:
        def draw(self, ax, data, style):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        plot_panels(data, ["a"], annotations=[Broken()])
    assert plt.get_fignums() == []


def test_bare_string_layout_draws_one_panel(data):
    _, axes = plot_panels(data, "a")
    assert len(axes) == 1
    assert axes[0].get_title(loc="left") == "a"


def test_pair_of_two_columns_raises(data):
    with pytest.raises(ValueError, match="Panel"):
        plot_panels(data, [("a", "b")])


def test_require_gaps_false_skips_an_absent_gap_column(data):
    _, (ax,) = plot_panels(data, ["a"], gaps="nope", require_gaps=False)
    assert crosses(ax) == []


def test_require_gaps_false_still_marks_a_present_gap_column(data):
    _, (ax,) = plot_panels(data, ["a"], gaps="missing", require_gaps=False)
    assert len(crosses(ax)[0].get_xdata()) == 3


def test_partial_with_project_defaults_can_be_overridden(data):
    from functools import partial

    project_plot = partial(plot_panels, gaps="missing", require_gaps=False, gap_label="hole", width=9)
    fig, (ax,) = project_plot(data, ["a"], width=7)
    assert fig.get_size_inches()[0] == 7
    assert "hole" in legend_labels(ax)


def test_required_columns_in_order_without_duplicates():
    from tspanels import Band, Note, required_columns

    cols = required_columns(
        ["a", Panel(["b", "a"], annotations=[Points("flag", "c"), Band("lo", 3.0)])],
        annotations=[Note("2024-01-01", "x", column="d")], gaps="missing")
    assert cols == ["a", "b", "flag", "c", "lo", "d", "missing"]


def test_required_columns_uses_a_columns_method_of_user_annotations():
    from tspanels import required_columns

    class Custom:
        def columns(self):
            return ["u", "v"]

        def draw(self, ax, data, style):
            pass

    assert required_columns(["a"], annotations=[Custom()]) == ["a", "u", "v"]


def test_annotation_columns_method_is_checked_before_drawing(data):
    from tspanels import Band

    with pytest.raises(KeyError, match="nope"):
        plot_panels(data, [Panel(["a"], annotations=[Band("nope", 1.0)])])


def test_line_color_may_name_a_style_field(data):
    _, (ax,) = plot_panels(data, [Panel([Line("a", color="alert")])], style=Style(alert="#c00000"))
    assert ax.lines[0].get_color() == "#c00000"


def test_line_color_named_by_series_position_is_skipped_by_automatic_colors(data):
    _, (ax,) = plot_panels(data, [Panel([Line("a"), Line("b", color="series[0]"), Line("c")])])
    assert [ln.get_color() for ln in ax.lines[:3]] == ["#eb6834", "#2a78d6", "#1baf7a"]


def test_line_color_named_by_style_field_follows_the_default_style(data):
    set_default_style(Style(reference="#444444"))
    _, (ax,) = plot_panels(data, [Panel([Line("a", color="reference")])])
    assert ax.lines[0].get_color() == "#444444"


def test_window_keeps_only_the_rows_inside_it(data):
    _, (ax,) = plot_panels(data, ["a"], window=("2024-01-01 05:00", "2024-01-01 10:00"))
    x = pd.to_datetime(ax.lines[0].get_xdata())
    assert x.min() == pd.Timestamp("2024-01-01 05:00")
    assert x.max() == pd.Timestamp("2024-01-01 10:00")
    assert len(x) == 11


def test_window_sets_the_time_axis_to_its_bounds(data):
    import matplotlib.dates as mdates
    _, (ax,) = plot_panels(data, ["a"], window=("2023-12-31 22:00", "2024-01-01 10:00"),
                           annotations=[Span("2024-01-01 09:00", "2024-01-03")])
    assert [mdates.num2date(v).replace(tzinfo=None) for v in ax.get_xlim()] == [
        pd.Timestamp("2023-12-31 22:00"), pd.Timestamp("2024-01-01 10:00")]


def test_window_scales_the_y_axis_to_the_rows_inside_it(data):
    d = data.copy()
    d.loc[d.index[-1], "a"] = 1000.0
    _, (ax,) = plot_panels(d, ["a"], window=(None, "2024-01-01 10:00"))
    assert ax.get_ylim()[1] < 100


def test_window_open_side_uses_the_data(data):
    import matplotlib.dates as mdates
    _, (ax,) = plot_panels(data, ["a"], window=("2024-01-01 20:00", None))
    assert mdates.num2date(ax.get_xlim()[1]).replace(tzinfo=None) == data.index[-1]


def test_window_without_rows_raises(data):
    with pytest.raises(ValueError, match="window"):
        plot_panels(data, ["a"], window=("2025-01-01", "2025-01-02"))


def test_window_marks_only_the_gaps_inside_it(data):
    _, (ax,) = plot_panels(data, ["a"], gaps="missing", window=(data.index[10], data.index[40]))
    assert len(crosses(ax)[0].get_xdata()) == 1


def test_window_in_the_time_zone_of_the_index(data):
    d = data.tz_localize("UTC")
    _, (ax,) = plot_panels(d, ["a"], window=("2024-01-01 05:00", "2024-01-01 10:00"))
    assert len(ax.lines[0].get_xdata()) == 11


@pytest.fixture
def duplicated(data):
    """The fixture data with the time of row 20 repeated once, as in an export with a double reading."""
    return pd.concat([data.iloc[:21], data.iloc[20:]])


def test_window_accepts_a_points_mask_computed_from_the_full_data_with_duplicate_times(duplicated):
    mask = duplicated["a"] > 0
    _, (ax,) = plot_panels(duplicated, Panel("a", annotations=[Points(mask, "a")]),
                           window=(duplicated.index[10], None))
    inside = mask[duplicated.index >= duplicated.index[10]]
    assert len(ax.lines[1].get_xdata()) == inside.sum()


def test_window_accepts_a_gaps_series_computed_from_the_full_data_with_duplicate_times(duplicated):
    gaps = duplicated["missing"] == 1
    _, (ax,) = plot_panels(duplicated, ["a"], gaps=gaps, window=(duplicated.index[10], None))
    assert len(crosses(ax)[0].get_xdata()) == 1


def test_window_still_rejects_a_duplicated_mask_with_another_index(duplicated):
    other = (duplicated["a"] > 0).iloc[::-1]
    with pytest.raises(ValueError, match="duplicate times"):
        plot_panels(duplicated, ["a"], gaps=other, window=(duplicated.index[10], None))


def test_note_outside_the_window_names_the_window(data):
    with pytest.raises(KeyError, match="outside the plotted time range"):
        plot_panels(data, Panel("a", annotations=[Note(data.index[0], "x", column="a")]),
                    window=(data.index[10], None))


def test_empty_layout_raises(data):
    with pytest.raises(ValueError, match="no panels"):
        plot_panels(data, [])
