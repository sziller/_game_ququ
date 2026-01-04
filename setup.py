#!/usr/bin/env python3
"""
setup.py — Quacks game setup helpers

This module is responsible for creating *legal initial game states*
on top of a freshly built pool (state.build_pool).

It does NOT:
- contain randomness
- implement gameplay actions (draw, effects, etc.)

It DOES:
- move specific chip subsets from the central box into player bags
- encode starting-bag recipes

by Sziller
"""

from __future__ import annotations

from typing import Dict, Tuple

from state import GameStateTD, ensure_player, type_id


# -------------------------------------------------
# Low-level helper: move subset from box to bag
# -------------------------------------------------
def give_player_bag_subset(
    state: GameStateTD,
    player_id: int,
    subset: Dict[Tuple[str, int], int],
) -> None:
    """
    Move a requested subset of chips from the central box into a player's bag.

    Parameters
    ----------
    state:
        Mutable game state.
    player_id:
        Target player.
    subset:
        Dict of requested chips:
            { (color, value): count_to_move }

        Example:
            {
                ("gray", 1): 7,
                ("orange", 1): 1,
                ("green", 1): 1,
            }

    Raises
    ------
    ValueError if the box does not contain enough chips.
    """
    ensure_player(state, player_id)

    # Index box contents by type_id (deterministic order)
    box_by_type: Dict[str, list[str]] = {}
    for cid in state["box"]:
        tid = state["chips"][cid]["type_id"]
        box_by_type.setdefault(tid, []).append(cid)

    for tid in box_by_type:
        box_by_type[tid].sort()

    # Execute requested moves
    for (color, value), need in subset.items():
        tid = type_id(color, int(value))
        available = box_by_type.get(tid, [])

        if len(available) < need:
            raise ValueError(
                f"Not enough chips in box for {tid}: need={need}, available={len(available)}"
            )

        for _ in range(need):
            cid = available.pop(0)

            # box -> bag
            state["box"].remove(cid)
            state["bags"][player_id].append(cid)
            state["where"][cid] = {"zone": "bag", "player": player_id}


# -------------------------------------------------
# High-level setup: standard starting bag (Quacks)
# -------------------------------------------------
def setup_standard_starting_bag(state: GameStateTD,
                                player_id: int) -> None:
    """
    Apply the standard Quacks starting bag for a player:

    - 4x gray (value 1)
    - 2x gray (value 2)
    - 1x gray (value 3)
    - 1x orange (value 1)
    - 1x green (value 1)

    This function encodes the *rule*, not randomness.
    """
    starting_subset = {
        ("gray", 1): 4,
        ("gray", 2): 2,
        ("gray", 3): 1,
        ("orange", 1): 1,
        ("green", 1): 1
    }
    give_player_bag_subset(state, player_id, starting_subset)


def setup_players_standard(
    state: GameStateTD,
    player_count: int,
) -> None:
    """
    Initialize multiple players with the standard starting bag.

    Parameters
    ----------
    state:
        Fresh game state returned by build_pool().
    player_count:
        Number of players to initialize.
    """
    for player_id in range(player_count):
        setup_standard_starting_bag(state, player_id)


# -----------------------------
# Demo usage
# -----------------------------
if __name__ == "__main__":
    state = build_pool(CHIPS)

    # Example: create Player 0 bag subset (replace with your real "start bag" rules)
    start_bag_p0 = {
        ("gray", 1): 7,
        ("orange", 1): 1,
        ("green", 1): 1,
    }
    give_player_bag_subset(state, player_id=0, subset=start_bag_p0)

    # Inspect results
    print("Player 0 bag size:", len(state["bags"][0]))
    print("Player 0 bag composition (type_id -> count):")
    print(count_container_by_type(state, state["bags"][0]))

    print("Remaining chips in box:", len(state["box"]))
