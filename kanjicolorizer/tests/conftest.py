import pytest
import os


@pytest.fixture
def total_characters() -> int:
    return 11724


@pytest.fixture
def testdata_dir(request: pytest.FixtureRequest) -> str:
    filepath = request.node.path
    return os.path.join(os.path.dirname(filepath), 'testdata')
