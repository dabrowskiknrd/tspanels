"""Annotations: reference levels, marked times, notes, events, and periods drawn over the series.

An annotation is any object with a method ``draw(ax, data, style)`` (the ``Annotation``
protocol), so a new kind of annotation requires no change to ``plot_panels``. The
arguments are the panel's matplotlib Axes, the full DataFrame being plotted (indexed by
time), and the ``Style`` in effect for the figure.

=================================  ====================================================
``RefLine(y, label)``              Horizontal reference level, for example an alarm
                                   threshold; the label is placed outside the right
                                   edge of the panel.
``Points(mask, column, label)``    Markers on ``column`` at the selected times, for
                                   example the readings that exceed a threshold.
``Note(x, text, column=...)``      One marked point with a text label, for example the
                                   maximum of a series.
``VLine(x, label)``                Vertical line for an event at one time, for example
                                   a restart.
``Span(start, end, label)``        Shaded period, for example a maintenance window.
``Band(lower, upper, label)``      Range between two edges, each a column or a fixed
                                   value, for example control limits or a confidence
                                   interval; filled, or drawn as two edge lines.
=================================  ====================================================

A color left at None is taken from the style when the annotation is drawn: ``RefLine``
and ``VLine`` use ``Style.reference``, ``Span`` uses ``Style.shade``, ``Points`` uses
``Style.alert``, ``Note`` uses the first color of ``Style.series``, and ``Band`` uses
``Style.shade`` when filled and ``Style.reference`` for its edge lines. An explicit color
takes precedence over the style; it may also name a field of the style, for example
``color="alert"`` or ``color="series[2]"`` (see ``Style.color``).

Every time given to an annotation (``Note.x``, ``VLine.x``, ``Span.start``, ``Span.end``)
is interpreted in the time zone of the data's index (see ``tspanels.data.as_time``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast, runtime_checkable

import pandas as pd
from matplotlib.axes import Axes

from tspanels.data import as_time, resolve_mask
from tspanels.style import Style

# The matplotlib type stubs declare float for the x positions of plot, axvline, and axvspan;
# Timestamps are accepted at run time through matplotlib's date conversion. The calls that
# pass a Timestamp are therefore marked with "pyright: ignore[reportArgumentType]".


def _time_range(index: pd.DatetimeIndex) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return the first and the last time of ``index``, typed as Timestamps."""
    return cast(pd.Timestamp, index.min()), cast(pd.Timestamp, index.max())


@runtime_checkable
class Annotation(Protocol):
    """The interface of an annotation: any object with this ``draw`` method is accepted.

    An annotation that reads columns of the data may also define a method
    ``columns() -> list[str]`` that returns their names. The method is optional and is
    therefore not part of this Protocol class, so that an object with ``draw`` alone
    still satisfies ``isinstance(obj, Annotation)``. When it is defined,
    ``required_columns`` and ``plot_panels`` use it to report a missing column before
    any drawing starts; without it, only ``mask`` and ``column`` attributes are
    recognized (see ``tspanels.plot.required_columns``).
    """

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Draw the annotation into ``ax``.

        Parameters
        ----------
        ax : matplotlib Axes
            The panel to draw into.
        data : pandas.DataFrame
            The full data being plotted, indexed by time.
        style : Style
            The colors in effect for the figure.
        """


@dataclass
class RefLine:
    """Horizontal line at a fixed value, for example an alarm threshold or a target value.

    Attributes
    ----------
    y : float
        Value at which the line is drawn, in the units of the panel's y axis.
    label : str
        Text placed just outside the right edge of the panel, at the height of the line;
        an empty string draws no text. The text is not a legend entry.
    color : str, optional
        Line color. None uses ``Style.reference``.
    linestyle : str
        Matplotlib line style.
    """

    y: float
    label: str = ""
    color: str | None = None
    linestyle: str = "--"

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Draw the line across the full width of the panel, and its label if one is set.

        The parameters are those of ``Annotation.draw``.
        """
        ax.axhline(self.y, color=style.color(self.color) or style.reference, linewidth=0.8, linestyle=self.linestyle)
        if self.label:
            ax.annotate(self.label, (1, self.y), xycoords=("axes fraction", "data"), xytext=(4, 0),
                        textcoords="offset points", ha="left", va="center", fontsize=9,
                        color=style.ink_muted)


@dataclass
class Points:
    """Markers on one series at selected times, for example alarms or readings above a limit.

    Attributes
    ----------
    mask : pandas.Series of bool, or str
        The times to mark. A boolean Series is aligned to the data's time index, and
        times absent from it are not marked. A string names a column of the data; a
        time is marked where that column is truthy and not missing, which also works
        for polars input.
    column : str
        Column whose values give the vertical position of the markers.
    label : str, optional
        Legend entry for the markers; None adds no entry.
    color : str, optional
        Marker color. None uses ``Style.alert``.
    marker : str
        Matplotlib marker symbol.
    markersize : float
        Marker size in points.
    """

    mask: pd.Series | str
    column: str
    label: str | None = None
    color: str | None = None
    marker: str = "o"
    markersize: float = 4

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Draw one marker at the value of ``column`` at each selected time.

        The parameters are those of ``Annotation.draw``.

        Raises
        ------
        KeyError
            If ``mask`` or ``column`` names a column that the data does not contain.
        """
        mask = resolve_mask(self.mask, data)
        ax.plot(data.index[mask], data.loc[mask, self.column], linestyle="none", marker=self.marker,
                markersize=self.markersize, color=style.color(self.color) or style.alert, label=self.label)


@dataclass
class Note:
    """One marked point with a text label beside it, for example the maximum of a series.

    Attributes
    ----------
    x : timestamp-like
        Time of the point.
    text : str
        Label text. The placeholders ``{x}`` and ``{y}`` are replaced by the time and
        the value of the point, and accept format specifications, for example
        ``"maximum: {y:.1f} at {x:%H:%M, %d %b %Y}"``.
    column : str, optional
        Column from which the value at ``x`` is read. Required when ``y`` is None.
        ``x`` must then occur exactly once in the data's time index.
    y : float, optional
        Value of the point. If given, ``column`` is not used and ``x`` need not be a
        time of the data.
    color : str, optional
        Marker color. None uses the first color of ``Style.series``.
    offset : (float, float), optional
        Position of the text relative to the point, in typographic points. None places
        the text to the right of the point, or to its left when the point lies in the
        last third of the data's time range, so that the text stays inside the panel.
    """

    x: object
    text: str
    column: str | None = None
    y: float | None = None
    color: str | None = None
    offset: tuple[float, float] | None = None

    def __post_init__(self):
        """Check that the value of the point can be determined.

        Raises
        ------
        ValueError
            If both ``column`` and ``y`` are None.
        """
        if self.column is None and self.y is None:
            raise ValueError("Note needs column= or y=: column names the column whose value "
                             "at x is marked, y gives the value itself")

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Draw the marker, outlined in ``Style.background``, and the formatted text.

        The parameters are those of ``Annotation.draw``.

        When ``y`` is None, the value is read from ``column`` at the single row of time
        ``x``. A time that occurs in several rows has several values, so no single point
        is defined; the method raises instead of choosing one of the rows, because any
        choice (the first, the last, a mean) could mark a value that the caller did not
        intend. Duplicate times elsewhere in the data do not affect the Note.

        Raises
        ------
        KeyError
            If ``y`` is None and ``x`` is not a time of the data's index. The message
            states when ``x`` lies outside the plotted time range, for example outside
            the ``window`` of ``plot_panels``.
        ValueError
            If ``y`` is None and ``x`` occurs more than once in the data's index.
        """
        index = cast(pd.DatetimeIndex, data.index)
        x = as_time(self.x, index)
        if self.y is not None:
            y = self.y
        else:
            values = data.loc[data.index == x, self.column]
            if len(values) == 0:
                first, last = _time_range(index)
                if not first <= x <= last:
                    raise KeyError(f"Note time {x} lies outside the plotted time range ({first} to "
                                   f"{last}); give y= explicitly or widen the window")
                raise KeyError(f"Note time {x} is not in the data's time index; give y= explicitly")
            if len(values) > 1:
                raise ValueError(f"Note time {x} occurs {len(values)} times in the data's time index, "
                                 "so its value is not unique; give y= explicitly or remove the "
                                 "duplicate times")
            y = values.iloc[0]
        ax.plot(x, y, marker="o", markersize=6, color=style.color(self.color) or style.series[0],  # pyright: ignore[reportArgumentType]
                markeredgecolor=style.background, markeredgewidth=1.5)
        offset = self.offset
        if offset is None:
            t0, t1 = _time_range(index)
            right_third = t1 > t0 and (x - t0) / (t1 - t0) > 2 / 3
            offset = (-8, -2) if right_third else (8, -2)
        ax.annotate(self.text.format(x=x, y=y), (x, y), xytext=offset, textcoords="offset points",
                    ha="right" if offset[0] < 0 else "left", va="center", fontsize=9, color=style.ink)


@dataclass
class VLine:
    """Vertical line that marks an event at one time, for example a restart.

    Attributes
    ----------
    x : timestamp-like
        Time of the event.
    label : str
        Text placed at the top of the panel, to the right of the line; an empty string
        draws no text. The text is not a legend entry.
    color : str, optional
        Line color. None uses ``Style.reference``.
    linestyle : str
        Matplotlib line style.
    """

    x: object
    label: str = ""
    color: str | None = None
    linestyle: str = ":"

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Draw the line over the full height of the panel, and its label if one is set.

        The parameters are those of ``Annotation.draw``.
        """
        x = as_time(self.x, data.index)
        ax.axvline(x, color=style.color(self.color) or style.reference, linewidth=0.8,  # pyright: ignore[reportArgumentType]
                   linestyle=self.linestyle)
        if self.label:
            ax.annotate(self.label, (x, 1), xycoords=("data", "axes fraction"), xytext=(3, -3),
                        textcoords="offset points", ha="left", va="top", fontsize=8,
                        color=style.ink_muted)


@dataclass
class Span:
    """Shaded time period, for example a maintenance window or a known outage.

    Attributes
    ----------
    start, end : timestamp-like
        Start and end of the period.
    label : str, optional
        Legend entry for the shaded area; None adds no entry.
    color : str, optional
        Fill color. None uses ``Style.shade``.
    alpha : float
        Fill opacity, from 0 (transparent) to 1 (opaque).
    """

    start: object
    end: object
    label: str | None = None
    color: str | None = None
    alpha: float = 0.15

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Shade the period from ``start`` to ``end`` over the full height of the panel.

        The parameters are those of ``Annotation.draw``.
        """
        ax.axvspan(as_time(self.start, data.index), as_time(self.end, data.index),  # pyright: ignore[reportArgumentType]
                   color=style.color(self.color) or style.shade, alpha=self.alpha, linewidth=0, label=self.label)


@dataclass
class Band:
    """Range between a lower and an upper edge, for example control limits or a confidence interval.

    Each edge is either a column of the data, which gives one value per time, or a
    fixed value, which gives a horizontal edge. A fixed band between two values is
    therefore also possible, for example a normal operating range.

    The band is drawn filled by default, because a filled area shows the range at a
    glance. ``fill=False`` draws the two edges as lines instead, which keeps a series
    inside the range fully visible; this is the usual form of control limits. With
    ``fill=False`` the legend lists the band once, under the lower edge.

    Attributes
    ----------
    lower, upper : str or float
        The edges: a column name, or a value in the units of the panel's y axis. A
        missing value in an edge column interrupts the band at that time.
    label : str, optional
        Legend entry for the band; None adds no entry.
    color : str, optional
        Fill or edge color. None uses ``Style.shade`` for a filled band and
        ``Style.reference`` for edge lines, the same colors as ``Span`` and ``RefLine``.
    alpha : float
        Fill opacity, from 0 (transparent) to 1 (opaque); used only when ``fill`` is True.
    fill : bool
        True fills the range; False draws the two edges as lines.
    linestyle : str
        Matplotlib line style of the edges; used only when ``fill`` is False.
    """

    lower: str | float
    upper: str | float
    label: str | None = None
    color: str | None = None
    alpha: float = 0.15
    fill: bool = True
    linestyle: str = "--"

    def columns(self) -> list[str]:
        """Return the edges that are column names, so that missing columns are reported before drawing."""
        return [edge for edge in (self.lower, self.upper) if isinstance(edge, str)]

    def draw(self, ax: Axes, data: pd.DataFrame, style: Style) -> None:
        """Draw the band over the full time range of the data.

        The parameters are those of ``Annotation.draw``.

        Raises
        ------
        KeyError
            If an edge names a column that the data does not contain.
        """
        lower, upper = (self._values(edge, data) for edge in (self.lower, self.upper))
        if self.fill:
            ax.fill_between(data.index, lower, upper, color=style.color(self.color) or style.shade,
                            alpha=self.alpha, linewidth=0, label=self.label)
            return
        color = style.color(self.color) or style.reference
        for values, label in ((lower, self.label), (upper, "_nolegend_")):
            ax.plot(data.index, values, color=color, linewidth=0.8, linestyle=self.linestyle,
                    label=label)

    @staticmethod
    def _values(edge: str | float, data: pd.DataFrame):
        """Return one value per row of ``data`` for an edge given as a column name or a value."""
        if isinstance(edge, str):
            if edge not in data.columns:
                raise KeyError(f"column {edge!r} not in the data")
            return data[edge].to_numpy(dtype=float, na_value=float("nan"))
        return [float(edge)] * len(data)
