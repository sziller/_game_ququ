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
- apply game defaults and per-player starting defaults

by Sziller
"""

from __future__ import annotations

from typing import Dict, Tuple, Optional

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

    subset:
        { (color, value): count_to_move }
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
def setup_standard_starting_bag(state: GameStateTD, player_id: int) -> None:
    """
    Apply the standard Quacks starting bag for a player:

    - 4x gray (value 1)
    - 2x gray (value 2)
    - 1x gray (value 3)
    - 1x orange (value 1)
    - 1x green (value 1)
    """
    starting_subset = {
        ("gray", 1): 4,
        ("gray", 2): 2,
        ("gray", 3): 1,
        ("orange", 1): 1,
        ("green", 1): 1,
    }
    give_player_bag_subset(state, player_id, starting_subset)


# -------------------------------------------------
# Initial conditions (game + player defaults)
# -------------------------------------------------
def apply_game_defaults(state: GameStateTD) -> None:
    """
    Apply once-per-game defaults (non-player-specific).
    Keep this minimal until you actually need global config.
    """
    # Example future area:
    # state["ruleset"] = {"variant_x": False, ...}
    pass


def apply_player_defaults(
    state: GameStateTD,
    player_id: int,
    *,
    start_rubies: int = 1,
    droplet_pos: int = 0,
    potion_filled: bool = True,
    reset_coins_and_vp: bool = True,
) -> None:
    """
    Apply starting values for a player ONCE at game setup.

    This is the authoritative place for "starting rules" like:
    - starting rubies
    - starting droplet position
    - starting potion state
    """
    ensure_player(state, player_id)

    ps = state["players"][player_id]

    ps["rubies"] = int(start_rubies)
    ps["droplet_pos"] = int(droplet_pos)
    ps["potion_filled"] = bool(potion_filled)

    if reset_coins_and_vp:
        ps["coins"] = 0
        ps["victory_points"] = 0


def setup_players_base(
    state: GameStateTD,
    player_count: int,
    *,
    start_rubies: int = 1,
    droplet_pos_by_player: Optional[dict[int, int]] = None,
    potion_filled: bool = True,
) -> None:
    """
    Initialize per-player *starting stats* (rubies, droplet position, potion state, etc.)
    without touching chip inventory.

    Call this early in setup.
    """
    droplet_pos_by_player = droplet_pos_by_player or {}

    for pid in range(player_count):
        apply_player_defaults(
            state,
            pid,
            start_rubies=start_rubies,
            droplet_pos=int(droplet_pos_by_player.get(pid, 0)),
            potion_filled=potion_filled,
            reset_coins_and_vp=True,
        )


def setup_players_with_arbitrary_bags(
    state: GameStateTD,
    player_count: int,
    *,
    bag_by_player: dict[int, Dict[Tuple[str, int], int]],
) -> None:
    """
    Assign a fully custom bag recipe per player, by moving chips from box->bag.
    """
    for pid in range(player_count):
        ensure_player(state, pid)
        subset = bag_by_player.get(pid)
        if subset:
            give_player_bag_subset(state, pid, subset)


def setup_new_game(
    state: GameStateTD,
    *,
    player_count: int,
    start_rubies: int = 1,
    droplet_pos_by_player: Optional[dict[int, int]] = None,
    potion_filled: bool = True,
    use_standard_bags: bool = True,
    bag_by_player: Optional[dict[int, Dict[Tuple[str, int], int]]] = None,
) -> None:
    """
    One-call setup orchestrator.

    Use this when you want a clean entry-point setup without two separate calls.
    """
    apply_game_defaults(state)

    setup_players_base(
        state,
        player_count=player_count,
        start_rubies=start_rubies,
        droplet_pos_by_player=droplet_pos_by_player,
        potion_filled=potion_filled,
    )

    if bag_by_player is not None:
        setup_players_with_arbitrary_bags(state, player_count, bag_by_player=bag_by_player)
    elif use_standard_bags:
        for pid in range(player_count):
            setup_standard_starting_bag(state, pid)
