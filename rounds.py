#!/usr/bin/env python3
"""
rounds.py — Basic 9-round framework for Quacks (manual confirmations)

Implements:
- 9 rounds
- phase sequence
- public broadcast output + centrally recorded log
- unanimous confirmation gates between phases

Event cards:
- Purple: execute immediately after draw + confirm (one-shot, may mutate state)
- Blue: active modifier for the duration of the round (applies via hook points)

Unknown rules (rat-tails, dice, chip eval, shop, ruby trade) are stubbed for now.

This version refactors all BLUE-card hardcoded rule tweaks into dispatch tables.

by Sziller
"""

from __future__ import annotations

import random
from typing import Callable, List, Optional, Literal

from actions import pot_sums
from board import BOARD_FIELDS
from event_cards import EVENT_DECK
from state import GameStateTD, ensure_player, clear_round_ctx
from chip_policies import effective_placement_step, apply_on_place_effects


# -----------------------------
# Small infrastructure helpers
# -----------------------------
def broadcast(state: GameStateTD, msg: str) -> None:
    """Public, transparent message to all players + stored centrally."""
    print(msg)
    state["public_log"].append(msg)

def _fmt_cell(val: object, width: int, align: str = "left") -> str:
    s = str(val)
    if len(s) > width:
        s = s[: width - 1] + "…"
    if align == "right":
        return s.rjust(width)
    if align == "center":
        return s.center(width)
    return s.ljust(width)


def broadcast_player_table(state: GameStateTD, player_ids: List[int], *, title: str = "PLAYER STATE") -> None:
    """
    Print a compact table of per-player state at the beginning of each round/turn.

    This is display-only. No mutations.
    """
    # Ensure players exist so table never crashes during early setup
    for pid in player_ids:
        ensure_player(state, pid)

    # Columns you likely care about for testing
    headers = [
        ("PID", 3, "right"),
        ("VP", 4, "right"),
        ("Coins", 6, "right"),
        ("Rubies", 6, "right"),
        ("Droplet", 7, "right"),
        ("Potion", 6, "center"),   # NEW
        ("Bag", 4, "right"),
        ("Palm", 5, "right"),
        ("Pot", 4, "right"),
        ("Desktop", 7, "right"),
    ]

    # Read counts safely even if you haven't added desktop everywhere yet
    def _desktop_len(pid: int) -> int:
        # if you later add state["desktops"][pid], this will show it
        desks = state.get("desktops")  # type: ignore[typeddict-item]
        if isinstance(desks, dict):
            return len(desks.get(pid, []))
        return 0

    def _potion_str(pid: int) -> str:
        ps = state["players"][pid]
        filled = bool(ps.get("potion_filled", True))  # default True for robustness
        return "FULL" if filled else "EMPTY"

    # Build table lines
    sep = " | "
    header_line = sep.join(_fmt_cell(h, w, "center") for (h, w, _) in headers)
    rule_line = "-+-".join("-" * w for (_, w, _) in headers)

    rows: List[str] = []
    for pid in player_ids:
        ps = state["players"][pid]
        row_vals = [
            pid,
            ps.get("victory_points", 0),
            ps.get("coins", 0),
            ps.get("rubies", 0),
            ps.get("droplet_pos", 0),
            _potion_str(pid),                  # NEW
            len(state["bags"].get(pid, [])),
            len(state.get("palms", {}).get(pid, [])),
            len(state["pots"].get(pid, [])),
            _desktop_len(pid),
        ]
        row = sep.join(_fmt_cell(v, w, a) for (v, (_, w, a)) in zip(row_vals, headers))
        rows.append(row)

    broadcast(state, f"\n[{title}]")
    broadcast(state, header_line)
    broadcast(state, rule_line)
    for r in rows:
        broadcast(state, r)



def confirm_all_players(state: GameStateTD, player_ids: List[int], prompt: str) -> None:
    """
    Unanimous confirmation gate.
    For now: sequential prompts in terminal.
    """
    broadcast(state, f"\n[CONFIRM-ALL] {prompt}")
    for pid in player_ids:
        while True:
            ans = input(f"Player {pid} confirm? [y]: ").strip().lower()
            if ans in ("y", "yes", ""):
                break
            print("Please confirm with 'y' (or just press Enter).")


def landing_rewards_for_total_sum(total_sum: int) -> tuple[int, int, bool, int]:
    """
    Uses BOARD_FIELDS list. If incomplete, clamps to last field or returns zeros if empty.
    Returns: (coins, vp, ruby, landing_index)
    """
    landing_index = total_sum + 1

    if not BOARD_FIELDS:
        return 0, 0, False, landing_index

    if landing_index < 0:
        landing_index = 0
    if landing_index >= len(BOARD_FIELDS):
        landing_index = len(BOARD_FIELDS) - 1

    f = BOARD_FIELDS[landing_index]
    return int(f["coins"]), int(f["victory_points"]), bool(f["ruby"]), landing_index

def count_color_in_pot(state: GameStateTD, pid: int, color: str) -> int:
    cnt = 0
    for cid in state["pots"][pid]:
        tid = state["chips"][cid]["type_id"]
        ctype = state["chip_types"][tid]
        if ctype["color"] == color:
            cnt += 1
    return cnt


def effective_placement_step(state: GameStateTD, pid: int, chip_id: str) -> int:
    """
    Return how many fields the freshly drawn chip advances the last position.

    Default: chip value
    Example rule (prototype per your description):
    - Red chips: advance = base_value + (#orange chips already in pot at draw time)
    """
    tid = state["chips"][chip_id]["type_id"]
    ctype = state["chip_types"][tid]
    base = int(ctype["value"])
    color = ctype["color"]

    if color == "red":
        orange_cnt = count_color_in_pot(state, pid, "orange")
        return base + orange_cnt

    return base


# -----------------------------
# Blue event dispatch tables
# -----------------------------
PurpleEffectFn = Callable[[GameStateTD, dict, List[int], random.Random], None]
PURPLE_EFFECTS: dict[str, PurpleEffectFn] = {}

# Context types: tiny “parameter bags” passed to handlers
class DrawContext:
    __slots__ = ("default_gray_limit",)

    def __init__(self, default_gray_limit: int):
        self.default_gray_limit = default_gray_limit


class RubiesContext:
    __slots__ = ("base_ruby_gain", "landed_on_ruby")

    def __init__(self, base_ruby_gain: int, landed_on_ruby: bool):
        self.base_ruby_gain = base_ruby_gain
        self.landed_on_ruby = landed_on_ruby


class ScoreContext:
    __slots__ = ("add_coins", "add_vp", "landed_on_ruby")

    def __init__(self, add_coins: int, add_vp: int, landed_on_ruby: bool):
        self.add_coins = add_coins
        self.add_vp = add_vp
        self.landed_on_ruby = landed_on_ruby


# Handler signatures
BlueDrawRuleFn = Callable[[GameStateTD, dict, DrawContext], int]
BlueRubiesRuleFn = Callable[[GameStateTD, dict, int, RubiesContext], int]
BlueScoreRuleFn = Callable[[GameStateTD, dict, int, ScoreContext], tuple[int, int]]


def _blue_draw_ev20_living_in_luxury(state: GameStateTD, card: dict, ctx: DrawContext) -> int:
    # EV20: threshold for white chips raised from 7 to 9 (we map this to explosion limit in current prototype)
    return 9


def _blue_rubies_ev14_shining_extra_bright(state: GameStateTD, card: dict, pid: int, ctx: RubiesContext) -> int:
    # EV14: if you reach a scoring field with a ruby -> extra ruby
    if ctx.landed_on_ruby:
        return ctx.base_ruby_gain + 1
    return ctx.base_ruby_gain


def _blue_score_ev23_lucky_devil(state: GameStateTD, card: dict, pid: int, ctx: ScoreContext) -> tuple[int, int]:
    # EV23: if you reach a scoring field with a ruby -> extra 2 victory points
    add_coins = ctx.add_coins
    add_vp = ctx.add_vp + (2 if ctx.landed_on_ruby else 0)
    return add_coins, add_vp


# Dispatch tables (card_id -> handler)
BLUE_DRAW_RULES: dict[str, BlueDrawRuleFn] = {
    "EV20": _blue_draw_ev20_living_in_luxury,
}

BLUE_RUBIES_RULES: dict[str, BlueRubiesRuleFn] = {
    "EV14": _blue_rubies_ev14_shining_extra_bright,
}

BLUE_SCORE_RULES: dict[str, BlueScoreRuleFn] = {
    "EV23": _blue_score_ev23_lucky_devil,
}


def get_active_blue_card(state: GameStateTD) -> Optional[dict]:
    """Return active blue card dict, if any and if it is blue."""
    card = state.get("active_blue_event")
    if not card:
        return None
    if card.get("color") != "blue":
        return None
    return card


def apply_blue_draw_rule(state: GameStateTD, default_gray_limit: int) -> int:
    """
    Return effective draw explosion limit, possibly modified by active blue card.
    """
    card = get_active_blue_card(state)
    if not card:
        return default_gray_limit

    card_id = card.get("card_id", "")
    fn = BLUE_DRAW_RULES.get(card_id)
    if not fn:
        return default_gray_limit

    return fn(state, card, DrawContext(default_gray_limit))


def apply_blue_rubies_rule(state: GameStateTD, pid: int, base_ruby_gain: int, landed_on_ruby: bool) -> int:
    """
    Return ruby gain for this player, possibly modified by active blue card.
    """
    card = get_active_blue_card(state)
    if not card:
        return base_ruby_gain

    card_id = card.get("card_id", "")
    fn = BLUE_RUBIES_RULES.get(card_id)
    if not fn:
        return base_ruby_gain

    return fn(state, card, pid, RubiesContext(base_ruby_gain, landed_on_ruby))


def apply_blue_score_rule(state: GameStateTD, pid: int, add_coins: int, add_vp: int, landed_on_ruby: bool) -> tuple[int, int]:
    """
    Return (coins, vp) delta, possibly modified by active blue card.
    """
    card = get_active_blue_card(state)
    if not card:
        return add_coins, add_vp

    card_id = card.get("card_id", "")
    fn = BLUE_SCORE_RULES.get(card_id)
    if not fn:
        return add_coins, add_vp

    return fn(state, card, pid, ScoreContext(add_coins, add_vp, landed_on_ruby))


# -----------------------------
# Event card timing + hooks
# -----------------------------
def execute_purple_event_now(state: GameStateTD, card: dict, player_ids: List[int], rng: random.Random) -> None:
    """
    Execute purple card effect immediately after draw+confirm.

    Runtime behavior:
    - Dispatch by card_id using PURPLE_EFFECTS.
    - The handler is responsible for any per-player prompting or global confirmation.
    - `scope` remains useful metadata for logging, but does not drive execution here.
    """
    card_id = card.get("card_id", "?")
    title = card.get("title", "")
    scope = card.get("scope") or "global"

    broadcast(state, f"\n[PURPLE EVENT] Executing {card_id} — {title} (scope={scope}).")

    fn = PURPLE_EFFECTS.get(card_id)
    if not fn:
        # Fallback: no implementation yet.
        broadcast(state, f"[PURPLE EVENT] No implementation registered for {card_id}. (stub)")
        # Optional: keep your previous “manual resolve” behavior as a placeholder:
        if scope == "per_player":
            for pid in player_ids:
                input(f"Player {pid}: resolve {card_id} manually, then press Enter...")
        else:
            confirm_all_players(state, player_ids, f"Resolve {card_id} (global) manually. Confirm when done.")
        broadcast(state, f"[PURPLE EVENT] Completed (stub) for {card_id}.")
        return

    # Real effect implementation
    fn(state, card, player_ids, rng)

    broadcast(state, f"[PURPLE EVENT] Completed execution for {card_id}.")

def _purple_ev12_alms(state: GameStateTD, card: dict, player_ids: List[int], rng: random.Random) -> None:
    # The player(s) with the fewest rubies receive(s) 1 ruby.
    rubies_by_pid = {pid: int(state["players"][pid]["rubies"]) for pid in player_ids}
    min_r = min(rubies_by_pid.values())
    targets = [pid for pid, r in rubies_by_pid.items() if r == min_r]

    for pid in targets:
        state["players"][pid]["rubies"] += 1

    broadcast(state, f"[EV12] Alms: fewest rubies={min_r} -> {targets} gain +1 ruby.")

def _purple_ev13_14_choose_wisely(state: GameStateTD, card: dict, player_ids: List[int], rng: random.Random) -> None:
    # Choose: Move droplet +2 OR take 1 purple chip (we'll implement the purple chip transfer in actions.py)
    from actions import take_any_chip_of_color_from_box_to_bag  # you will add this

    for pid in player_ids:
        broadcast(state, f"[{card['card_id']}] Player {pid} choice.")
        while True:
            choice = input(f"Player {pid}: (d)roplet +2 OR take (p)urple chip? [d/p]: ").strip().lower()
            if choice in ("d", ""):
                state["players"][pid]["droplet_pos"] = int(state["players"][pid].get("droplet_pos", 0)) + 2
                broadcast(state, f"Player {pid}: droplet_pos increased to {state['players'][pid]['droplet_pos']}.")
                break
            if choice in ("p", "purple"):
                cid = take_any_chip_of_color_from_box_to_bag(state, pid, color="purple")
                broadcast(state, f"Player {pid}: took purple chip {cid} from box to bag.")
                break
            print("Please enter 'd' or 'p'.")


PURPLE_EFFECTS.update({
    "EV12": _purple_ev12_alms,
    "EV13": _purple_ev13_14_choose_wisely,
    "EV14": _purple_ev13_14_choose_wisely,
})



def note_blue_event_active(state: GameStateTD, card: dict, round_no: int) -> None:
    """
    Mark blue card as active for the duration of this round.
    The effect is applied via dispatch tables inside later phases.
    """
    state["active_blue_event"] = card
    card_id = card.get("card_id", "?")
    title = card.get("title", "")
    broadcast(state, f"\n[BLUE EVENT] {card_id} — {title} is ACTIVE for the duration of round {round_no}.")


def blue_event_hook(state: GameStateTD, phase_name: str) -> None:
    """
    Transparent hook point (log-only). The actual logic happens via dispatch tables.
    """
    card = get_active_blue_card(state)
    if not card:
        return
    card_id = card.get("card_id", "?")
    title = card.get("title", "")
    broadcast(state, f"[BLUE EVENT] {card_id} — {title} is active for phase: {phase_name}.")


# -----------------------------
# Phase stubs (replace later)
# -----------------------------
def phase_start(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    # Clear per-round event pointers at round start
    state["current_event"] = None
    state["active_blue_event"] = None

    broadcast(state, f"\n==============================")
    broadcast(state, f"ROUND {round_no}/9 — START")
    broadcast(state, f"==============================")

    # NEW: show full player table at start of round
    broadcast_player_table(state, player_ids, title=f"PLAYER STATE — Round {round_no} start")


def phase_event_card(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    """
    Draw one event card randomly WITHOUT replacement.
    - Purple: execute immediately after unanimous confirmation (one-shot)
    - Blue: becomes active for duration of the round (applied via dispatch tables)
    """
    if not state["event_deck"]:
        state["current_event"] = None
        broadcast(state, f"\n[EVENT CARD] Round {round_no}: No cards left in deck.")
        confirm_all_players(state, player_ids, "No event card available. Proceed?")
        return

    idx = rng.randrange(len(state["event_deck"]))
    card = state["event_deck"].pop(idx)

    state["current_event"] = card
    state["event_discard"].append(card)

    card_id = card.get("card_id", "?")
    title = card.get("title", "")
    color = card.get("color", "?")
    desc = card.get("description", "")

    broadcast(state, f"\n[EVENT CARD] Round {round_no}: Drew {card_id} ({color}) — {title}")
    if desc:
        broadcast(state, f"[EVENT CARD] Description: {desc}")

    confirm_all_players(state, player_ids, "Event card acknowledged.")

    if color == "purple":
        execute_purple_event_now(state, card, player_ids, rng)
        confirm_all_players(state, player_ids, "Purple event resolved. Proceed to rat-tails?")
    elif color == "blue":
        note_blue_event_active(state, card, round_no)
        confirm_all_players(state, player_ids, "Blue event is active. Proceed to rat-tails?")
    else:
        broadcast(state, f"[EVENT CARD] WARNING: Unknown event color '{color}'. No timing applied.")
        confirm_all_players(state, player_ids, "Proceed to rat-tails?")


def phase_rat_tails(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    """
    Determine per-player rat-tail count for this round.
    This value is transient and MUST be recomputed every round.
    """
    broadcast(state, "\n[RAT-TAILS] Enter per-player rat-tail counts for this round (stub/manual).")
    rt: dict[int, int] = {}

    for pid in player_ids:
        ensure_player(state, pid)
        while True:
            s = input(f"Player {pid} rat-tails this round (integer, default 0): ").strip()
            if s == "":
                rt[pid] = 0
                break
            try:
                v = int(s)
                if v < 0:
                    print("Please enter 0 or a positive integer.")
                    continue
                rt[pid] = v
                break
            except ValueError:
                print("Please enter an integer (e.g., 0, 1, 2).")

    

    state["round_ctx"]["rat_tails"] = rt
    broadcast(state, f"[RAT-TAILS] Stored: {rt}")

    # NEW: show table right before the "proceed to drawing" confirmation
    broadcast_player_table(state, player_ids, title=f"PLAYER STATE — before DRAWING (Round {round_no})")
    
    confirm_all_players(state, player_ids, "Rat-tails done. Proceed to drawing phase?")


def phase_drawing(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    """
    Drawing is local interaction, but outcomes are transparent.

    Drawing now happens in two steps:
      1) Draw N chips to PALM (inspection zone)
      2) Decide:
         - Place ONE chosen chip from palm -> pot, then resolve placement + on-draw effects
         - OR return ALL palm chips to bag (rare; controlled by a flag)

    In all cases:
      - After the decision, any remaining chips in palm are returned to bag.
      - Then we proceed to the next drawing prompt (unless exploded).

    Tracked values:
    - gray_sum: sum of gray chips currently in pot (explosion)
    - chip_sum: sum of all chips currently in pot (may go DOWN if chips removed)
    - pos_last: board position of last placed chip (monotonic; does NOT go down)
    - pos_start: droplet_pos + rat_tails (per-player, per-round start)
    """
    gray_limit = int(state["round_ctx"].get("gray_limit", 7))
    trackers = state["round_ctx"].setdefault("draw_trackers", {})

    ev15_used = state["round_ctx"].setdefault("ev15_first_white_return_used", {})

    # rat-tails are round-local; tolerate missing key for robustness
    rat_tails_map = state["round_ctx"].get("rat_tails", {})

    # Rule toggle: returning drawn palm chips back to bag is rarely allowed.
    # Default: forbidden. Enable per round/effect by setting:
    #   state["round_ctx"]["allow_return_all_from_palm"] = True
    allow_return_all = bool(state["round_ctx"].get("allow_return_all_from_palm", False))

    # Blue event can modify explosion threshold (gray_limit)
    effective_gray_limit = apply_blue_draw_rule(state, gray_limit)
    if effective_gray_limit != gray_limit:
        broadcast(state, f"\n[DRAWING] Explosion limit modified by blue event: {gray_limit} -> {effective_gray_limit}")

    broadcast(state, "\n[DRAWING] Players draw individually. Busts are public.")
    results: dict[int, dict] = {}

    from actions import (
        draw_n_from_bag_to_palm,
        move_chip_palm_to_pot,
        return_all_palm_to_bag,
        return_chip_from_pot_to_bag,
        pot_sums,
    )

    def landing_rewards_for_position(pos_last: int) -> tuple[int, int, bool, int]:
        """
        Your current board helper is based on 'total_sum' and uses total_sum+1 as landing.
        Here we already track a true board position (pos_last).
        So: landing field index == pos_last (clamped).
        Returns: (coins, vp, ruby, landing_index).
        """
        landing_index = pos_last

        if not BOARD_FIELDS:
            return 0, 0, False, landing_index

        if landing_index < 0:
            landing_index = 0
        if landing_index >= len(BOARD_FIELDS):
            landing_index = len(BOARD_FIELDS) - 1

        f = BOARD_FIELDS[landing_index]
        return int(f["coins"]), int(f["victory_points"]), bool(f["ruby"]), landing_index

    for pid in player_ids:
        ensure_player(state, pid)
        broadcast(state, f"\n--- Player {pid} drawing starts ---")

        exploded = False

        # per-player start position
        droplet_pos = int(state["players"][pid].get("droplet_pos", 0))
        rat_tails = int(rat_tails_map.get(pid, 0))
        pos_start = droplet_pos + rat_tails

        # monotonic position tracker
        pos_last = pos_start

        trackers[pid] = {
            "pos_start": pos_start,
            "pos_last": pos_last,
            "droplet_pos": droplet_pos,
            "rat_tails": rat_tails,
        }

        broadcast(state, f"[Player {pid}] START POS | droplet_pos={droplet_pos} + rat_tails={rat_tails} => pos_start={pos_start}")

        while True:
            ans = input(f"[Player {pid}] Continue drawing? [y/n]: ").strip().lower()
            if ans in ("n", "no"):
                broadcast(state, f"[Player {pid}] stops drawing voluntarily.")
                # invariant: palm must be empty
                if state["palms"][pid]:
                    returned = return_all_palm_to_bag(state, pid)
                    broadcast(state, f"[Player {pid}] SAFETY: Returned leftover PALM chips to bag: {returned}")
                break
            if ans not in ("y", "yes"):
                print("Please enter 'y' or 'n'.")
                continue

            # --- Step 1: draw N chips to PALM ---
            while True:
                s = input(f"[Player {pid}] How many chips to draw to PALM (default 1)? ").strip()
                if s == "":
                    n_palm = 1
                    break
                try:
                    n_palm = int(s)
                    if n_palm <= 0:
                        print("Please enter a positive integer (>=1).")
                        continue
                    break
                except ValueError:
                    print("Please enter an integer (e.g., 1, 2, 3).")

            drawn = draw_n_from_bag_to_palm(state, pid, n_palm, rng=rng)

            if not drawn:
                broadcast(state, f"[Player {pid}] Bag is empty. No chip drawn.")
                if state["palms"][pid]:
                    returned = return_all_palm_to_bag(state, pid)
                    broadcast(state, f"[Player {pid}] SAFETY: Returned leftover PALM chips to bag: {returned}")
                break

            # show palm content
            palm_list = list(state["palms"][pid])
            palm_options = []
            for idx, cid in enumerate(palm_list):
                tid = state["chips"][cid]["type_id"]
                ctype = state["chip_types"][tid]
                palm_options.append(
                    f"{idx} -> {ctype['color']} v={int(ctype['value'])}"
                )

            broadcast(state, f"[Player {pid}] PALM (select by NUMBER):")

            for idx, cid in enumerate(palm_list):
                tid = state["chips"][cid]["type_id"]
                ctype = state["chip_types"][tid]
                broadcast(
                    state,
                    f"  [{idx}] {ctype['color']} v={int(ctype['value'])} ({cid})"
                )

            # --- Step 2: decision ---
            # - place exactly one
            # - OR return all (if allowed)
            if allow_return_all:
                while True:
                    choice = input(f"[Player {pid}] Action: (p)lace one to pot OR (r)eturn all to bag? [p/r]: ").strip().lower()
                    if choice in ("p", "place", ""):
                        choice = "p"
                        break
                    if choice in ("r", "return"):
                        choice = "r"
                        break
                    print("Please enter 'p' or 'r'.")
            else:
                # forbidden branch (still explicit)
                broadcast(
                    state,
                    f"[Player {pid}] Action: place ONE chip to pot "
                    f"(return-all is NOT allowed now)."
                )
                choice = "p"

            if choice == "r":
                returned = return_all_palm_to_bag(state, pid)
                broadcast(state, f"[Player {pid}] Returned palm chips to bag: {returned}")
                # proceed to next drawing prompt
                continue

            # choice == "p": place exactly one from palm
            broadcast(state, f"[Player {pid}] Choose chip to PLACE:")
            for line in palm_options:
                broadcast(state, f"  {line}")

            while True:
                s = input("Selection: ").strip()
                try:
                    idx = int(s)
                    if 0 <= idx < len(palm_list):
                        placed_cid = palm_list[idx]
                        break
                    else:
                        print("Index out of range.")
                except ValueError:
                    print("Please enter a valid integer key.")

            # move chosen chip to pot
            move_chip_palm_to_pot(state, pid, placed_cid)

            # ALWAYS flush remaining palm back to bag
            if state["palms"][pid]:
                returned_rest = return_all_palm_to_bag(state, pid)
                broadcast(state, f"[Player {pid}] Returned remaining PALM chips to bag: {returned_rest}")
            
            # --- POTION RULE (new) ---
            # If you PLACE a gray chip, have NOT exploded, and potion is filled:
            # you may use the potion to undo this placement (return just placed gray chip to bag)
            placed_tid = state["chips"][placed_cid]["type_id"]
            placed_ctype = state["chip_types"][placed_tid]
            placed_color = placed_ctype["color"]

            if placed_color == "gray" and (not exploded) and bool(state["players"][pid].get("potion_filled", True)):
                yn = input(
                    f"[Player {pid}] Potion available: you placed a GRAY chip ({placed_cid}). "
                    f"Use potion to put it back into the bag? [y/n]: "
                ).strip().lower()

                if yn in ("y", "yes", ""):
                    # undo placement
                    return_chip_from_pot_to_bag(state, pid, placed_cid)
                    state["players"][pid]["potion_filled"] = False
                    broadcast(
                        state,
                        f"[Player {pid}] POTION USED: returned just placed gray chip {placed_cid} back to bag. "
                        f"Potion is now EMPTY."
                    )
                    # Important: do NOT advance pos_last, do NOT apply on-draw effects for this chip.
                    # Proceed to next iteration (player will be prompted to draw again as usual).
                    continue
            
            # --- placement step + pos tracking ---
            step = effective_placement_step(state, pid, placed_cid)
            pos_last += int(step)
            trackers[pid]["pos_last"] = pos_last

            tid = state["chips"][placed_cid]["type_id"]
            ctype = state["chip_types"][tid]
            base_val = int(ctype["value"])
            color = ctype["color"]

            # EV15 (blue): first gray chip you draw this round may be returned to bag
            active = get_active_blue_card(state)
            if active and active.get("card_id") == "EV15":
                if color == "gray" and not bool(ev15_used.get(pid, False)):
                    yn = input(
                        f"[Player {pid}] EV15: Return this first gray chip {placed_cid} to bag? [y/n]: ").strip().lower()
                    if yn in ("y", "yes", ""):
                        return_chip_from_pot_to_bag(state, pid, placed_cid)
                        ev15_used[pid] = True
                        broadcast(state, f"[Player {pid}] EV15: returned {placed_cid} to bag (effect consumed).")
                        # IMPORTANT: This does NOT change pos_last (monotonic), by your design.
                    else:
                        ev15_used[pid] = True  # effect consumed even if declined

            # --- immediate ON-DRAW effects (policy dispatch) ---
            apply_on_place_effects(state, pid, placed_cid)

            # sums from CURRENT pot contents
            gray_sum, chip_sum = pot_sums(state, pid)

            # landing rewards from POSITION (pos_last), not from chip_sum
            coins, vp, ruby, landing_index = landing_rewards_for_position(pos_last)

            broadcast(
                state,
                f"[Player {pid}] PLACED {placed_cid} ({tid}, {color}, base_v={base_val}, step={step}) | "
                f"GRAY_SUM={gray_sum} CHIP_SUM={chip_sum} | "
                f"POS_START={pos_start} POS_LAST={pos_last} => "
                f"LAND={landing_index}: coins={coins}, vp={vp}, ruby={'YES' if ruby else 'NO'}"
            )

            # explosion check
            if gray_sum > effective_gray_limit:
                exploded = True
                broadcast(state, f"[Player {pid}] EXPLODED: GRAY_SUM {gray_sum} > {effective_gray_limit}. Drawing stops.")
                # invariant: palm empty
                if state["palms"][pid]:
                    returned = return_all_palm_to_bag(state, pid)
                    broadcast(state, f"[Player {pid}] SAFETY: Returned leftover PALM chips to bag: {returned}")
                break

        # finalize player result snapshot
        gray_sum, chip_sum = pot_sums(state, pid)
        coins, vp, ruby, landing_index = landing_rewards_for_position(pos_last)

        results[pid] = {
            "droplet_pos": droplet_pos,
            "rat_tails": rat_tails,
            "pos_start": pos_start,
            "pos_last": pos_last,
            "gray_sum": gray_sum,
            "chip_sum": chip_sum,
            "exploded": exploded,
            "landing_index": landing_index,
            "landing_coins": coins,
            "landing_vp": vp,
            "landing_ruby": ruby,
        }

        broadcast(
            state,
            f"[Player {pid}] DRAW RESULT | POS_START={pos_start} POS_LAST={pos_last} "
            f"CHIP_SUM={chip_sum} GRAY_SUM={gray_sum} "
            f"EXPLODED={'YES' if exploded else 'NO'} | "
            f"LAND={landing_index} coins={coins} vp={vp} ruby={'YES' if ruby else 'NO'}"
        )

        # hard invariant at end of player's drawing: palm must be empty
        if state["palms"][pid]:
            returned = return_all_palm_to_bag(state, pid)
            broadcast(state, f"[Player {pid}] SAFETY: Returned leftover PALM chips to bag: {returned}")

    state["round_ctx"]["drawing_results"] = results
    confirm_all_players(state, player_ids, "Drawing done for all. Proceed to winner/dice phase?")




def phase_winner_and_dice(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    blue_event_hook(state, "winner_and_dice")
    results = state["round_ctx"]["drawing_results"]

    # Determine winners (same as before)
    eligible = [(pid, results[pid]["pos_last"]) for pid in player_ids if not results[pid]["exploded"]]
    if not eligible:
        eligible = [(pid, results[pid]["pos_last"]) for pid in player_ids]

    max_pos = max(p for _, p in eligible)
    winners = [pid for pid, p in eligible if p == max_pos]

    broadcast(state, f"\n[WINNER] Winner(s) of draw-phase: {winners} (max POS_LAST={max_pos})")

    # Dice results are round-local (useful for debugging/tests)
    dice_results = state["round_ctx"].setdefault("dice_results", {})

    # Dice faces:
    # 1: +1 VP
    # 2: +1 VP
    # 3: +2 VP
    # 4: +1 orange chip from box -> bag
    # 5: +1 ruby
    # 6: droplet +1
    from actions import take_any_chip_of_color_from_box_to_bag

    for pid in winners:
        roll = rng.randint(1, 6)

        # Apply effect
        effect_desc = ""
        if roll in (1, 2):
            state["players"][pid]["victory_points"] += 1
            effect_desc = "Gain +1 VP"
        elif roll == 3:
            state["players"][pid]["victory_points"] += 2
            effect_desc = "Gain +2 VP"
        elif roll == 4:
            try:
                cid = take_any_chip_of_color_from_box_to_bag(state, pid, color="orange")
                effect_desc = f"Take 1 orange chip from box → bag ({cid})"
            except ValueError:
                effect_desc = "Take 1 orange chip from box → bag (NONE AVAILABLE)"
        elif roll == 5:
            state["players"][pid]["rubies"] += 1
            effect_desc = "Gain +1 ruby"
        elif roll == 6:
            state["players"][pid]["droplet_pos"] = int(state["players"][pid].get("droplet_pos", 0)) + 1
            effect_desc = f"Move droplet +1 (now {state['players'][pid]['droplet_pos']})"

        dice_results[pid] = {"roll": roll, "effect": effect_desc}

        broadcast(state, f"[DICE] Player {pid} rolls {roll}/6 → {effect_desc}")

    confirm_all_players(state, player_ids, "Winner/dice resolved. Proceed to chip evaluation?")



def phase_chip_eval(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    blue_event_hook(state, "chip_eval")

    broadcast(state, "\n[CHIP EVAL] (stub) Pot-content effects evaluated locally for each player.")
    for pid in player_ids:
        input(f"Player {pid}: press Enter when chip-eval done...")
    confirm_all_players(state, player_ids, "Chip eval done. Proceed to ruby distribution?")


def phase_rubies(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    """
    Ruby distribution phase (simple core rule, hook kept).

    Rule (no modifiers for now):
    - If a player ended the drawing phase on a ruby field (landing_ruby == True),
      they gain exactly +1 ruby.
    - Otherwise, they gain 0.

    Input:
    - state["round_ctx"]["drawing_results"][pid]["landing_ruby"] : bool

    Effects:
    - Updates: state["players"][pid]["rubies"]
    - Logs: who gained a ruby and new totals
    """
    # Keep the phase hook for transparency/future blue-card phase awareness
    blue_event_hook(state, "rubies")

    results = state["round_ctx"]["drawing_results"]

    broadcast(state, "\n[RUBIES] Distributing rubies based on landing fields.")

    for pid in player_ids:
        ensure_player(state, pid)

        landed_on_ruby = bool(results[pid].get("landing_ruby", False))
        gain = 1 if landed_on_ruby else 0  # no event modifiers yet

        if gain:
            state["players"][pid]["rubies"] += gain
            broadcast(
                state,
                f"Player {pid}: landed on RUBY field -> +{gain} ruby "
                f"(now {state['players'][pid]['rubies']})."
            )
        else:
            broadcast(
                state,
                f"Player {pid}: no ruby field -> +0 rubies "
                f"(still {state['players'][pid]['rubies']})."
            )

    confirm_all_players(state, player_ids, "Rubies resolved. Proceed to VP/coins accounting?")



def phase_vp_and_coins(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    blue_event_hook(state, "vp_and_coins")
    results = state["round_ctx"]["drawing_results"]

    broadcast(state, "\n[SCORING] Adding landing rewards (coins + victory points). Transparent.")

    for pid in player_ids:
        add_coins = results[pid]["landing_coins"]
        add_vp = results[pid]["landing_vp"]

        add_coins, add_vp = apply_blue_score_rule(
            state,
            pid,
            add_coins,
            add_vp,
            results[pid]["landing_ruby"],
        )

        state["players"][pid]["coins"] += add_coins
        state["players"][pid]["victory_points"] += add_vp

        broadcast(
            state,
            f"Player {pid}: +{add_coins} coins, +{add_vp} VP "
            f"=> coins={state['players'][pid]['coins']}, VP={state['players'][pid]['victory_points']}"
        )

    confirm_all_players(state, player_ids, "Scoring acknowledged. Proceed to purchase phase?")


def phase_purchase(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    blue_event_hook(state, "purchase")

    broadcast(state, "\n[SHOP] (stub) Purchasing is local; results are shown to all.")
    for pid in player_ids:
        msg = input(f"Player {pid}: enter purchase summary (or empty) to broadcast: ").strip()
        if msg:
            broadcast(state, f"Player {pid} purchase: {msg}")
    confirm_all_players(state, player_ids, "Purchases done. Proceed to ruby trade phase?")


def phase_ruby_trade(state: GameStateTD, round_no: int, player_ids: List[int], rng: random.Random) -> None:
    blue_event_hook(state, "ruby_trade")

    broadcast(state, "\n[RUBY TRADE] Spend 2 rubies to either:")
    broadcast(state, "  - refill your potion (ONLY if empty)")
    broadcast(state, "  - move your droplet forward by +1 (repeatable)")
    broadcast(state, "Enter actions per player; results are broadcast to all.")

    RUBY_COST = 2

    for pid in player_ids:
        ensure_player(state, pid)

        while True:
            rubies = int(state["players"][pid]["rubies"])
            droplet_pos = int(state["players"][pid].get("droplet_pos", 0))
            potion_filled = bool(state["players"][pid].get("potion_filled", True))

            broadcast(
                state,
                f"\nPlayer {pid} status: rubies={rubies}, droplet_pos={droplet_pos}, "
                f"potion={'FILLED' if potion_filled else 'EMPTY'}"
            )

            if rubies < RUBY_COST:
                broadcast(state, f"Player {pid}: not enough rubies to trade (need {RUBY_COST}).")
                break

            # Menu
            print(f"Player {pid} options:")
            print("  [d] Spend 2 rubies -> droplet +1")
            print("  [p] Spend 2 rubies -> refill potion (only if empty)")
            print("  [q] Finish ruby trade for this player")

            choice = input(f"Player {pid} choice [d/p/q]: ").strip().lower()
            if choice in ("q", "quit", "done", ""):
                broadcast(state, f"Player {pid}: finished ruby trade.")
                break

            if choice in ("d", "droplet"):
                state["players"][pid]["rubies"] -= RUBY_COST
                state["players"][pid]["droplet_pos"] = int(state["players"][pid].get("droplet_pos", 0)) + 1
                broadcast(
                    state,
                    f"Player {pid}: spent {RUBY_COST} rubies -> droplet_pos now {state['players'][pid]['droplet_pos']} "
                    f"(rubies left {state['players'][pid]['rubies']})."
                )
                continue

            if choice in ("p", "potion", "flask"):
                if bool(state["players"][pid].get("potion_filled", True)):
                    broadcast(state, f"Player {pid}: potion is already FILLED. Refill not allowed.")
                    continue

                state["players"][pid]["rubies"] -= RUBY_COST
                state["players"][pid]["potion_filled"] = True
                broadcast(
                    state,
                    f"Player {pid}: spent {RUBY_COST} rubies -> potion refilled "
                    f"(rubies left {state['players'][pid]['rubies']})."
                )
                continue

            broadcast(state, f"Player {pid}: invalid choice '{choice}'. Use d/p/q.")

    confirm_all_players(state, player_ids, "Ruby trade done. Round ends.")



PhaseId = Literal[
    "start",
    "event_card",
    "rat_tails",
    "drawing",
    "winner_and_dice",
    "chip_eval",
    "rubies",
    "vp_and_coins",
    "purchase",
    "ruby_trade",
]

ROUND_PHASES: List[PhaseId] = [
    "start",
    "event_card",
    "rat_tails",
    "drawing",
    "winner_and_dice",
    "chip_eval",
    "rubies",
    "vp_and_coins",
    "purchase",
    "ruby_trade",
]

PHASE_DISPATCH: dict[PhaseId, Callable[[GameStateTD, int, List[int], random.Random], None]] = {
    "start": phase_start,
    "event_card": phase_event_card,
    "rat_tails": phase_rat_tails,
    "drawing": phase_drawing,
    "winner_and_dice": phase_winner_and_dice,
    "chip_eval": phase_chip_eval,
    "rubies": phase_rubies,
    "vp_and_coins": phase_vp_and_coins,
    "purchase": phase_purchase,
    "ruby_trade": phase_ruby_trade,
}

PHASE_REQUIRES: dict[PhaseId, List[str]] = {
    "start": [],
    "event_card": [],
    "rat_tails": [],
    "drawing": ["gray_limit"],
    "winner_and_dice": ["drawing_results"],
    "chip_eval": [],
    "rubies": ["drawing_results"],
    "vp_and_coins": ["drawing_results"],
    "purchase": [],
    "ruby_trade": [],
}



# -----------------------------
# Round / Game driver
# -----------------------------
def run_round(
    state: GameStateTD,
    round_no: int,
    player_ids: List[int],
    rng: random.Random,
    *,
    gray_limit: int = 7
) -> None:
    clear_round_ctx(state)
    state["round_ctx"]["gray_limit"] = gray_limit

    for phase_id in ROUND_PHASES:
        # check requirements
        for key in PHASE_REQUIRES.get(phase_id, []):
            if key not in state["round_ctx"]:
                raise RuntimeError(f"Phase '{phase_id}' requires missing round_ctx key: '{key}'")

        # call phase
        PHASE_DISPATCH[phase_id](state, round_no, player_ids, rng)

    # -------------------------
    # End-of-round cleanup
    # -------------------------
    from actions import return_all_pot_to_bag, return_all_palm_to_bag

    broadcast(state, f"\n[ROUND {round_no}] CLEANUP: returning pot contents to bags.")

    for pid in player_ids:
        # Safety invariant: palm should be empty at end of a round, but enforce it.
        if state.get("palms", {}).get(pid):
            leftover = return_all_palm_to_bag(state, pid)
            if leftover:
                broadcast(state, f"[ROUND {round_no}] CLEANUP: Player {pid} had leftover PALM chips -> bag: {leftover}")

        returned = return_all_pot_to_bag(state, pid)
        broadcast(state, f"[ROUND {round_no}] CLEANUP: Player {pid} pot -> bag ({len(returned)} chips).")

    # Clear round modifiers / pointers
    state["active_blue_event"] = None
    state["current_event"] = None



def run_game(state: GameStateTD, player_count: int, *, seed: int = 42, gray_limit: int = 7) -> None:
    player_ids = list(range(player_count))
    for pid in player_ids:
        ensure_player(state, pid)

    rng = random.Random(seed)

    state["event_deck"] = list(EVENT_DECK)
    state["event_discard"] = []
    state["current_event"] = None
    state["active_blue_event"] = None

    broadcast(state, f"\nGAME START: players={player_ids}, rounds=9, seed={seed}, gray_limit={gray_limit}")
    confirm_all_players(state, player_ids, "Game start confirmed. Begin round 1?")

    for round_no in range(1, 10):  # 1..9
        run_round(state, round_no, player_ids, rng, gray_limit=gray_limit)

    broadcast(state, "\nGAME END — Final standings:")
    for pid in player_ids:
        ps = state["players"][pid]
        broadcast(state, f"Player {pid}: VP={ps['victory_points']}, coins={ps['coins']}, rubies={ps['rubies']}")


def apply_ui_action(state: GameStateTD, pid: int, action_id: str, payload: dict | None) -> None:
    ...
