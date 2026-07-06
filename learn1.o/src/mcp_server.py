"""FastMCP server wrapper. Exposes all agent tools as MCP tools.

Run standalone:
    python -m src.mcp_server
"""

from mcp.server.fastmcp import FastMCP

from src import github_tools
from src.visualize import OUTPUT_DIR

mcp = FastMCP("AI Agent", instructions="AI coding agent with GitHub, visualization, and voice capabilities.")


# ── GitHub tools ───────────────────────────────────────────────────

@mcp.tool()
def github_get_repo(repo: str) -> str:
    """Get metadata about a GitHub repository (stars, forks, description). Format: owner/repo"""
    return str(github_tools.github_get_repo(repo))


@mcp.tool()
def github_list_issues(repo: str, state: str = "open", limit: int = 10) -> str:
    """List issues in a repository. state: open|closed|all"""
    return str(github_tools.github_list_issues(repo, state, limit))


@mcp.tool()
def github_create_issue(repo: str, title: str, body: str = "", labels: list[str] | None = None) -> str:
    """Create an issue in a repository."""
    return str(github_tools.github_create_issue(repo, title, body, labels))


@mcp.tool()
def github_list_prs(repo: str, state: str = "open", limit: int = 10) -> str:
    """List pull requests. state: open|closed|all"""
    return str(github_tools.github_list_prs(repo, state, limit))


@mcp.tool()
def github_get_pr(repo: str, pr_number: int) -> str:
    """Get details of a specific pull request."""
    return str(github_tools.github_get_pr(repo, pr_number))


@mcp.tool()
def github_comment(repo: str, issue_number: int, body: str) -> str:
    """Add a comment to an issue or PR."""
    return str(github_tools.github_comment(repo, issue_number, body))


@mcp.tool()
def github_get_commits(repo: str, branch: str = "main", since: str = "", limit: int = 30) -> str:
    """List recent commits. Use ISO 8601 date for since (e.g., 2025-01-01)."""
    s: str | None = since if since else None
    return str(github_tools.github_get_commits(repo, branch, s, limit))


@mcp.tool()
def github_list_repos(owner: str, limit: int = 30) -> str:
    """List repositories for a user or organization."""
    return str(github_tools.github_list_repos(owner, limit))


# ── Main ──────────────────────────────────────────────────────────

def main():
    print(f"  MCP Server running. Images saved to: {OUTPUT_DIR}")
    print("  Connect from any MCP client (Claude Desktop, Cursor, etc.)")
    mcp.run()


if __name__ == "__main__":
    main()
