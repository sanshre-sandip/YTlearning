#!/usr/bin/env python3
"""Entry point for the AI Agent. Two modes: text (default) and voice.

Usage:
    python main.py                  # text mode
    python main.py --voice          # voice mode
    python main.py --no-mcp         # skip external MCP servers
"""

from __future__ import annotations

import sys
import asyncio
import argparse
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.config import GITHUB_TOKEN, OLLAMA_BASE_URL, OLLAMA_MODEL, MCP_SERVERS_CONFIG
from src.agent import Agent
from src.mcp_client import MCPServerManager

console = Console()


# ── Prerequisites ──────────────────────────────────────────────────

def check_prerequisites() -> bool:
    """Verify Ollama is reachable and GitHub token is set."""
    import httpx
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        model_names = [m["name"] for m in models]
        if OLLAMA_MODEL not in model_names and f"{OLLAMA_MODEL}:latest" not in model_names:
            console.print(f"[yellow]⚠ Model '{OLLAMA_MODEL}' not found locally. Pull it: ollama pull {OLLAMA_MODEL}[/yellow]")
        else:
            console.print(f"[green]✓ Ollama — {OLLAMA_MODEL} available[/green]")
    except Exception as e:
        console.print(f"[red]✗ Cannot reach Ollama at {OLLAMA_BASE_URL}[/red]")
        console.print(f"  {e}")
        console.print("  Make sure Ollama is running: ollama serve")
        return False

    if not GITHUB_TOKEN:
        console.print("[yellow]⚠ GITHUB_TOKEN not set. GitHub tools will fail on private repos.[/yellow]")
    else:
        console.print("[green]✓ GitHub token configured[/green]")

    return True


def show_banner():
    console.print(Panel.fit(
        "[bold blue]AI Agent[/bold blue] — Ollama + MCP + GitHub + Viz + Voice\n"
        f"Model: {OLLAMA_MODEL}  |  Type [bold]exit[/bold] to quit",
        border_style="blue",
    ))


# ── Turn processing (shared between text and voice) ────────────────

async def process_turn(agent: Agent, user_input: str):
    """Run one agent turn and display results."""
    with console.status("[bold blue]Thinking...[/bold blue]"):
        try:
            steps = await agent.run(user_input)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return

    for step in steps:
        t = step["type"]

        if t == "text":
            content = step["content"]
            if content.strip():
                console.print(Panel(Markdown(content), border_style="green"))

        elif t == "tool_call":
            tool = step.get("tool", "?")
            result = step.get("result", step.get("error", ""))
            if not tool.startswith("visualize_"):
                console.print(f"[dim]→ {tool} → {_summarize(result)}[/dim]")

        elif t == "viz":
            img_path = step.get("image_path", "")
            tool = step.get("tool", "?")
            console.print(f"[bold blue]📊 {tool} → saved: {img_path}[/bold blue]")


def _summarize(result) -> str:
    if isinstance(result, list):
        return f"{len(result)} items"
    if isinstance(result, dict):
        return f"{len(result)} keys"
    s = str(result)
    return s[:80] + "..." if len(s) > 80 else s


# ── Text mode ──────────────────────────────────────────────────────

async def run_text_mode(agent: Agent):
    show_banner()
    console.print("[dim]Tip: Try 'Show me recent commits in user/repo' or 'Create a diagram of...'[/dim]\n")

    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(
                None, lambda: Prompt.ask("[bold cyan]You[/bold cyan]")
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if not user_input.strip():
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        await process_turn(agent, user_input)


# ── Voice mode ─────────────────────────────────────────────────────

async def run_voice_mode(agent: Agent):
    from src.voice import record_and_transcribe, speak

    show_banner()
    console.print("[dim]Voice mode: Press Enter to record, Enter again to stop[/dim]\n")

    loop = asyncio.get_event_loop()

    while True:
        console.print("[bold cyan]Press Enter to speak (or type 'exit' to quit)[/bold cyan]")

        try:
            text = await loop.run_in_executor(None, record_and_transcribe)
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if text is None:
            continue

        text_lower = text.lower().strip()
        if text_lower in ("exit", "quit", "goodbye"):
            console.print("[yellow]Goodbye![/yellow]")
            speak("Goodbye!")
            break

        await process_turn(agent, text)

        # Speak the last text response
        last_text = next(
            (m["content"] for m in reversed(agent.messages)
             if m.get("role") == "assistant" and m.get("content", "").strip()),
            None,
        )
        if last_text:
            await loop.run_in_executor(None, speak, last_text[:500])


# ── Main async entry ───────────────────────────────────────────────

async def main_async(args: argparse.Namespace):
    if not check_prerequisites():
        sys.exit(1)

    # Create MCP server manager (unless --no-mcp)
    mcp_manager = None
    if not args.no_mcp:
        mcp_path = Path(MCP_SERVERS_CONFIG)
        if mcp_path.exists():
            mcp_manager = MCPServerManager(mcp_path)

    # Create agent
    agent = Agent(mcp_manager=mcp_manager)

    try:
        # Start MCP servers and collect tool definitions
        total_tools = await agent.start()
        console.print(f"[green]✓ Agent ready — {total_tools} tools available[/green]\n")

        # Run the chosen mode
        if args.voice:
            await run_voice_mode(agent)
        else:
            await run_text_mode(agent)
    finally:
        # Always clean up
        await agent.shutdown()


def main():
    parser = argparse.ArgumentParser(description="AI Agent — Ollama + MCP + GitHub + Viz + Voice")
    parser.add_argument("--voice", action="store_true", help="Enable voice interaction mode")
    parser.add_argument("--no-mcp", action="store_true", help="Skip connecting to external MCP servers")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
