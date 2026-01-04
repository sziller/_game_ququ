#!/usr/bin/env python3
"""
chip_policies.py — Central dispatch for chip behavior policies (Quacks prototype)

Goal
----
Keep `rounds.py` free from hardcoded chip-color logic.
All chip behavior is categorized by WHEN it triggers:

1) Placement-step rules (during drawing):
   - determines how far the newly placed chip advances the pot marker (pos_last)
   - example: RED depends on existing ORANGE chips

2) On-place immediate effects (during drawing):
   - executed right after a chosen chip is moved PALM -> POT
   - may mutate pot/bag/palm etc.
   - example: YELLOW may remove the immediately preceding GRAY chip

3) Chip-eval phase effects (later):
   - not implemented yet, but stubs included for clean extension

Design
------
- Dispatch tables keyed by chip color for now.
- Later you can key by `type_id` if needed.
- Policy functions mutate state only through actions.py helpers.

by Sziller
"""

from __future__ import annotations

from typing import Callable, Optional, TypedDict, Any

from state import GameStateTD, ensure_player
from actions import return_chip_from_pot_to_bag


# -------------------------------------------------------------------
# Context objects (small parameter bags)
# -------------------------------------------------------------------
class PlacementCtx(TypedDict, total=False):
    # You can extend this later (round_no, events, etc.)
    pass


class OnPlaceCtx(TypedDict, total=False):
    # If you later want to pass additional knobs (e.g. allow prompts),
    # include them here.
    pass


# -------------------------------------------------------------------
# Handler signatures
# -------------------------------------------------------------------
PlacementStepFn = Callable[[GameStateTD, int, str, int, PlacementCtx], int]
OnPlaceFn = Callable[[GameStateTD, int, str, OnPlaceCtx], None]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _chip_color_value(state: GameStateTD, chip_id: str) -> tuple[str, int, str]:
    """
    Return (color, value, type_id) for a chip_id.
    """
    tid = state["chips"][chip_id]["type_id"]
    ctype = state["chip_types"][tid]
    return str(ctype["color"]), int(ctype["value"]), tid


def _count_color_in_pot(state: GameStateTD, player_id: int, color: str) -> int:
    """
    Count chips of given color currently in the player's pot.
    """
    ensure_player(state, player_id)
    cnt = 0
    for cid in state["pots"][player_id]:
        tid = state["chips"][cid]["type_id"]
        ctype = state["chip_types"][tid]
        if ctype["color"] == color:
            cnt += 1
    return cnt


# -------------------------------------------------------------------
# Placement-step rules (affect pos_last increment)
# -------------------------------------------------------------------
def _step_default_value(
    state: GameStateTD,
    player_id: int,
    chip_id: str,
    base_value: int,
    ctx: PlacementCtx,
) -> int:
    # Default: step equals the chip's printed value
    return int(base_value)


def _step_red_add_oranges(
    state: GameStateTD,
    player_id: int,
    chip_id: str,
    base_value: int,
    ctx: PlacementCtx,
) -> int:
    """
    RED rule:
    Step = base red value + number of ORANGE chips already in the pot
    (counted at the time the red chip is placed).
    """
    orange_cnt = _count_color_in_pot(state, player_id, "orange")
    return int(base_value) + int(orange_cnt)


PLACEMENT_STEP_RULES: dict[str, PlacementStepFn] = {
    "red": _step_red_add_oranges,
    # add more here later
}


def effective_placement_step(state: GameStateTD, player_id: int, placed_chip_id: str) -> int:
    """
    Compute how many board fields the placed chip advances the position tracker (pos_last).

    This is the single entry point called by `phase_drawing`.
    - Looks up chip color/value
    - Dispatches to a rule function if present
    - Falls back to default printed value
    """
    ensure_player(state, player_id)

    color, base_val, _tid = _chip_color_value(state, placed_chip_id)
    fn = PLACEMENT_STEP_RULES.get(color, _step_default_value)
    return int(fn(state, player_id, placed_chip_id, base_val, {}))


# -------------------------------------------------------------------
# On-place immediate effects (drawing phase)
# -------------------------------------------------------------------
def _on_place_yellow_may_remove_prev_gray(
    state: GameStateTD,
    player_id: int,
    placed_chip_id: str,
    ctx: OnPlaceCtx,
) -> None:
    """
    YELLOW rule:
    If the chip placed immediately before this yellow chip (in pot order) is GRAY,
    the player may remove that GRAY chip back into their bag.

    IMPORTANT:
    - This uses pot order, not pos_last.
    - Removal does not affect pos_last (handled by rounds.py tracker).
    """
    ensure_player(state, player_id)

    pot = state["pots"][player_id]
    if len(pot) < 2:
        return

    # placed chip is the last (just appended), so predecessor is -2
    prev_cid = pot[-2]
    prev_color, _prev_val, _prev_tid = _chip_color_value(state, prev_cid)
    if prev_color != "gray":
        return

    yn = input(
        f"[Player {player_id}] Yellow after gray: remove preceding gray chip {prev_cid}? [y/n]: "
    ).strip().lower()
    if yn in ("y", "yes", ""):
        return_chip_from_pot_to_bag(state, player_id, prev_cid)
        # Logging is done by the caller (rounds.py) to keep policies pure-ish.


def _on_place_blue_stub(
    state: GameStateTD,
    player_id: int,
    placed_chip_id: str,
    ctx: OnPlaceCtx,
) -> None:
    """
    BLUE rule (NOT implemented yet in this step):
    In Quacks, blue chips can cause additional draws/choices.
    This requires calling back into the drawing UI flow (palm decision loop),
    which we will add later via a callback in ctx.
    """
    return


ON_PLACE_RULES: dict[str, OnPlaceFn] = {
    "yellow": _on_place_yellow_may_remove_prev_gray,
    "blue": _on_place_blue_stub,
    # add more here later (greenred etc.)
}


def apply_on_place_effects(state: GameStateTD, player_id: int, placed_chip_id: str) -> None:
    """
    Apply immediate effects caused by placing this chip during the drawing phase.

    Entry point used by `phase_drawing` right after PALM->POT and pos_last update.
    """
    ensure_player(state, player_id)

    color, _base_val, _tid = _chip_color_value(state, placed_chip_id)
    fn = ON_PLACE_RULES.get(color)
    if not fn:
        return

    fn(state, player_id, placed_chip_id, {})


# -------------------------------------------------------------------
# Chip-eval phase (stubs for later)
# -------------------------------------------------------------------
EVAL_RULES: dict[str, Callable[[GameStateTD, int], None]] = {
    # "purple": ...,
    # "black": ...,
    # "green": ...,
}


def apply_chip_eval_effects(state: GameStateTD, player_id: int) -> None:
    """
    Stub entry point for later:
    Execute effects that happen in `phase_chip_eval` for this player.
    """
    return
