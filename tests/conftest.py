"""Shared test setup: a non-interactive matplotlib backend and a clean state per test."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from tspanels.style import DEFAULT_STYLE, set_default_style


@pytest.fixture(autouse=True)
def _reset_state():
    """Restore the default style and close all figures after each test."""
    yield
    set_default_style(DEFAULT_STYLE)
    plt.close("all")
