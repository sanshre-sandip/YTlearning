"""Tests for GitHub API tools."""

from unittest.mock import patch

import pytest

from src.github_tools import (
    github_get_repo,
    github_list_issues,
    github_create_issue,
    github_list_prs,
    github_get_pr,
    github_comment,
    github_get_commits,
    github_list_repos,
)


@pytest.fixture(autouse=True)
def mock_headers():
    """Clear env so we don't accidentally make real API calls."""
    with patch("src.github_tools.GITHUB_TOKEN", ""):
        yield


@patch("src.github_tools.httpx.get")
def test_github_get_repo(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"full_name": "owner/repo", "stargazers_count": 10}

    result = github_get_repo("owner/repo")
    assert result["full_name"] == "owner/repo"
    mock_get.assert_called_once()


@patch("src.github_tools.httpx.get")
def test_github_list_issues(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"number": 1, "title": "Bug", "state": "open"},
        {"number": 2, "title": "Feature", "state": "closed"},
    ]

    issues = github_list_issues("owner/repo", state="open", limit=5)
    assert len(issues) == 2
    assert issues[0]["title"] == "Bug"


@patch("src.github_tools.httpx.post")
def test_github_create_issue(mock_post):
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"number": 10, "title": "New", "state": "open"}

    result = github_create_issue("owner/repo", "New", "desc", ["bug"])
    assert result["number"] == 10
    mock_post.assert_called_once()


@patch("src.github_tools.httpx.get")
def test_github_list_prs(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"number": 1, "title": "PR 1", "state": "open"}]

    prs = github_list_prs("owner/repo", limit=10)
    assert len(prs) == 1


@patch("src.github_tools.httpx.get")
def test_github_get_pr(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"number": 5, "title": "PR"}

    pr = github_get_pr("owner/repo", 5)
    assert pr["number"] == 5


@patch("src.github_tools.httpx.post")
def test_github_comment(mock_post):
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"id": 99, "body": "Nice!"}

    result = github_comment("owner/repo", 1, "Nice!")
    assert result["body"] == "Nice!"


@patch("src.github_tools.httpx.get")
def test_github_get_commits(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"sha": "a", "commit": {"author": {"name": "X", "date": "2026-01-01T00:00:00Z"}, "message": "m"}}
    ]

    commits = github_get_commits("owner/repo", branch="main", limit=10)
    assert len(commits) == 1


@patch("src.github_tools.httpx.get")
def test_github_list_repos(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"name": "a"}, {"name": "b"}]

    repos = github_list_repos("owner", limit=10)
    assert len(repos) == 2
