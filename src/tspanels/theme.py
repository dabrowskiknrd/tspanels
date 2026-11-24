"""The look of ``plot_panels``, applied to ordinary matplotlib plots through rcParams.

``plot_panels`` styles its own figures explicitly, axis by axis. A notebook usually also
contains other plots, such as scatter plots, histograms, or bar charts, drawn directly
with matplotlib. ``rc_params`` translates a ``Style`` into matplotlib settings (rcParams)
that give those plots the same look: titles on the left in ``Style.ink``, muted tick and
axis labels, lines in the ``Style.series`` colors, a horizontal grid, no top or right
axis line, and legends without a frame.

Design decisions
----------------
- The settings are returned as a dict by ``rc_params``, and applied globally only by
  the explicit call ``use_theme``. The dict can also be applied to a limited block of
  code with ``matplotlib.rc_context(rc_params())``, which restores the previous
  settings at the end of the block. Importing tspanels therefore never changes
  matplotlib's settings.
- ``plot_panels`` does not depend on these settings: it applies its colors explicitly,
  so its figures are identical with and without ``use_theme``.
- Only the properties that ``plot_panels`` itself styles are set. Line widths, marker
  sizes, figure size, and fonts keep the values in effect, so that the theme combines
  with other matplotlib styles.
"""

from __future__ import annotations

import matplotlib as mpl
from matplotlib.rcsetup import cycler

from tspanels.style import Style, resolve_style


def rc_params(style: Style | None = None) -> dict:
    """Return the matplotlib settings that give ordinary plots the look of ``plot_panels``.

    Parameters
    ----------
    style : Style, optional
        The colors to use. None uses the project-level default style (see
        ``set_default_style``), read at the time of this call.

    Returns
    -------
    dict
        rcParams names and values, for ``matplotlib.rcParams.update`` or
        ``matplotlib.rc_context``.
    """
    style = resolve_style(style)
    return {
        "figure.facecolor": style.background,
        "axes.facecolor": style.background,
        "axes.edgecolor": style.axis,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": style.grid,
        "grid.linewidth": 0.8,
        "axes.titlelocation": "left",
        "axes.titlesize": 10,
        "axes.titlecolor": style.ink,
        "figure.titlesize": 12,
        "text.color": style.ink,
        "axes.labelcolor": style.ink_muted,
        "axes.labelsize": 9,
        "xtick.color": style.ink_muted,
        "ytick.color": style.ink_muted,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.prop_cycle": cycler(color=list(style.series)),
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": style.ink_muted,
    }


def use_theme(style: Style | None = None) -> None:
    """Apply ``rc_params(style)`` to every later matplotlib plot of the Python process.

    The settings last until they are changed again; ``matplotlib.rcdefaults()`` restores
    matplotlib's defaults. To apply them to a limited block of code instead, use
    ``with matplotlib.rc_context(tspanels.rc_params()):``.

    Parameters
    ----------
    style : Style, optional
        The colors to use. None uses the project-level default style. A later call of
        ``set_default_style`` does not update settings applied earlier; ``use_theme``
        is called again for that.

    Raises
    ------
    TypeError
        If ``style`` is neither None nor a ``Style``.
    """
    if style is not None and not isinstance(style, Style):
        raise TypeError(f"style must be a Style or None, not {type(style).__name__}")
    mpl.rcParams.update(rc_params(style))
