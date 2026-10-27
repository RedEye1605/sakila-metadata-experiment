import pytest


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip = pytest.mark.skip(reason="requires --run-integration and the isolated research MySQL")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)

