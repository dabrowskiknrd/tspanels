import numpy as np
import pandas as pd
import pytest

from tspanels.data import as_time, resolve_mask, to_frame

IDX = pd.date_range("2024-01-01", periods=4, freq="15min")


def test_pandas_with_datetime_index_is_sorted_copy():
    df = pd.DataFrame({"a": [1, 2, 3, 4]}, index=IDX[::-1])
    out = to_frame(df)
    assert out.index.is_monotonic_increasing
    assert out is not df
    assert df.index[0] == IDX[-1]


def test_pandas_with_time_column():
    df = pd.DataFrame({"t": IDX, "a": range(4)})
    assert list(to_frame(df, time="t").index) == list(IDX)


def test_dict_of_series_outer_join():
    out = to_frame({"a": pd.Series([1, 2], IDX[:2]), "b": pd.Series([3], IDX[3:])})
    assert len(out) == 3
    assert out["b"].isna().sum() == 2


def test_polars_requires_time_and_converts():
    pl = pytest.importorskip("polars")
    frame = pl.DataFrame({"t": IDX.to_numpy(), "a": [1, 2, 3, 4]})
    with pytest.raises(ValueError):
        to_frame(frame)
    assert list(to_frame(frame, time="t")["a"]) == [1, 2, 3, 4]


def test_non_datetime_index_raises_type_error_naming_time():
    with pytest.raises(TypeError, match="time"):
        to_frame(pd.DataFrame({"a": [1, 2]}))


def test_unsupported_type_raises_type_error():
    with pytest.raises(TypeError):
        to_frame([1, 2, 3])


def test_missing_time_column_raises_key_error():
    with pytest.raises(KeyError):
        to_frame(pd.DataFrame({"a": [1]}), time="t")


def test_resolve_mask_column_truthy_not_missing():
    df = pd.DataFrame({"g": [1, 0, np.nan, 2]}, index=IDX)
    assert list(resolve_mask("g", df)) == [True, False, False, True]


def test_resolve_mask_series_reindexed():
    df = pd.DataFrame({"a": range(4)}, index=IDX)
    assert list(resolve_mask(pd.Series([True], IDX[1:2]), df)) == [False, True, False, False]


def test_resolve_mask_missing_column_raises_key_error():
    df = pd.DataFrame({"a": range(4)}, index=IDX)
    with pytest.raises(KeyError, match="nope"):
        resolve_mask("nope", df)


def test_as_time_localizes_naive_to_aware_index():
    idx = IDX.tz_localize("UTC")
    assert as_time("2024-01-01 00:15", idx) == idx[1]
    assert as_time(pd.Timestamp("2024-01-01 01:15", tz="Europe/Warsaw"), idx) == idx[1]


def test_as_time_naive_index_returns_naive():
    assert as_time("2024-01-01 00:15", IDX) == IDX[1]


def test_resolve_mask_nullable_boolean_series_with_na():
    df = pd.DataFrame({"a": range(4)}, index=IDX)
    mask = pd.Series([True, pd.NA, False, True], index=IDX, dtype="boolean")
    assert list(resolve_mask(mask, df)) == [True, False, False, True]


def test_resolve_mask_series_missing_values_are_not_selected():
    df = pd.DataFrame({"a": range(4)}, index=IDX)
    assert list(resolve_mask(pd.Series([1.0, np.nan, 0.0, 2.0], IDX), df)) == [True, False, False, True]


@pytest.mark.parametrize("bad", [IDX[:2], [IDX[0]], np.array([True, False, True, False])])
def test_resolve_mask_unsupported_type_raises_clear_type_error(bad):
    df = pd.DataFrame({"a": range(4)}, index=IDX)
    with pytest.raises(TypeError, match="column name or a boolean pandas Series"):
        resolve_mask(bad, df)


def test_time_column_without_datetimes_suggests_to_datetime():
    df = pd.DataFrame({"t": ["2024-01-01", "2024-01-02"], "a": [1, 2]})
    with pytest.raises(TypeError, match="to_datetime") as info:
        to_frame(df, time="t")
    assert "'t'" in str(info.value)


def test_dict_without_time_index_names_the_series():
    with pytest.raises(TypeError, match="Series of a") as err:
        to_frame({"a": pd.Series([1, 2]), "b": pd.Series([3, 4])})
    assert "time=" not in str(err.value)


def test_dict_with_time_argument_raises_value_error():
    with pytest.raises(ValueError, match="time="):
        to_frame({"a": pd.Series([1, 2], IDX[:2])}, time="t")


DUP = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 01:00", "2024-01-01 02:00"])


def test_resolve_mask_on_duplicate_times_accepts_mask_on_the_same_index():
    df = pd.DataFrame({"a": [1.0, 2, 3, 4]}, index=DUP)
    assert resolve_mask(df["a"] > 2, df).tolist() == [False, False, True, True]


def test_resolve_mask_with_duplicate_times_not_matching_raises_clear_value_error():
    df = pd.DataFrame({"a": [1.0, 2, 3, 4]}, index=DUP)
    with pytest.raises(ValueError, match="duplicate times"):
        resolve_mask((df["a"] > 2).iloc[:3], df)


def test_resolve_mask_with_unique_times_on_duplicate_data_is_aligned_by_time():
    df = pd.DataFrame({"a": [1.0, 2, 3, 4]}, index=DUP)
    mask = pd.Series([False, True], index=DUP[[0, 1]])
    assert resolve_mask(mask, df).tolist() == [False, True, True, False]
