"""Shared fixtures for tests."""

from pathlib import Path
import pytest


@pytest.fixture
def sample_commit() -> dict:
    return {
        "sha": "abc123",
        "commit": {
            "author": {"name": "Test", "date": "2026-06-01T12:00:00Z"},
            "message": "test commit",
        },
    }


@pytest.fixture
def sample_issue() -> dict:
    return {
        "id": 1,
        "number": 42,
        "title": "Test issue",
        "state": "open",
        "body": "Body text",
    }


@pytest.fixture
def sample_pr() -> dict:
    return {
        "id": 1,
        "number": 7,
        "title": "Test PR",
        "state": "open",
        "body": "PR body",
        "head": {"ref": "feature-branch"},
        "base": {"ref": "main"},
    }
