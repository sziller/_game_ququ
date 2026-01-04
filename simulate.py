#!/usr/bin/env python3
"""
simulate.py — game runner for Quacks round framework (manual confirmations)

Run:
    python simulate.py
"""

from __future__ import annotations

from catalog import CHIPS
from state import build_pool, validate_unique_location
from setup import setup_players_standard
from rounds import run_game


def main() -> None:
    # Build the full inventory
    state = build_pool(CHIPS)

    # Give starting bags (still your standard starter subset)
    setup_players_standard(state, player_count=2)

    # Integrity check
    validate_unique_location(state)
    print("Initial setup OK.")

    # Run full 9-round game (manual confirmations)
    run_game(state, player_count=2, seed=42, gray_limit=7)


if __name__ == "__main__":
    main()
