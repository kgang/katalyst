"""The route that names the program and the build that is running.

It reads the version from the installed package rather than from a constant
written by hand, so this test also catches the case where the program is being
run without being installed properly.
"""

from fastapi.testclient import TestClient

from katalyst import __version__
from katalyst.api.main import app


def test_about_names_the_product_and_the_running_version() -> None:
    """The answer is the product name and the version from the package metadata."""
    with TestClient(app) as client:
        response = client.get("/api/about")

    assert response.status_code == 200
    assert response.json() == {"name": "Katalyst", "version": __version__}
    assert __version__
