"""The two routes that hand out the worked examples.

The point of these tests is the crossing: the map leaves the program as JSON,
comes back through the same shapes, and still breaks no rule. If something is
lost on the way out — a tuple flattened, a date turned into a string nothing
parses back — the map that arrives is not the map that left, and this is where
that shows up rather than in the browser.
"""

from fastapi.testclient import TestClient

from katalyst.api.main import app
from katalyst.domain import Branch, Graph, validate
from katalyst.fixtures import FIXTURE_DATE, HORMUZ


def test_the_list_route_offers_the_hormuz_example() -> None:
    """Asking what examples exist names hormuz, with a title and a sentence."""
    with TestClient(app) as client:
        response = client.get("/api/fixtures")

    assert response.status_code == 200
    offered = response.json()
    assert [one["id"] for one in offered] == ["hormuz"]
    assert offered[0]["title"]
    assert offered[0]["one_line"]


def test_the_detail_route_returns_a_map_that_is_still_valid_after_the_trip() -> None:
    """The map comes back through JSON unchanged, and breaks no rule on arrival."""
    with TestClient(app) as client:
        response = client.get("/api/fixtures/hormuz")

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["id"] == "hormuz"
    assert bundle["fixture_date"] == FIXTURE_DATE.isoformat()

    came_back = Graph.model_validate(bundle["graph"])
    assert validate(came_back) == []
    assert came_back == HORMUZ


def test_the_detail_route_returns_the_branch_with_its_three_edits() -> None:
    """The branch travels as an ordered list of edits, each one still telling its kind apart."""
    with TestClient(app) as client:
        response = client.get("/api/fixtures/hormuz")

    branches = [Branch.model_validate(one) for one in response.json()["branches"]]

    assert len(branches) == 1
    assert [edit.kind for edit in branches[0].interventions] == ["do", "insert", "do"]


def test_asking_for_an_example_that_does_not_exist_answers_in_words() -> None:
    """An unknown name comes back as 404 with a sentence naming what does exist."""
    with TestClient(app) as client:
        response = client.get("/api/fixtures/photonics")

    assert response.status_code == 404
    message = response.json()["detail"]
    assert "photonics" in message
    assert "hormuz" in message
    # A reader is shown this, so it has to be a sentence rather than a code.
    assert len(message.split()) >= 8
