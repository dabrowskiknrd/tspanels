"""Conversion of the accepted input data to one pandas DataFrame indexed by time.

``to_frame`` turns every accepted input (a pandas DataFrame, a ``{name: Series}`` dict,
or a polars DataFrame) into a pandas DataFrame with a sorted DatetimeIndex, which is the
form all drawing code works on. ``resolve_mask`` and ``as_time`` translate the arguments
of annotations and gap markers (a selection of times, a single time) into that form.

Polars is never imported here: a polars DataFrame is recognized by the module name of
its type, so the package works without polars installed.

Duplicate times are accepted: ``to_frame`` neither removes nor rejects them, because
lines, shaded periods, and markers are drawn correctly over repeated times, and recorded
data often contains a few double readings. An error is raised only where a duplicate
time makes the result undefined: a boolean Series with duplicate times that is not
indexed like the data (``resolve_mask``), and a ``Note`` that reads its value at a
duplicated time (``tspanels.annotations.Note``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import pandas as pd


def _is_polars_frame(data) -> bool:
    """Return True if ``data`` is a polars DataFrame, without importing polars."""
    return type(data).__module__.split(".")[0] == "polars" and hasattr(data, "to_pandas")


def to_frame(data, time: str | None = None) -> pd.DataFrame:
    """Convert the input data to a pandas DataFrame indexed and sorted by time.

    The input is never modified; a new DataFrame is returned.

    Parameters
    ----------
    data : pandas.DataFrame, dict of pandas.Series, or polars.DataFrame
        The time series. A pandas DataFrame is indexed by time, or contains the time
        column named by ``time``. A ``{name: Series}`` dict is joined on the time index
        of its Series (outer join): a time missing from one Series becomes NaN in that
        column. A polars DataFrame has no index, so ``time`` must name its time column.
    time : str, optional
        Name of the column that holds the timestamps. The column becomes the index and
        is removed from the columns. None uses the existing index of a pandas input.
        Not accepted with a dict, whose Series carry their times in their index; it is
        rejected rather than ignored, so that the error names the actual problem.

    Returns
    -------
    pandas.DataFrame
        The data with a DatetimeIndex sorted in increasing order. A time zone of the
        input is kept. Duplicate times are kept (see the module docstring).

    Raises
    ------
    TypeError
        If ``data`` is of another type, or if the resulting index is not a
        DatetimeIndex: for example when a DataFrame indexed by row numbers is passed
        without ``time``, when the column named by ``time`` holds strings, or when the
        Series of a dict are not indexed by time. The message names the remedy that
        applies to the input form.
    ValueError
        If ``data`` is a polars DataFrame and ``time`` is None, or a dict and ``time``
        is given.
    KeyError
        If ``time`` names a column that ``data`` does not contain.
    """
    if _is_polars_frame(data):
        if time is None:
            raise ValueError("a polars DataFrame has no index; name its time column with time=")
        if time not in data.columns:
            raise KeyError(f"time column {time!r} not in the data")
        frame = data.to_pandas().set_index(time)
    elif isinstance(data, pd.DataFrame):
        if time is None:
            frame = data
        elif time in data.columns:
            frame = data.set_index(time)
        else:
            raise KeyError(f"time column {time!r} not in the data")
    elif isinstance(data, Mapping):
        if time is not None:
            raise ValueError("time= is not used with a {name: Series} dict: the times are the "
                             "index of each Series")
        frame = pd.concat(data, axis=1)
        if not isinstance(frame.index, pd.DatetimeIndex):
            raise TypeError(
                "the Series of a {name: Series} dict must be indexed by time (a DatetimeIndex), "
                f"not {type(frame.index).__name__}; set the index of each Series to its times"
            )
    else:
        raise TypeError(
            "data must be a pandas DataFrame, a {name: Series} dict, or a polars DataFrame, "
            f"not {type(data).__name__}"
        )
    if not isinstance(frame.index, pd.DatetimeIndex):
        if time is not None:
            raise TypeError(
                f"column {time!r} does not hold datetimes (dtype {frame.index.dtype}); "
                "convert it with pd.to_datetime before plotting"
            )
        raise TypeError(
            f"the data must be indexed by time (a DatetimeIndex), not {type(frame.index).__name__}; "
            "name the time column with time="
        )
    return frame.sort_index()


def resolve_mask(mask: pd.Series | str, data: pd.DataFrame) -> pd.Series:
    """Return a boolean Series on ``data.index`` that is True at the selected times.

    Parameters
    ----------
    mask : pandas.Series or str
        The selection: a column of ``data`` named by a string, or a Series aligned to
        ``data.index``. In both forms a time is selected where the value is truthy
        (non-zero, True) and not missing (NaN, None, ``pd.NA``); times absent from a
        Series are not selected.
    data : pandas.DataFrame
        The data being plotted, indexed by time.

    Returns
    -------
    pandas.Series of bool
        One value per row of ``data``, in the order of ``data.index``.

    Raises
    ------
    KeyError
        If ``mask`` names a column that ``data`` does not contain.
    TypeError
        If ``mask`` is of another type, for example a list of times, a DatetimeIndex,
        or a numpy array.
    ValueError
        If the Series has duplicate times and is not indexed exactly like ``data``.
        A Series with the same index as ``data``, such as one computed from the data's
        own columns, is used row by row, so duplicate times are accepted there. A
        Series with unique times is aligned by time, which is defined also when
        ``data`` repeats a time: every row of that time receives the Series value. A
        Series that repeats a time with another index has no unique value for that
        time, so the result would be undefined.
    """
    if isinstance(mask, str):
        if mask not in data.columns:
            raise KeyError(f"column {mask!r} not in the data")
        values = data[mask]
    elif isinstance(mask, pd.Series):
        if mask.index.equals(data.index):
            values = mask  # same rows in the same order, also when times repeat
        elif mask.index.has_duplicates:
            raise ValueError(
                "the selection of times has duplicate times and is not indexed like the data, so "
                "it cannot be aligned to the data; compute the selection from the plotted data "
                "itself (same index) or remove the duplicate times"
            )
        else:
            values = mask.reindex(data.index)  # times absent from the mask become missing
    else:
        raise TypeError(
            "a selection of times must be a column name or a boolean pandas Series indexed "
            f"by time, not {type(mask).__name__}"
        )
    present = values.notna().to_numpy()
    truthy = values.to_numpy(dtype=object, na_value=False).astype(bool)
    return pd.Series(present & truthy, index=data.index)


def as_time(x, index: pd.Index) -> pd.Timestamp:
    """Convert a time given by the caller to a Timestamp comparable with ``index``.

    When ``index`` has a time zone, a time without a time zone is taken to be in that
    zone, and a time with another time zone is converted to it. When ``index`` has no
    time zone, a time without one is returned unchanged, and the time zone of a time
    that has one is removed, keeping its wall-clock time.

    Parameters
    ----------
    x : timestamp-like
        A ``pandas.Timestamp``, ``datetime``, ``numpy.datetime64``, or a string such as
        ``"2024-01-05 12:00"``.
    index : pandas.Index
        The time index of the data being plotted, a DatetimeIndex; only its time zone
        is read.

    Returns
    -------
    pandas.Timestamp
        The time, in the time zone of ``index``, or without a time zone when ``index``
        has none.
    """
    ts = cast(pd.Timestamp, pd.Timestamp(x))
    tz = getattr(index, "tz", None)
    if tz is None:
        return ts.tz_localize(None) if ts.tz is not None else ts
    return ts.tz_localize(tz) if ts.tz is None else ts.tz_convert(tz)
