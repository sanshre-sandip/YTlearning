"""Agent core: connects to Ollama with tool definitions and manages the conversation loop."""

from typing import Any, Callable
import json
from pathlib import Path

import ollama

from src.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from src import github_tools
from src import visualize

# ── Tool registry ──────────────────────────────────────────────────

ToolDef = dict[str, Any]          # JSON Schema tool definition for Ollama
ToolFunc = Callable[..., Any]     # The Python function that implements it


class Tool:
    def __init__(self, name: str, description: str, parameters: dict[str, Any], fn: ToolFunc):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.fn = fn

    def definition(self) -> ToolDef:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def execute(self, **kwargs) -> Any:
        return self.fn(**kwargs)


# ── Build all tools ────────────────────────────────────────────────

def _str_param(desc: str) -> dict:
    return {"type": "string", "description": desc}

def _int_param(desc: str) -> dict:
    return {"type": "integer", "description": desc}

def _str_list_param(desc: str) -> dict:
    return {"type": "array", "items": {"type": "string"}, "description": desc}


TOOLS: list[Tool] = [
    # ---- GitHub tools ----
    Tool(
        name="github_get_repo",
        description="Get metadata about a GitHub repository (stars, forks, description, etc.). Format: owner/repo",
        parameters={
            "type": "object",
            "properties": {"repo": _str_param("Repository name in owner/repo format")},
            "required": ["repo"],
        },
        fn=github_tools.github_get_repo,
    ),
    Tool(
        name="github_list_issues",
        description="List issues in a GitHub repository. Filter by state: open, closed, or all.",
        parameters={
            "type": "object",
            "properties": {
                "repo": _str_param("Repository name in owner/repo format"),
                "state": _str_param("Issue state: open, closed, or all"),
                "limit": _int_param("Maximum number of issues to return"),
            },
            "required": ["repo"],
        },
        fn=github_tools.github_list_issues,
    ),
    Tool(
        name="github_create_issue",
        description="Create a new issue in a GitHub repository.",
        parameters={
            "type": "object",
            "properties": {
                "repo": _str_param("Repository name in owner/repo format"),
                "title": _str_param("Issue title"),
                "body": _str_param("Issue body/description"),
                "labels": _str_list_param("List of labels to apply"),
            },
            "required": ["repo", "title"],
        },
        fn=github_tools.github_create_issue,
    ),
    Tool(
        name="github_list_prs",
        description="List pull requests in a GitHub repository. Filter by state: open, closed, or all.",
        parameters={
            "type": "object",
            "properties": {
                "repo": _str_param("Repository name in owner/repo format"),
                "state": _str_param("PR state: open, closed, or all"),
                "limit": _int_param("Maximum number of PRs to return"),
            },
            "required": ["repo"],
        },
        fn=github_tools.github_list_prs,
    ),
    Tool(
        name="github_get_pr",
        description="Get detailed information about a specific pull request.",
        parameters={
            "type": "object",
            "properties": {
                "repo": _str_param("Repository name in owner/repo format"),
                "pr_number": _int_param("Pull request number"),
            },
            "required": ["repo", "pr_number"],
        },
        fn=github_tools.github_get_pr,
    ),
    Tool(
        name="github_comment",
        description="Add a comment to an issue or pull request on GitHub.",
        parameters={
            "type": "object",
            "properties": {
                "repo": _str_param("Repository name in owner/repo format"),
                "issue_number": _int_param("Issue or PR number"),
                "body": _str_param("Comment text body"),
            },
            "required": ["repo", "issue_number", "body"],
        },
        fn=github_tools.github_comment,
    ),
    Tool(
        name="github_get_commits",
        description="Get recent commits from a GitHub repository. Optionally filter by branch and date.",
        parameters={
            "type": "object",
            "properties": {
                "repo": _str_param("Repository name in owner/repo format"),
                "branch": _str_param("Branch name (default: main)"),
                "since": _str_param("ISO 8601 date string to filter commits after (e.g., 2025-01-01)"),
                "limit": _int_param("Maximum number of commits to return"),
            },
            "required": ["repo"],
        },
        fn=github_tools.github_get_commits,
    ),
    Tool(
        name="github_list_repos",
        description="List repositories for a GitHub user or organization.",
        parameters={
            "type": "object",
            "properties": {
                "owner": _str_param("GitHub username or organization name"),
                "limit": _int_param("Maximum number of repos to return"),
            },
            "required": ["owner"],
        },
        fn=github_tools.github_list_repos,
    ),
    # ---- Visualization tools ----
    Tool(
        name="visualize_commits",
        description="Generate a line chart showing commit activity over time from commit data. Returns the image path.",
        parameters={
            "type": "object",
            "properties": {
                "commits": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of commit objects from github_get_commits",
                },
            },
            "required": ["commits"],
        },
        fn=visualize.plot_commit_activity,
    ),
    Tool(
        name="visualize_issue_stats",
        description="Generate a bar chart showing open vs closed issue counts. Returns the image path.",
        parameters={
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of issue objects from github_list_issues",
                },
            },
            "required": ["issues"],
        },
        fn=visualize.plot_issue_stats,
    ),
    Tool(
        name="visualize_diagram",
        description="Draw a directed dependency/architecture graph from nodes and edges. Returns the image path.",
        parameters={
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "prefixItems": [
                            {"type": "string", "description": "Node ID"},
                            {"type": "string", "description": "Node label"},
                        ],
                    },
                    "description": "Array of [node_id, label] pairs",
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "prefixItems": [
                            {"type": "string", "description": "Source node ID"},
                            {"type": "string", "description": "Target node ID"},
                        ],
                    },
                    "description": "Array of [source_id, target_id] pairs",
                },
            },
            "required": ["nodes", "edges"],
        },
        fn=visualize.draw_dependency_graph,
    ),
]

TOOL_DEFINITIONS = [t.definition() for t in TOOLS]
TOOL_MAP: dict[str, Tool] = {t.name: t for t in TOOLS}


# ── Agent ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI coding agent assistant that helps monitor and manage GitHub projects.

You have tools to:
- Read GitHub repositories, issues, PRs, commits, and repo lists
- Create issues and add comments on GitHub
- Generate visualizations: commit activity charts, issue status charts, architecture diagrams
- Provide text updates and summaries

Rules:
1. When the user asks about a repo, use the GitHub tools to fetch live data.
2. When the user asks for charts or visualizations, first fetch the data, then use the viz tools.
3. Always summarize what you found before showing visualizations.
4. You can create issues and comment on PRs when asked.
5. If the user doesn't specify a repo, use the conversation context or ask.

Keep responses clear and actionable."""


class Agent:
    """Manages conversation with Ollama, handles tool calls, and maintains history."""

    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.client = ollama.Client(host=base_url)
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def reset(self):
        """Clear conversation history (keeps system prompt)."""
        self.messages = [self.messages[0]]

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def _call_ollama(self) -> dict[str, Any]:
        """Send messages + tools to Ollama and return the full response."""
        return self.client.chat(
            model=self.model,
            messages=self.messages,
            tools=TOOL_DEFINITIONS,
        )

    def _dispatch_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a tool by name with parsed arguments."""
        tool = TOOL_MAP.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        result = tool.execute(**arguments)
        return result

    def run(self, user_input: str) -> list[dict[str, Any]]:
        """Run one turn: send user input, process tool calls, return all steps.

        Returns a list of step dicts, each with 'type': 'text' | 'tool_call' | 'viz'.
        """
        self.add_user_message(user_input)
        steps: list[dict[str, Any]] = []
        max_turns = 10

        for turn in range(max_turns):
            response = self._call_ollama()
            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # Add assistant's response to history
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            # If there's text content, capture it
            if content:
                steps.append({"type": "text", "content": content})

            # Process each tool call
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                raw_args = func.get("arguments", {})

                # Arguments might be a JSON string (some Ollama versions)
                if isinstance(raw_args, str):
                    arguments = json.loads(raw_args)
                else:
                    arguments = raw_args

                try:
                    result = self._dispatch_tool(tool_name, arguments)

                    # Determine step type
                    step_type = "tool_call"
                    step_info: dict[str, Any] = {"type": step_type, "tool": tool_name, "result": result}

                    # If it's a viz function, record the output path separately
                    if tool_name.startswith("visualize_") and isinstance(result, Path):
                        step_info["type"] = "viz"
                        step_info["image_path"] = str(result)

                    steps.append(step_info)

                    # Send tool result back to Ollama
                    result_str = json.dumps(result, default=str, indent=2)
                    self.messages.append({
                        "role": "tool",
                        "content": result_str,
                    })

                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {e}"
                    self.messages.append({
                        "role": "tool",
                        "content": error_msg,
                    })
                    steps.append({"type": "tool_call", "tool": tool_name, "error": str(e)})

            # If no tool calls, we're done
            if not tool_calls:
                break

        return steps
