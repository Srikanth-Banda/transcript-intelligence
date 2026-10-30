"""Transcript Intelligence pipeline (take-home). See DECISIONS.md for why each stage is built this way."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "outputs"
PROMPT_DIR = ROOT / "prompts"
