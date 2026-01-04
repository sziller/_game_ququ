#!/usr/bin/env python3
"""
actions.py — Quacks chip actions (state mutations)

This module contains *only* gameplay actions that mutate the GameState.

Zones:
- box: central supply
- bag: player hidden bag
- palm: ephemeral inspection zone (draw temporarily, then either return to bag, move to pot, or put on desktop)
- desktop: persistent side-area per player (chips can only enter from palm; can leave to bag or pot)
- pot: placed chips (affect sums/effects)

Assumptions / Dependencies
-------------------------
- Uses the data structures and helper `ensure_player()` from `state.py`.

by Sziller
"""

from __future__ import annotations

import random
from typing import Optional

from state import GameStateTD, ensure_player


# -----------------------------
# Bag -> Pot (direct draw)
# -----------------------------
def draw_from_bag(
    state: GameStateTD,
    player_id: int,
    *,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Draw ONE chip uniformly at random from the player's bag (without replacement),
    move it into the player's pot, update `where`, and return the drawn `chip_id`.
    """
    ensure_player(state, player_id)

    bag = state["bags"][player_id]
    if not bag:
        raise ValueError(f"Player {player_id} bag is empty")

    rng = rng or random

    i = rng.randrange(len(bag))
    chip_id = bag[i]
    bag[i] = bag[-1]
    bag.pop()

    state["pots"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "pot", "player": player_id}

    return chip_id


def draw_n_from_bag(
    state: GameStateTD,
    player_id: int,
    n: int,
    *,
    rng: Optional[random.Random] = None,
) -> list[str]:
    """
    Draw up to `n` chips from the player's bag, or stop early if the bag empties.
    Returns chip_ids in draw order.
    """
    drawn: list[str] = []
    for _ in range(n):
        if not state["bags"].get(player_id):
            break
        if len(state["bags"][player_id]) == 0:
            break
        drawn.append(draw_from_bag(state, player_id, rng=rng))
    return drawn


# -----------------------------
# Bag <-> Palm <-> Pot (inspection)
# -----------------------------
def draw_from_bag_to_palm(
    state: GameStateTD,
    player_id: int,
    *,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Draw ONE chip uniformly at random from the player's bag (without replacement),
    move it into the player's palm, update `where`, and return the drawn `chip_id`.
    """
    ensure_player(state, player_id)

    bag = state["bags"][player_id]
    if not bag:
        raise ValueError(f"Player {player_id} bag is empty")

    rng = rng or random

    i = rng.randrange(len(bag))
    chip_id = bag[i]
    bag[i] = bag[-1]
    bag.pop()

    state["palms"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "palm", "player": player_id}

    return chip_id


def draw_n_from_bag_to_palm(
    state: GameStateTD,
    player_id: int,
    n: int,
    *,
    rng: Optional[random.Random] = None,
) -> list[str]:
    """
    Draw up to `n` chips from bag to palm. Stops early if bag empties.
    Returns chip_ids in draw order.
    """
    ensure_player(state, player_id)
    rng = rng or random

    drawn: list[str] = []
    for _ in range(n):
        if len(state["bags"][player_id]) == 0:
            break
        drawn.append(draw_from_bag_to_palm(state, player_id, rng=rng))
    return drawn


def move_chip_palm_to_pot(state: GameStateTD, player_id: int, chip_id: str) -> None:
    """
    Move a specific chip from player's palm into player's pot.
    """
    ensure_player(state, player_id)

    palm = state["palms"][player_id]
    try:
        palm.remove(chip_id)
    except ValueError:
        raise ValueError(f"Chip {chip_id} not found in player {player_id} palm")

    state["pots"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "pot", "player": player_id}


def return_chip_palm_to_bag(state: GameStateTD, player_id: int, chip_id: str) -> None:
    """
    Return a specific chip from player's palm back into player's bag.
    """
    ensure_player(state, player_id)

    palm = state["palms"][player_id]
    try:
        palm.remove(chip_id)
    except ValueError:
        raise ValueError(f"Chip {chip_id} not found in player {player_id} palm")

    state["bags"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "bag", "player": player_id}


def return_all_palm_to_bag(state: GameStateTD, player_id: int) -> list[str]:
    """
    Return ALL chips currently in player's palm back to their bag.
    Returns the list of chip_ids returned (in the palm's current order).
    """
    ensure_player(state, player_id)

    palm = state["palms"][player_id]
    if not palm:
        return []

    returned = list(palm)
    for cid in returned:
        state["bags"][player_id].append(cid)
        state["where"][cid] = {"zone": "bag", "player": player_id}

    palm.clear()
    return returned


# -----------------------------
# Palm <-> Desktop (persistent side-area)
# -----------------------------
def move_chip_palm_to_desktop(state: GameStateTD, player_id: int, chip_id: str) -> None:
    """
    Move a chip from player's PALM to player's DESKTOP.

    Semantics:
    - Desktop is persistent across phases and rounds.
    - Chips can ONLY enter desktop from palm (enforced here by only providing this entry function).
    """
    ensure_player(state, player_id)

    palm = state["palms"][player_id]
    try:
        palm.remove(chip_id)
    except ValueError:
        raise ValueError(f"Chip {chip_id} not found in player {player_id} palm")

    state["desktops"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "desktop", "player": player_id}


def move_chip_desktop_to_bag(state: GameStateTD, player_id: int, chip_id: str) -> None:
    """
    Move a chip from player's DESKTOP back to player's BAG.
    """
    ensure_player(state, player_id)

    desk = state["desktops"][player_id]
    try:
        desk.remove(chip_id)
    except ValueError:
        raise ValueError(f"Chip {chip_id} not found on player {player_id} desktop")

    state["bags"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "bag", "player": player_id}


def move_chip_desktop_to_pot(state: GameStateTD, player_id: int, chip_id: str) -> None:
    """
    Move a chip from player's DESKTOP into player's POT.
    """
    ensure_player(state, player_id)

    desk = state["desktops"][player_id]
    try:
        desk.remove(chip_id)
    except ValueError:
        raise ValueError(f"Chip {chip_id} not found on player {player_id} desktop")

    state["pots"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "pot", "player": player_id}


# -----------------------------
# Pot -> Bag (retroactive removal)
# -----------------------------
def return_chip_from_pot_to_bag(state: GameStateTD, player_id: int, chip_id: str) -> None:
    """
    Remove a chip from player's pot (if present) and put it back into the player's bag.
    Updates `where` accordingly.

    NOTE:
    - This does NOT affect any position tracker. Position tracking is handled in rounds.py.
    """
    ensure_player(state, player_id)

    pot = state["pots"][player_id]
    try:
        pot.remove(chip_id)
    except ValueError:
        raise ValueError(f"Chip {chip_id} not found in player {player_id} pot")

    state["bags"][player_id].append(chip_id)
    state["where"][chip_id] = {"zone": "bag", "player": player_id}
    
def return_all_pot_to_bag(state: GameStateTD, player_id: int) -> list[str]:
    """
    Return ALL chips currently in player's pot back into their bag.
    Returns the list of chip_ids returned (in the pot's current order).

    Round cleanup uses this so that each round starts with an empty pot.
    """
    ensure_player(state, player_id)

    pot = state["pots"][player_id]
    if not pot:
        return []

    returned = list(pot)
    for cid in returned:
        state["bags"][player_id].append(cid)
        state["where"][cid] = {"zone": "bag", "player": player_id}

    pot.clear()
    return returned



# -----------------------------
# Utility: pot sums
# -----------------------------
def pot_sums(state: GameStateTD, player_id: int) -> tuple[int, int]:
    """
    Compute (gray_sum, total_sum) for the chips currently in player's pot.

    gray_sum: sum of values where chip_type.color == "gray"
    total_sum: sum of values across all chips in pot
    """
    ensure_player(state, player_id)

    gray_sum = 0
    total_sum = 0

    for cid in state["pots"][player_id]:
        tid = state["chips"][cid]["type_id"]
        ctype = state["chip_types"][tid]
        val = int(ctype["value"])
        total_sum += val
        if ctype["color"] == "gray":
            gray_sum += val

    return gray_sum, total_sum


def take_any_chip_of_color_from_box_to_bag(state: GameStateTD, player_id: int, *, color: str) -> str:
    """
    Take ONE chip of the given color from the central box and put it into the player's bag.
    Returns the chip_id taken.

    Used by purple events like EV13/EV14 ("take 1 purple chip").
    """
    ensure_player(state, player_id)

    # Find any chip in the box whose chip_type color matches
    for cid in sorted(state["box"]):
        tid = state["chips"][cid]["type_id"]
        ctype = state["chip_types"][tid]
        if ctype["color"] == color:
            state["box"].remove(cid)
            state["bags"][player_id].append(cid)
            state["where"][cid] = {"zone": "bag", "player": player_id}
            return cid

    raise ValueError(f"No chip of color '{color}' left in box.")
