"""Visualization tools: progress charts and architecture diagrams."""

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import networkx as nx

from src.config import OUTPUT_DIR


def plot_commit_activity(commits: list[dict[str, Any]], title: str = "Commit Activity", filename: str = "commit_activity.png") -> Path:
    """Line chart showing commit frequency over time."""
    dates: list[datetime] = []
    for c in commits:
        date_str = c.get("commit", {}).get("author", {}).get("date", "")
        if date_str:
            dates.append(datetime.fromisoformat(date_str.replace("Z", "+00:00")))
    if not dates:
        return _empty_chart("No commit dates found", filename)

    dates.sort()
    date_counts: dict[str, int] = {}
    for d in dates:
        key = d.strftime("%Y-%m-%d")
        date_counts[key] = date_counts.get(key, 0) + 1

    sorted_days = sorted(date_counts.keys())
    counts = [date_counts[d] for d in sorted_days]
    day_objs = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_days]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(day_objs, counts, marker="o", linestyle="-", color="#0078D7")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Commits")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_issue_stats(issues: list[dict[str, Any]], title: str = "Issue Status", filename: str = "issue_stats.png") -> Path:
    """Bar chart showing open vs closed issues by label or status."""
    if not issues:
        return _empty_chart("No issue data", filename)

    states: dict[str, int] = {"open": 0, "closed": 0}
    for i in issues:
        s = i.get("state", "unknown")
        states[s] = states.get(s, 0) + 1

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = {"open": "#28A745", "closed": "#CB2431"}
    labels = list(states.keys())
    values = list(states.values())
    bar_colors = [colors.get(l, "#6A737D") for l in labels]

    ax.bar(labels, values, color=bar_colors, edgecolor="white", linewidth=1.5)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("Count")
    for i, v in enumerate(values):
        ax.text(i, v + 0.3, str(v), ha="center", fontweight="bold")

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_pr_velocity(prs: list[dict[str, Any]], title: str = "PR Activity", filename: str = "pr_velocity.png") -> Path:
    """Chart showing PR states."""
    return plot_issue_stats(prs, title=title, filename=filename)


def draw_dependency_graph(
    nodes: list[tuple[str, str]],  # (node_id, label)
    edges: list[tuple[str, str]],  # (from_node, to_node)
    title: str = "Architecture Diagram",
    filename: str = "dependency_graph.png",
) -> Path:
    """Draw a directed graph visualization."""
    G = nx.DiGraph()
    for node_id, label in nodes:
        G.add_node(node_id, label=label)
    for src, dst in edges:
        G.add_edge(src, dst)

    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)
    labels_dict = {n: G.nodes[n].get("label", n) for n in G.nodes()}

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#0078D7", node_size=2000, alpha=0.9)
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowsize=20, edge_color="#6A737D", width=1.5)
    nx.draw_networkx_labels(G, pos, labels_dict, ax=ax, font_size=10, font_color="white")

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.axis("off")

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def draw_flow_diagram(
    steps: list[tuple[str, str]],  # (step_id, description)
    filename: str = "flow_diagram.png",
) -> Path:
    """Draw a linear flow diagram of steps."""
    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.axis("off")

    y = 0
    x_positions = [i * 3 for i in range(len(steps))]
    for i, (step_id, desc) in enumerate(steps):
        x = x_positions[i]
        ax.annotate(
            "",
            xy=(x, y),
            xytext=(x, y),
            fontsize=12,
            ha="center",
            va="center",
        )
        bbox = dict(boxstyle="round,pad=0.4", facecolor="#0078D7", edgecolor="none")
        ax.text(x, y, desc, ha="center", va="center", fontsize=10, color="white", bbox=bbox)
        if i < len(steps) - 1:
            ax.annotate(
                "",
                xy=(x_positions[i + 1] - 0.5, y),
                xytext=(x_positions[i] + 0.5, y),
                arrowprops=dict(arrowstyle="->", color="#6A737D", lw=2),
            )

    ax.set_xlim(-1, x_positions[-1] + 1 if steps else 5)
    ax.set_ylim(-1, 1)
    ax.set_title("Flow Diagram", fontsize=14, fontweight="bold", pad=20)

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def _empty_chart(message: str, filename: str) -> Path:
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=14, color="#6A737D")
    ax.axis("off")
    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out
