"""Shared pieces for the rules-layer tests."""

import pytest
from hypothesis import find

from tests.strategies import graphs


@pytest.fixture
def a_small_valid_graph():
    """One valid map, the smallest the generator will make.

    A few faults cannot be reached by damaging a random map — an arrow with neither
    end on the map, a claim that points at itself — so those tests start from one
    fixed map and break it by hand. Asking the generator for its smallest example
    keeps that map honest: it is built by the same code as every other.
    """
    return find(graphs(), lambda candidate: len(candidate.propositions) >= 2)
