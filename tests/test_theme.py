import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

from tspanels import Style, rc_params, set_default_style, use_theme


def same(a, b):
    return mcolors.to_hex(a) == mcolors.to_hex(b)


def test_rc_params_take_colors_from_the_style():
    s = Style(ink="#101010", ink_muted="#202020", axis="#303030", grid="#404040",
              series=("#aa0000", "#00aa00"), background="#fafafa")
    rc = rc_params(s)
    assert rc["axes.titlecolor"] == "#101010" and rc["text.color"] == "#101010"
    assert rc["axes.labelcolor"] == rc["xtick.color"] == rc["legend.labelcolor"] == "#202020"
    assert rc["axes.edgecolor"] == "#303030" and rc["grid.color"] == "#404040"
    assert rc["axes.facecolor"] == rc["figure.facecolor"] == "#fafafa"
    assert rc["axes.prop_cycle"].by_key()["color"] == ["#aa0000", "#00aa00"]
    assert rc["axes.titlelocation"] == "left" and rc["axes.grid.axis"] == "y"
    assert rc["axes.spines.top"] is False and rc["legend.frameon"] is False


def test_rc_params_are_valid_matplotlib_settings():
    with mpl.rc_context(rc_params()):
        pass  # matplotlib validates every key and value on entry


def test_rc_params_without_style_use_the_default_style():
    set_default_style(Style(ink="#123456"))
    assert rc_params()["axes.titlecolor"] == "#123456"


def test_use_theme_styles_plain_matplotlib_plots():
    with mpl.rc_context():
        use_theme(Style(series=("#aa0000",), grid="#404040"))
        _, ax = plt.subplots()
        (line,) = ax.plot([0, 1], [0, 1])
        ax.set_title("t")
        assert same(line.get_color(), "#aa0000")
        assert not ax.spines["top"].get_visible()
        assert ax.get_title(loc="center") == "" and ax.get_title(loc="left") == "t"
    assert mpl.rcParams["axes.titlelocation"] == "center"  # rc_context restored the defaults


def test_use_theme_rejects_other_types():
    with pytest.raises(TypeError, match="Style"):
        use_theme("dark")


def test_plot_panels_figures_are_identical_with_and_without_the_theme():
    import numpy as np
    import pandas as pd

    from tspanels import Band, Note, Panel, Points, RefLine, Span, VLine, plot_panels

    t = pd.date_range("2024-01-01", periods=96, freq="h")
    d = pd.DataFrame({"a": np.sin(np.arange(96) / 8), "b": np.cos(np.arange(96) / 8), "gap": 0}, index=t)
    d["c"] = 1e7 + 1e5 * d["a"]  # large values, so that the y axis shows an offset label
    d.iloc[40:44, d.columns.get_loc("gap")] = 1

    def render():
        fig, _ = plot_panels(
            d,
            [Panel(["a", "b"], title="ab", annotations=[RefLine(0.5, "ref"), Band(-0.5, 0.5, "band"),
                                                         Points(d["a"] > 0.9, "a", "high"),
                                                         Note(t[10], "{y:.1f}", column="a")]),
             Panel("b", annotations=[Band(-0.2, "b", fill=False)]), "c"],
            title="title", annotations=[Span(t[20], t[30], "span"), VLine(t[50], "event")], gaps="gap")
        fig.canvas.draw()
        pixels = np.asarray(fig.canvas.buffer_rgba()).copy()
        plt.close(fig)
        return pixels

    plain = render()
    with mpl.rc_context():
        use_theme()
        themed = render()
    assert plain.shape == themed.shape
    assert np.array_equal(plain, themed)
