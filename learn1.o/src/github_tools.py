"""GitHub API tools exposed to the AI agent."""

from typing import Any
import httpx

from src.config import GITHUB_TOKEN

API_BASE = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "learn1-agent/0.1",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def _get(path: str, params: dict | None = None) -> dict[str, Any] | list[dict[str, Any]]:
    url = f"{API_BASE}{path}"
    resp = httpx.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, body: dict) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    resp = httpx.post(url, headers=HEADERS, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def github_get_repo(repo: str) -> dict[str, Any]:
    """Get metadata about a GitHub repository. Format: owner/repo."""
    return _get(f"/repos/{repo}")


def github_list_issues(repo: str, state: str = "open", limit: int = 10) -> list[dict[str, Any]]:
    """List issues in a repository. state: open|closed|all."""
    data = _get(f"/repos/{repo}/issues", params={"state": state, "per_page": min(limit, 100)})
    return data[:limit]


def github_create_issue(repo: str, title: str, body: str = "", labels: list[str] | None = None) -> dict[str, Any]:
    """Create an issue in a repository."""
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    return _post(f"/repos/{repo}/issues", payload)


def github_list_prs(repo: str, state: str = "open", limit: int = 10) -> list[dict[str, Any]]:
    """List pull requests in a repository. state: open|closed|all."""
    data = _get(f"/repos/{repo}/pulls", params={"state": state, "per_page": min(limit, 100)})
    return data[:limit]


def github_get_pr(repo: str, pr_number: int) -> dict[str, Any]:
    """Get details of a specific pull request."""
    return _get(f"/repos/{repo}/pulls/{pr_number}")


def github_comment(repo: str, issue_number: int, body: str) -> dict[str, Any]:
    """Add a comment to an issue or pull request."""
    return _post(f"/repos/{repo}/issues/{issue_number}/comments", {"body": body})


def github_get_commits(repo: str, branch: str = "main", since: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    """List recent commits in a repository."""
    params: dict[str, Any] = {"sha": branch, "per_page": min(limit, 100)}
    if since:
        params["since"] = since
    data = _get(f"/repos/{repo}/commits", params=params)
    return data[:limit]


def github_list_repos(owner: str, limit: int = 30) -> list[dict[str, Any]]:
    """List repositories for a user or organization."""
    data = _get(f"/users/{owner}/repos", params={"per_page": min(limit, 100), "sort": "updated"})
    return data[:limit]
