"""Tests for visualization tools."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.visualize import (
    plot_commit_activity,
    plot_issue_stats,
    draw_dependency_graph,
    draw_flow_diagram,
    _empty_chart,
)


def test_plot_commit_activity_no_data():
    path = plot_commit_activity([], title="Test")
    assert path.exists()
    assert path.suffix == ".png"
    path.unlink()


def test_plot_commit_activity_with_data(sample_commit):
    path = plot_commit_activity([sample_commit], filename="test_activity.png")
    assert path.exists()
    assert path.name == "test_activity.png"
    path.unlink()


def test_plot_issue_stats_no_data():
    path = plot_issue_stats([], filename="test_issues_empty.png")
    assert path.exists()
    path.unlink()


def test_plot_issue_stats_with_data(sample_issue):
    path = plot_issue_stats([sample_issue], filename="test_issues.png")
    assert path.exists()
    path.unlink()


def test_draw_dependency_graph():
    nodes = [("a", "Module A"), ("b", "Module B")]
    edges = [("a", "b")]
    path = draw_dependency_graph(nodes, edges, filename="test_graph.png")
    assert path.exists()
    path.unlink()


def test_draw_flow_diagram():
    steps = [("1", "Step 1"), ("2", "Step 2")]
    path = draw_flow_diagram(steps, filename="test_flow.png")
    assert path.exists()
    path.unlink()


def test_empty_chart():
    path = _empty_chart("No data", "empty.png")
    assert path.exists()
    path.unlink()
