"""tspanels: aligned time series drawn as stacked panels that share one time axis.

The package consists of six modules; their public names are re-exported here, so that
``from tspanels import plot_panels, Panel, Line, Style`` is the usual import.

- ``style``: ``Style``, the colors of a figure, and the project-level default style.
- ``data``: ``to_frame``, the conversion of pandas, dict, and polars input to a pandas
  DataFrame indexed by time.
- ``layout``: ``Line`` and ``Panel``, which define which series are drawn where.
- ``annotations``: ``RefLine``, ``Points``, ``Note``, ``VLine``, ``Span``, ``Band``, and the
  ``Annotation`` protocol that user-defined annotations follow.
- ``plot``: ``plot_panels``, which draws the figure, its building blocks, and
  ``required_columns``, the columns a layout refers to.
- ``theme``: ``rc_params`` and ``use_theme``, which give ordinary matplotlib plots the
  look of ``plot_panels``.
"""

from tspanels.annotations import Annotation, Band, Note, Points, RefLine, Span, VLine
from tspanels.data import to_frame
from tspanels.layout import Line, Panel, as_panels
from tspanels.plot import (
    draw_panel,
    format_time_axis,
    mark_gaps,
    plot_panels,
    required_columns,
    style_axis,
)
from tspanels.style import DEFAULT_STYLE, Style, get_default_style, set_default_style
from tspanels.theme import rc_params, use_theme

__all__ = [
    "DEFAULT_STYLE",
    "Annotation",
    "Band",
    "Line",
    "Note",
    "Panel",
    "Points",
    "RefLine",
    "Span",
    "Style",
    "VLine",
    "as_panels",
    "draw_panel",
    "format_time_axis",
    "get_default_style",
    "mark_gaps",
    "plot_panels",
    "rc_params",
    "required_columns",
    "set_default_style",
    "style_axis",
    "to_frame",
    "use_theme",
]
