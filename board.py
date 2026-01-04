#!/usr/bin/env python3
"""
board.py — Linear board definition for Quacks (LIST-BASED, EMPTY)

The board is a linear list of fields.

Rules:
- Field index == list index
- Player FINISHES on field = pot_sum
- Player LANDS on field = pot_sum + 1
- Rewards are taken from the LANDING field

You are expected to fill in BOARD_FIELDS with the real game data.
"""

from __future__ import annotations

from typing import List, TypedDict


# -----------------------------
# Board field definition
# -----------------------------
class BoardFieldTD(TypedDict):
    coins: int              # money gained when landing here
    victory_points: int     # VP gained when landing here
    ruby: bool              # whether a ruby is gained


# -----------------------------
# EMPTY board (index = list position)
# -----------------------------
BOARD_FIELDS: List[BoardFieldTD] = [
    # index 0
    {"coins": 0, "victory_points": 0, "ruby": False},
    # index 1
    {"coins": 0, "victory_points": 0, "ruby": False},
    # index 2
    {"coins": 0, "victory_points": 0, "ruby": False},
    # index 3
    {"coins": 0, "victory_points": 0, "ruby": False},
    # index 4
    {"coins": 0, "victory_points": 0, "ruby": False},
    # index 5
    {"coins": 0, "victory_points": 0, "ruby": True},
    # index 6
    {"coins": 6, "victory_points": 1, "ruby": False},
    # index 7
    {"coins": 7, "victory_points": 1, "ruby": False},
    # index 8
    {"coins": 8, "victory_points": 1, "ruby": False},
    # index 9
    {"coins": 9, "victory_points": 1, "ruby": True},
    # index 10
    {"coins": 10, "victory_points": 2, "ruby": False},
    # index 11
    {"coins": 11, "victory_points": 2, "ruby": False},
    # index 12
    {"coins": 12, "victory_points": 2, "ruby": False},
    # index 13
    {"coins": 13, "victory_points": 2, "ruby": True},
    # index 14
    {"coins": 14, "victory_points": 3, "ruby": False},
    # index 15
    {"coins": 15, "victory_points": 3, "ruby": False},
    # index 16
    {"coins": 15, "victory_points": 3, "ruby": True},
    # index 17
    {"coins": 16, "victory_points": 3, "ruby": False},
    # index 18
    {"coins": 16, "victory_points": 4, "ruby": False},
    # index 19
    {"coins": 17, "victory_points": 4, "ruby": False},
    # index 20
    {"coins": 17, "victory_points": 4, "ruby": True},
    # index 21
    {"coins": 18, "victory_points": 4, "ruby": False},
    # index 22
    {"coins": 18, "victory_points": 5, "ruby": False},
    # index 23
    {"coins": 19, "victory_points": 5, "ruby": False},
    # index 24
    {"coins": 19, "victory_points": 5, "ruby": True},
    # index 25
    {"coins": 20, "victory_points": 5, "ruby": False},
    # index 26
    {"coins": 20, "victory_points": 6, "ruby": False},
    # index 27
    {"coins": 21, "victory_points": 6, "ruby": False},
    # index 28
    {"coins": 21, "victory_points": 6, "ruby": True},
    # index 29
    {"coins": 22, "victory_points": 7, "ruby": False},
    # index 30
    {"coins": 22, "victory_points": 7, "ruby": True},
    # index 31
    {"coins": 23, "victory_points": 7, "ruby": False},
    # index 32
    {"coins": 23, "victory_points": 8, "ruby": False},
    # index 33
    {"coins": 24, "victory_points": 8, "ruby": False},
    # index 34
    {"coins": 24, "victory_points": 8, "ruby": True},
    # index 35
    {"coins": 25, "victory_points": 9, "ruby": False},
    # index 36
    {"coins": 25, "victory_points": 9, "ruby": True},
    # index 37
    {"coins": 26, "victory_points": 9, "ruby": False},
    {"coins": 26, "victory_points": 10, "ruby": False},
    {"coins": 27, "victory_points": 10, "ruby": False},
    {"coins": 27, "victory_points": 10, "ruby": True},
    {"coins": 28, "victory_points": 11, "ruby": False},
    {"coins": 28, "victory_points": 11, "ruby": True},
    {"coins": 29, "victory_points": 11, "ruby": False},
    {"coins": 29, "victory_points": 12, "ruby": False},
    {"coins": 30, "victory_points": 12, "ruby": False},
    {"coins": 30, "victory_points": 12, "ruby": True},
    {"coins": 31, "victory_points": 12, "ruby": False},
    {"coins": 31, "victory_points": 13, "ruby": False},
    {"coins": 32, "victory_points": 13, "ruby": False},
    {"coins": 32, "victory_points": 13, "ruby": True},
    {"coins": 33, "victory_points": 14, "ruby": False},
    {"coins": 33, "victory_points": 14, "ruby": True},
    {"coins": 33, "victory_points": 15, "ruby": False}
]


# -----------------------------
# Lookup helpers
# -----------------------------
def get_finish_field(pot_sum: int) -> BoardFieldTD:
    """
    Return the field where the player FINISHES.
    """
    return BOARD_FIELDS[pot_sum]


def get_landing_field(pot_sum: int) -> BoardFieldTD:
    """
    Return the field where the player LANDS (one field higher).
    """
    return BOARD_FIELDS[pot_sum + 1]
