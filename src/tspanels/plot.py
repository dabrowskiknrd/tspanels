"""Drawing: ``plot_panels`` and the functions it uses to draw and style each panel.

``plot_panels`` is the entry point. It converts the data (``tspanels.data.to_frame``)
and the layout (``tspanels.layout.as_panels``), checks that every referenced column
exists, creates one subplot per panel on a shared time axis, and calls ``draw_panel``
for each. ``draw_panel`` draws the lines, the annotations, the gap markers, the title,
and the legend of one panel, and applies ``style_axis``. ``format_time_axis`` sets the
date ticks of the bottom panel. ``required_columns`` lists the columns that a layout and
its annotations refer to; ``plot_panels`` checks them before drawing. ``style_axis``,
``format_time_axis``, and ``mark_gaps`` can also be applied to Axes created outside
``plot_panels``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from typing import cast

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from tspanels.annotations import Annotation, Points
from tspanels.data import as_time, resolve_mask, to_frame
from tspanels.layout import Panel, as_panels
from tspanels.style import Style, resolve_style


def style_axis(ax: Axes, style: Style | None = None) -> None:
    """Apply the axis style to ``ax``: light horizontal grid, no top or right axis line.

    The grid is drawn in ``style.grid``, the left and bottom axis lines in
    ``style.axis``, the tick labels in ``style.ink_muted`` at font size 9, and the panel
    face in ``style.background``.

    Every property that ``tspanels.rc_params`` also sets is set here explicitly, so
    that a figure of ``plot_panels`` is identical with and without ``use_theme``. Three
    of them are set to matplotlib's default values, which are the values these figures
    had before the theme existed: the x grid is switched off, the grid is drawn above
    shaded areas and below lines (``set_axisbelow("line")``), and the offset labels of
    the axes (for example the year under a date axis, or ``1e6`` beside a y axis) keep
    the size ``"medium"``, independent of the tick label size of the theme.

    Parameters
    ----------
    ax : matplotlib Axes
        The Axes to style; it is modified in place.
    style : Style, optional
        The colors to use. None uses the project-level default style.
    """
    style = resolve_style(style)
    ax.set_facecolor(style.background)
    ax.grid(False, axis="x")
    ax.grid(axis="y", color=style.grid, linewidth=0.8)
    ax.set_axisbelow("line")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(style.axis)
    ax.tick_params(colors=style.ink_muted, labelsize=9)
    for axis in (ax.xaxis, ax.yaxis):
        axis.get_offset_text().set_fontsize("medium")


def format_time_axis(ax: Axes) -> None:
    """Set date ticks on the x axis of ``ax`` that adapt to the length of the time range.

    The ticks are chosen automatically and labeled concisely (for example only the hour
    within a day, and the date where the day changes), which suits time ranges from
    minutes to years.

    Parameters
    ----------
    ax : matplotlib Axes
        The Axes whose x axis holds times; it is modified in place. In a figure of
        stacked panels with a shared x axis, this is the bottom panel.
    """
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


def mark_gaps(ax: Axes, gap_times, label: str | None = None, style: Style | None = None) -> None:
    """Draw a cross along the bottom edge of the panel at each gap time.

    The crosses are placed at 3 % of the panel height regardless of the y axis range,
    so they do not depend on the data values.

    Parameters
    ----------
    ax : matplotlib Axes
        The panel to draw into.
    gap_times : sequence of timestamps
        The times to mark.
    label : str, optional
        Legend entry for the crosses; None adds no entry.
    style : Style, optional
        The colors to use; the crosses are drawn in ``style.alert``. None uses the
        project-level default style.
    """
    style = resolve_style(style)
    bottom_edge = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
    ax.plot(gap_times, [0.03] * len(gap_times), transform=bottom_edge, linestyle="none",
            marker="x", markersize=4, markeredgewidth=1, color=style.alert, label=label)


def _draw_without_legend(ax: Axes, annotations: Sequence[Annotation], data: pd.DataFrame,
                         style: Style) -> None:
    """Draw ``annotations`` into ``ax`` and remove every legend entry they created.

    The artists themselves, including text drawn on the axes, remain visible; only their
    legend labels are replaced by ``"_nolegend_"``, which matplotlib's legend skips. Both
    the artists and the containers that ``bar``, ``errorbar``, and ``stem`` create are
    covered, because the legend reads the label of such a container, not of its parts.
    """
    before = set(ax.get_children()) | set(ax.containers)
    for annotation in annotations:
        annotation.draw(ax, data, style)
    for item in [*ax.get_children(), *ax.containers]:
        if item not in before:
            item.set_label("_nolegend_")


def draw_panel(ax: Axes, data: pd.DataFrame, panel: Panel, style: Style | None = None,
               shared_annotations: Sequence[Annotation] = (), gap_times=None,
               gap_label: str | None = None, shared_in_legend: bool = True) -> None:
    """Draw one Panel into an existing matplotlib Axes.

    The drawing order is: the lines, the figure-wide annotations, the panel's own
    annotations, the gap markers, the notice for a panel whose columns hold no values,
    the title, the legend, and the axis style. Lines without an explicit color receive
    the colors of ``style.series`` in order, skipping colors that other lines of the
    panel use explicitly; when the colors run out, the last one is repeated.

    Parameters
    ----------
    ax : matplotlib Axes
        The Axes to draw into.
    data : pandas.DataFrame
        The data, indexed by time, containing every column the panel refers to.
    panel : Panel
        The lines and annotations to draw.
    style : Style, optional
        The colors to use. None uses the project-level default style.
    shared_annotations : sequence of Annotation
        Figure-wide annotations, drawn before the panel's own annotations.
    gap_times : sequence of timestamps, optional
        Times to mark with ``mark_gaps``; None or an empty sequence draws no markers.
        When markers are drawn, a vertical margin of 12 % keeps the lines above them.
    gap_label : str, optional
        Legend entry of the gap markers in this panel; None adds no entry.
    shared_in_legend : bool
        Whether the figure-wide annotations contribute legend entries in this panel.
        ``plot_panels`` sets it to False for every panel after the first, so that each
        entry is listed once.

    Raises
    ------
    KeyError
        If a line or an annotation refers to a column that ``data`` lacks, or a ``Note``
        without ``y`` refers to a time absent from the index.
    """
    style = resolve_style(style)
    explicit = {style.color(line.color) for line in panel.lines}
    colors = iter(c for c in style.series if c not in explicit)
    for line in panel.lines:
        color = style.color(line.color) or next(colors, style.series[-1])
        ax.plot(data.index, data[line.column], color=color, linewidth=line.linewidth,
                linestyle=line.linestyle, label=line.label)
    if shared_in_legend:
        for annotation in shared_annotations:
            annotation.draw(ax, data, style)
    else:
        _draw_without_legend(ax, shared_annotations, data, style)
    for annotation in panel.annotations:
        annotation.draw(ax, data, style)
    if gap_times is not None and len(gap_times):
        ax.margins(y=0.12)  # vertical margin that keeps the lines above the gap markers
        mark_gaps(ax, gap_times, gap_label, style)
    if data[panel.columns()].isna().to_numpy().all():
        ax.text(0.5, 0.5, "no data in this period", transform=ax.transAxes, ha="center",
                va="center", fontsize=9, color=style.ink_muted)

    title = panel.title
    if title is None and len(panel.lines) == 1:
        title = panel.lines[0].label or panel.lines[0].column
    if title:
        ax.set_title(title, loc="left", fontsize=10, color=style.ink)

    handles, _ = ax.get_legend_handles_labels()
    if len(handles) >= 2:
        # placed above the panel and aligned right, so that it never covers the data
        ax.legend(loc="lower right", bbox_to_anchor=(1, 1), ncols=min(len(handles), 2),
                  frameon=False, fontsize=9, labelcolor=style.ink_muted)
    elif handles:
        ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=style.ink_muted)
    style_axis(ax, style)


def _annotation_columns(annotation) -> list[str]:
    """Return the column names that one annotation reads, in a fixed order.

    An annotation that defines a ``columns()`` method (as ``Band`` does) declares its
    columns itself, and that list is used as is. Otherwise two attributes are read: a
    ``mask`` given as a column name (as in ``Points``), then a non-empty ``column``
    attribute (as in ``Points`` and ``Note``). The attribute rule exists so that
    user-defined annotations written before the ``columns()`` method was introduced are
    still checked; a new annotation that reads columns should define ``columns()``.
    """
    declared = getattr(annotation, "columns", None)
    if callable(declared):
        return list(cast(Iterable[str], declared()))
    found = []
    if isinstance(getattr(annotation, "mask", None), str):
        found.append(annotation.mask)
    if getattr(annotation, "column", None):
        found.append(annotation.column)
    return found


def _in_window(annotation, full: pd.DataFrame, rows: slice):
    """Return ``annotation`` with a boolean Series mask aligned to ``full`` and cut to ``rows``.

    A selection is usually computed from the data before ``plot_panels`` is called, so its
    index is the index of all rows, not of the rows inside the window. Aligned to all rows
    first and then cut with the same slice as the data, it has exactly the index of the
    plotted rows, which ``resolve_mask`` accepts also when times repeat. Only ``Points``
    is handled; every other annotation is returned unchanged.
    """
    if isinstance(annotation, Points) and isinstance(annotation.mask, pd.Series):
        return replace(annotation, mask=resolve_mask(annotation.mask, full).loc[rows])
    return annotation


def required_columns(panels, annotations: Sequence[Annotation] = (), gaps=None) -> list[str]:
    """Return every column name that a layout, its annotations, and ``gaps`` refer to.

    This is the check that ``plot_panels`` applies before drawing, made public so that a
    caller can select exactly the columns a figure needs, for example from a wide table,
    before calling ``plot_panels``. It is computed from the layout alone, without data.

    The order is fixed so that the result can be used directly as a column selection:
    for each panel from top to bottom, the line columns and then the columns of the
    panel's annotations; then the columns of the figure-wide ``annotations``; then
    ``gaps`` when it is a column name. A name that occurs more than once is listed at
    its first occurrence only.

    Parameters
    ----------
    panels : dict, sequence, str, Line, or Panel
        The layout, in any form accepted by ``as_panels``.
    annotations : sequence of Annotation
        Figure-wide annotations, as passed to ``plot_panels``.
    gaps : str, pandas.Series of bool, or None
        The ``gaps`` argument of ``plot_panels``; only a string adds a column.

    Returns
    -------
    list of str
        The column names, without duplicates.

    Notes
    -----
    The columns of an annotation are taken from its ``columns()`` method when it has
    one, and otherwise from its ``mask`` and ``column`` attributes (see the
    ``Annotation`` protocol). A user-defined annotation that reads other columns
    without declaring them is not covered; a missing column then raises ``KeyError``
    while drawing instead of before.
    """
    names = []
    for panel in as_panels(panels):
        names += panel.columns()
        for annotation in panel.annotations:
            names += _annotation_columns(annotation)
    for annotation in annotations:
        names += _annotation_columns(annotation)
    if isinstance(gaps, str):
        names.append(gaps)
    return list(dict.fromkeys(names))


def plot_panels(
    data,
    panels,
    *,
    time: str | None = None,
    window: tuple | None = None,
    title: str | None = None,
    annotations: Sequence[Annotation] = (),
    gaps=None,
    gap_label: str | None = "gap",
    require_gaps: bool = True,
    style: Style | None = None,
    width: float = 14,
    panel_height: float = 2.2,
) -> tuple[Figure, list[Axes]]:
    """Plot aligned time series as vertically stacked panels that share one time axis.

    Each panel is one subplot; the panels are drawn from top to bottom in the order of
    ``panels`` and share the x axis, whose date ticks are shown under the bottom panel.

    Parameters
    ----------
    data : pandas.DataFrame, dict of pandas.Series, or polars.DataFrame
        The time series, in any form accepted by ``tspanels.to_frame``: a DataFrame
        indexed by time, a DataFrame with the time column named by ``time``, a
        ``{name: Series}`` dict (joined on time; missing times become NaN), or a polars
        DataFrame together with ``time``.
    window : (start, end), optional
        The period to plot, both bounds included; None for a bound leaves that side at
        the first or last time of the data. Only the rows inside the window are drawn,
        so the y axes are scaled to them and the gap markers cover them only, and the
        time axis spans exactly the window, also when an annotation reaches beyond it.
        The times are interpreted in the time zone of the data's index. A boolean
        Series given as ``gaps`` or as the mask of a ``Points`` annotation is aligned to
        all rows of the data before the window is applied, so that a selection computed
        from the data before the call is accepted also when the data repeats a time.
        None (the default) plots all rows.
    panels : dict, sequence, str, Line, or Panel
        The layout, from top to bottom: Panel objects, Line objects, column names,
        ``(column, title)`` pairs, a ``{column: title}`` dict, or a single column name,
        Line, or Panel (see ``as_panels``). A panel with several lines is written as
        ``Panel([...])``. The data's columns are passed to ``as_panels``, so a pair
        whose title is the name of another column is rejected as ambiguous.
    time : str, optional
        Name of the time column; required for polars input.
    title : str, optional
        Figure title, aligned left, in ``style.ink``. Line breaks (``"\\n"``) produce
        several lines.
    annotations : sequence of Annotation
        Figure-wide annotations, drawn in every panel, typically ``VLine`` and ``Span``.
        Their legend entries appear in the first panel only; text they draw on the
        axes, such as a ``VLine`` label, appears in every panel. This holds for every
        annotation type, including user-defined ones.
    gaps : str or pandas.Series of bool, optional
        Gap times to mark with a cross along the bottom edge of every panel. A string
        names a column whose truthy, non-missing values mark gaps; a boolean Series
        marks the times where it is True. None (the default) draws no gap markers.
    gap_label : str, optional
        Legend entry of the gap markers, shown in the first panel only. None adds no
        entry.
    require_gaps : bool
        Whether a ``gaps`` column name that the data lacks raises ``KeyError`` (True,
        the default) or draws no gap markers (False). False suits a project in which
        some tables have a gap column and others do not: the project fixes its
        defaults once, for example with
        ``functools.partial(plot_panels, gaps="gap", require_gaps=False)``, and every
        call can still override them. This argument is provided instead of a
        project-level default setting, so that the defaults of a call are visible
        where the call is defined. It has no effect when ``gaps`` is a Series or None.
    style : Style, optional
        The colors of the figure. None uses the project-level default style (see
        ``set_default_style``).
    width : float
        Figure width in inches.
    panel_height : float
        Height in inches of a panel with ``height=1``; the figure height is
        ``panel_height`` times the sum of the panel heights.

    Returns
    -------
    fig : matplotlib Figure
    axes : list of matplotlib Axes
        One Axes per panel, from top to bottom, for further additions.

    Raises
    ------
    TypeError
        If ``data`` is of an unsupported type or is not indexed by time, if ``gaps``
        is neither a column name nor a boolean pandas Series, or if a layout item has
        none of the accepted forms.
    ValueError
        If ``data`` has no rows, or no rows inside ``window``; if the layout has no
        panels; if ``data`` is a polars DataFrame and ``time`` is None,
        or a dict and ``time`` is given; if the title of a ``(column, title)`` pair is
        the name of another column; if a boolean Series (``gaps`` or a ``Points``
        mask) has duplicate times and is not indexed like the data; or if a ``Note``
        without ``y`` refers to a time that occurs more than once.
    KeyError
        If a panel, an annotation, or ``gaps`` refers to a column that ``data`` lacks
        (for ``gaps`` only when ``require_gaps`` is True); the referenced columns are
        those returned by ``required_columns``;
        if ``time`` names a column that ``data`` lacks; or if a ``Note`` without ``y``
        refers to a time absent from the index.
    """
    style = resolve_style(style)
    data = to_frame(data, time)
    if len(data.index) == 0:
        raise ValueError("data has no rows")
    full = data  # all rows; boolean Series are aligned to these before the window is applied
    rows = slice(None)
    xlim = None
    if window is not None:
        start, end = (None if t is None else as_time(t, data.index) for t in window)
        rows = slice(start, end)
        data = data.loc[rows]
        if len(data.index) == 0:
            raise ValueError(f"data has no rows in the window {window}")
        xlim = (data.index[0] if start is None else start, data.index[-1] if end is None else end)
    panels = as_panels(panels, columns=data.columns)
    if not panels:
        raise ValueError("the layout has no panels; give at least one column name, Line, or Panel")
    if window is not None:
        annotations = [_in_window(a, full, rows) for a in annotations]
        panels = [replace(p, annotations=[_in_window(a, full, rows) for a in p.annotations])
                  for p in panels]
    if isinstance(gaps, str) and not require_gaps and gaps not in data.columns:
        gaps = None  # an absent gap column is accepted and draws no markers
    missing = sorted(set(required_columns(panels, annotations, gaps)) - set(data.columns))
    if missing:
        raise KeyError(f"columns not in the data: {missing}")
    gap_times = None if gaps is None else data.index[resolve_mask(gaps, full).loc[rows].to_numpy()]

    heights = [p.height for p in panels]
    fig, axes = plt.subplots(len(panels), 1, sharex=True, squeeze=False,
                             figsize=(width, panel_height * sum(heights)),
                             height_ratios=heights, layout="constrained",
                             facecolor=style.background)
    axes = list(axes[:, 0])
    try:
        for i, (ax, panel) in enumerate(zip(axes, panels)):
            draw_panel(ax, data, panel, style, annotations, gap_times,
                       gap_label if i == 0 else None, shared_in_legend=(i == 0))
        format_time_axis(axes[-1])
        if xlim is not None:
            axes[-1].set_xlim(*xlim)  # the axes share x, so this sets every panel
        if title:
            fig.suptitle(title, x=0.01, ha="left", fontsize=12, color=style.ink)
    except BaseException:
        plt.close(fig)  # a half-drawn figure would otherwise remain open and be displayed
        raise
    return fig, axes
