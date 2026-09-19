import numpy as np
import pytest
from build123d import Box, Location

from pruefstand import Body


def box(key, size, at=(0, 0, 0), moving=False):
    s = Box(*size).locate(Location(tuple(float(x) for x in at)))
    return Body(key, key, solid=s, moving=moving)


@pytest.fixture
def wuerfel_paar():
    """Zwei 10er-Würfel mit 0,5 mm Spalt in X."""
    return box('A', (10, 10, 10), (0, 0, 0)), box('B', (10, 10, 10), (10.5, 0, 0))
