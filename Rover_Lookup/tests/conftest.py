"""
Pytest configuration for Rover_Lookup tests.
"""

import logging
from pathlib import Path
import sys

import pytest

# Add the parent directory to the path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def setup_logging():
    """Automatically configure logging for all tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
