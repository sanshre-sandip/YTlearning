"""Configuration loaded from .env with sensible defaults."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_DEFAULT_REPO = os.getenv("GITHUB_DEFAULT_REPO", "")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")  # tiny | base | small | medium | large

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MCP_SERVERS_CONFIG = os.getenv("MCP_SERVERS_CONFIG", str(PROJECT_ROOT / "mcp_servers.json"))
