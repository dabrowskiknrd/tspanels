"""Colors of the figures, held in one ``Style`` object.

Every color that ``plot_panels`` and the annotations use is a field of ``Style``.
The style of a figure is chosen in one of two ways:

- per call, with ``plot_panels(..., style=Style(...))``;
- per project, with ``set_default_style(Style(...))``, which every later call without a
  ``style`` argument uses.

A color given explicitly to a ``Line`` or an annotation always takes precedence over
the style. Such a color may also name a field of the style, for example
``color="alert"`` or ``color="series[2]"`` (see ``Style.color``); it is then taken from
the style of the figure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Style:
    """The set of colors used to draw a figure.

    The default colors are blue, orange, and green lines on a white background, a light
    gray grid, gray reference lines, and red alerts. A modified style is created by
    passing only the fields to change, for example ``Style(alert="#c00000")``; the
    instance cannot be modified after creation.

    Attributes
    ----------
    series : tuple of str
        Line colors, assigned in this order to the lines of a panel that have no
        explicit color. A panel with more such lines than colors draws the remaining
        lines in the last color.
    ink : str
        Color of the figure title, the panel titles, and the text of ``Note``.
    ink_muted : str
        Color of tick labels, legend text, the labels of ``RefLine`` and ``VLine``, and
        the notice shown in a panel without data.
    axis : str
        Color of the left and bottom axis lines (spines).
    grid : str
        Color of the horizontal grid lines.
    reference : str
        Default color of ``RefLine`` and ``VLine``.
    shade : str
        Default fill color of ``Span``; drawn with low opacity.
    alert : str
        Color of the gap markers and default color of ``Points``.
    background : str
        Face color of the figure and of every panel, and edge color of the ``Note``
        marker, which separates the marker from the line beneath it.
    """

    series: tuple[str, ...] = ("#2a78d6", "#eb6834", "#1baf7a", "#8a8984")
    ink: str = "#0b0b0b"
    ink_muted: str = "#52514e"
    axis: str = "#b5b4ae"
    grid: str = "#e5e4e0"
    reference: str = "#8a8984"
    shade: str = "#8a8984"
    alert: str = "#d03b3b"
    background: str = "white"

    def color(self, value):
        """Return the color that ``value`` names in this style, or ``value`` unchanged.

        A string equal to the name of a one-color field, such as ``"alert"`` or
        ``"reference"``, returns that field's color; ``"series[i]"`` returns the color
        at position ``i`` of ``series``, or the last color when ``i`` is beyond the end,
        which is the rule for automatic line colors. Every other value, such as
        ``"#c00000"``, ``"red"``, an RGB tuple, or None, is returned unchanged. The
        field names are not matplotlib color names, so no matplotlib color is shadowed.

        A ``Line`` or an annotation whose ``color`` names a field takes its color from
        the style of the figure when it is drawn, so it follows ``plot_panels(style=...)``
        and ``set_default_style``.
        """
        if not isinstance(value, str):
            return value
        if value in _COLOR_FIELDS:
            return getattr(self, value)
        match = _SERIES_ITEM.fullmatch(value)
        if match:
            return self.series[min(int(match.group(1)), len(self.series) - 1)]
        return value


_COLOR_FIELDS = frozenset(f.name for f in fields(Style) if f.name != "series")
_SERIES_ITEM = re.compile(r"series\[(\d+)\]")

DEFAULT_STYLE = Style()
"""The style with all default colors."""

_default: Style = DEFAULT_STYLE


def set_default_style(style: Style) -> None:
    """Set the style used by every later drawing call that receives no ``style`` argument.

    The setting lasts until the next call of this function or the end of the Python
    process; ``set_default_style(DEFAULT_STYLE)`` restores the default colors.

    Parameters
    ----------
    style : Style
        The new project-level default style.

    Raises
    ------
    TypeError
        If ``style`` is not a ``Style``.
    """
    global _default
    if not isinstance(style, Style):
        raise TypeError(f"style must be a Style, not {type(style).__name__}")
    _default = style


def get_default_style() -> Style:
    """Return the project-level default style, as last set by ``set_default_style``."""
    return _default


def resolve_style(style: Style | None) -> Style:
    """Return ``style``, or the project-level default style when ``style`` is None."""
    return get_default_style() if style is None else style
