#!/usr/bin/env python3
"""Entry point for the AI Agent. Two modes: text (default) and voice."""

import sys
import argparse
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.config import GITHUB_TOKEN, OLLAMA_BASE_URL, OLLAMA_MODEL
from src.agent import Agent

console = Console()


def check_prerequisites() -> bool:
    """Verify Ollama is reachable and GitHub token is set (warn if not)."""
    try:
        import httpx
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        model_names = [m["name"] for m in models]
        if OLLAMA_MODEL not in model_names and f"{OLLAMA_MODEL}:latest" not in model_names:
            console.print(f"[yellow]⚠ Model '{OLLAMA_MODEL}' not found locally. Pull it: ollama pull {OLLAMA_MODEL}[/yellow]")
        else:
            console.print(f"[green]✓ Ollama connected — {OLLAMA_MODEL} available[/green]")
    except Exception as e:
        console.print(f"[red]✗ Cannot reach Ollama at {OLLAMA_BASE_URL}[/red]")
        console.print(f"  Error: {e}")
        console.print("  Make sure Ollama is running: ollama serve")
        return False

    if not GITHUB_TOKEN:
        console.print("[yellow]⚠ GITHUB_TOKEN not set. GitHub tools will fail on private repos. Set in .env[/yellow]")
    else:
        console.print("[green]✓ GitHub token configured[/green]")

    return True


def show_banner():
    console.print(Panel.fit(
        "[bold blue]AI Agent[/bold blue] — Ollama + MCP + GitHub + Viz + Voice\n"
        f"Model: {OLLAMA_MODEL}  |  Type [bold]exit[/bold] to quit",
        border_style="blue",
    ))


def run_text_mode():
    """Interactive text-based REPL with the agent."""
    agent = Agent()
    show_banner()
    console.print("[dim]Tip: Try 'Show me recent commits in user/repo' or 'Create a diagram of...'[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if not user_input.strip():
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        _process_turn(agent, user_input)


def _process_turn(agent: Agent, user_input: str):
    """Run one agent turn and display results."""
    with console.status("[bold blue]Thinking...[/bold blue]"):
        try:
            steps = agent.run(user_input)
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
            if tool.startswith("github_"):
                console.print(f"[dim]→ Called {tool} — got {_summarize(result)}[/dim]")

        elif t == "viz":
            img_path = step.get("image_path", "")
            tool = step.get("tool", "?")
            console.print(f"[bold blue]📊 {tool} → saved to: {img_path}[/bold blue]")
            # Try to display inline in supported terminals
            if img_path:
                _try_display_image(img_path)


def _summarize(result: any) -> str:
    """Short summary of a result for the log."""
    if isinstance(result, list):
        return f"{len(result)} items"
    if isinstance(result, dict):
        return f"{len(result)} keys"
    s = str(result)
    return s[:80] + "..." if len(s) > 80 else s


def _try_display_image(path: str):
    """Display image in terminal if possible (kitty, iTerm2, etc.)."""
    p = Path(path)
    if not p.exists():
        return
    # Kitty terminal
    if "KITTY_WINDOW_ID" in sys._xoptions or True:  # Try inline
        try:
            from rich.text import Text
            import base64
            with open(p, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            console.print(f"[dim]Image saved: {p}[/dim]")
        except Exception:
            console.print(f"  [dim]Image: {p}[/dim]")


def run_voice_mode():
    """Voice-based interaction loop."""
    from src.voice import record_and_transcribe, speak

    agent = Agent()
    show_banner()
    console.print("[dim]Voice mode: Press Enter to start recording, Enter again to stop[/dim]\n")

    while True:
        console.print("[bold cyan]Press Enter to speak (or type 'exit' to quit)[/bold cyan]")

        try:
            text = record_and_transcribe()
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

        _process_turn(agent, text)

        # Speak the last text response
        last_text = None
        for step in reversed(agent.messages):
            if step.get("role") == "assistant" and step.get("content", "").strip():
                last_text = step["content"]
                break
        if last_text:
            # Speak first 500 chars max
            speak(last_text[:500])


def main():
    parser = argparse.ArgumentParser(description="AI Agent — Ollama + MCP + GitHub + Viz + Voice")
    parser.add_argument("--voice", action="store_true", help="Enable voice interaction mode")
    args = parser.parse_args()

    if not check_prerequisites():
        sys.exit(1)

    if args.voice:
        run_voice_mode()
    else:
        run_text_mode()


if __name__ == "__main__":
    main()
