"""MCP client: connects to external MCP server processes, discovers tools, calls them.

Usage:
    manager = MCPServerManager()
    await manager.start_all()  # spawns all servers from config
    tools = manager.get_tool_definitions()  # merge into Ollama tool list
    result = await manager.call_tool("server-name", "tool-name", {...})
    await manager.shutdown()
"""

from __future__ import annotations

import json
import os
import re
import signal
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.types import Tool as MCPTool


def _resolve_env(env: dict[str, str] | None) -> dict[str, str] | None:
    """Resolve ${VAR} placeholders in env dict from os.environ."""
    if not env:
        return env
    resolved = {}
    for k, v in env.items():
        if isinstance(v, str):
            v = os.path.expandvars(v)
        resolved[k] = v
    return resolved


class MCPToolWrapper:
    """Wraps an MCP tool from an external server with its origin."""

    def __init__(self, server_name: str, tool: MCPTool):
        self.server_name = server_name
        self.name = tool.name
        self.description = tool.description or ""
        self.input_schema = tool.inputSchema

    def to_ollama_tool(self) -> dict[str, Any]:
        """Convert to Ollama-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class MCPConnection:
    """A single connection to an MCP server process."""

    def __init__(self, name: str, params: StdioServerParameters):
        self.name = name
        self.params = params
        self.session: ClientSession | None = None
        self._transport = None
        self._tools: list[MCPToolWrapper] = []

    async def start(self) -> list[MCPToolWrapper]:
        """Spawn the server process and discover its tools."""
        self._transport = await stdio_client(self.params).__aenter__()
        read, write = self._transport
        self.session = await ClientSession(read, write).__aenter__()
        await self.session.initialize()
        result = await self.session.list_tools()
        self._tools = [MCPToolWrapper(self.name, t) for t in result.tools]
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on this server."""
        if not self.session:
            raise RuntimeError(f"MCP server '{self.name}' not started")
        result = await self.session.call_tool(tool_name, arguments)
        # Collect all content text
        texts = []
        for content in result.content:
            if hasattr(content, "text") and content.text:
                texts.append(content.text)
        return "\n".join(texts) if texts else result.content

    async def stop(self):
        """Gracefully stop the server."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._transport:
                await self._transport.__aexit__(None, None, None)
        except Exception:
            pass


class MCPServerManager:
    """Manages multiple external MCP server connections."""

    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.connections: dict[str, MCPConnection] = {}

    def load_config(self) -> list[dict[str, Any]]:
        """Load and parse the MCP servers config file."""
        if not self.config_path.exists():
            print(f"  [yellow]⚠ MCP config not found: {self.config_path}[/yellow]")
            return []
        with open(self.config_path) as f:
            data = json.load(f)
        return data.get("servers", [])

    async def start_all(self) -> list[dict[str, Any]]:
        """Start all configured MCP servers and return their tool definitions."""
        servers = self.load_config()
        if not servers:
            return []

        all_tool_defs: list[dict[str, Any]] = []
        for srv in servers:
            name = srv.get("name", "unknown")
            try:
                env = _resolve_env(srv.get("env"))
                params = StdioServerParameters(
                    command=srv["command"],
                    args=srv.get("args", []),
                    env=env,
                )
                conn = MCPConnection(name, params)
                tools = await conn.start()
                self.connections[name] = conn
                for t in tools:
                    all_tool_defs.append(t.to_ollama_tool())
                print(f"  [green]✓ MCP server '{name}' — {len(tools)} tools loaded[/green]")
            except Exception as e:
                print(f"  [red]✗ MCP server '{name}' failed: {e}[/red]")

        return all_tool_defs

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on whichever server it belongs to.

        Searches all connections for the tool name.
        """
        for conn in self.connections.values():
            if any(t.name == tool_name for t in conn._tools):
                return await conn.call_tool(tool_name, arguments)
        raise ValueError(f"Tool '{tool_name}' not found on any connected MCP server")

    async def shutdown(self):
        """Stop all connected MCP servers."""
        for name, conn in list(self.connections.items()):
            await conn.stop()
            print(f"  [dim]Stopped MCP server: {name}[/dim]")
        self.connections.clear()
