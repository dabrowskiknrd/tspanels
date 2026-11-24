import pytest

from tspanels import Line, Panel, as_panels


def test_panel_converts_single_string_to_line_list():
    assert Panel("a").lines == [Line("a")]


def test_panel_columns_in_order():
    assert Panel([Line("a"), "b"]).columns() == ["a", "b"]


def test_as_panels_from_dict():
    panels = as_panels({"a": "A", "b": "B"})
    assert [p.title for p in panels] == ["A", "B"]
    assert [p.columns() for p in panels] == [["a"], ["b"]]


def test_as_panels_from_mixed_sequence():
    panels = as_panels(["a", ("b", "B"), Line("c"), Panel(["d"])])
    assert [p.columns() for p in panels] == [["a"], ["b"], ["c"], ["d"]]
    assert panels[1].title == "B"


def test_as_panels_single_item_is_one_panel():
    assert [p.columns() for p in as_panels("abc")] == [["abc"]]
    assert [p.columns() for p in as_panels(Line("a"))] == [["a"]]
    assert [p.columns() for p in as_panels(Panel(["a", "b"]))] == [["a", "b"]]


@pytest.mark.parametrize("item", [("a", "b", "c"), (1, "x"), ("a", 2), ["a", "b"], 3])
def test_as_panels_malformed_item_raises_type_error(item):
    with pytest.raises(TypeError, match="Panel"):
        as_panels([item])


def test_as_panels_pair_whose_title_is_another_column_raises():
    with pytest.raises(ValueError, match=r"Panel\(\['a', 'b'\]\)"):
        as_panels([("a", "b")], columns=["a", "b"])


def test_as_panels_pair_title_equal_to_own_column_or_not_a_column_is_accepted():
    panels = as_panels([("a", "a"), ("b", "B")], columns=["a", "b"])
    assert [p.title for p in panels] == ["a", "B"]


def test_as_panels_dict_title_is_never_read_as_a_column():
    assert as_panels({"a": "b"}, columns=["a", "b"])[0].title == "b"
