#!/usr/bin/env python3
"""
state.py — Quacks chip state & pool construction + central player state

This module defines:
- identity-preserving chip pool (box/bag/palm/pot/where)
- per-player central state (coins, victory points, rubies, droplet position, etc.)
- helpers for initialization and integrity checks

Gameplay actions belong in actions.py.
Round orchestration belongs in rounds.py.

by Sziller
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Set, TypedDict


# -----------------------------
# TypedDicts (simple + extendable)
# -----------------------------
class EffectTD(TypedDict, total=False):
    id: str
    params: Dict[str, Any]


class ChipTypeTD(TypedDict, total=False):
    type_id: str
    color: str
    name_de: str
    value: int
    effects: List[EffectTD]
    ui: Dict[str, Any]


class ChipTD(TypedDict):
    chip_id: str
    type_id: str
    state: Dict[str, Any]  # per-chip annotations if ever needed


# NEW: add "palm" as an identity-preserving location
Zone = Literal["box", "bag", "palm", "desktop", "pot"]



class LocationTD(TypedDict):
    zone: Zone
    player: Optional[int]  # None for box


class PlayerStateTD(TypedDict):
    coins: int
    victory_points: int
    rubies: int

    # Persistent placement head-start. Field index where chip placement "base" begins.
    droplet_pos: int
    # NEW: Flask / potion state (persistent across rounds)
    potion_filled: bool


class GameStateTD(TypedDict):
    chip_types: Dict[str, ChipTypeTD]
    chips: Dict[str, ChipTD]
    where: Dict[str, LocationTD]

    box: Set[str]
    bags: Dict[int, List[str]]

    # NEW: ephemeral inspection zone per player
    palms: Dict[int, List[str]]
    desktops: Dict[int, List[str]]
    pots: Dict[int, List[str]]

    # Centrally recorded player state
    players: Dict[int, PlayerStateTD]

    # Public, centrally recorded log entries (transparency)
    public_log: List[str]

    # Event card system (deck without replacement)
    event_deck: List[dict]        # list[EventCardTD], kept loose to avoid circular import typing
    event_discard: List[dict]     # drawn cards in order
    current_event: Optional[dict] # active card for the current round

    # Active round modifiers
    active_blue_event: Optional[dict]   # the blue event card active for the current round

    # Round-scoped transient workspace (phase outputs, temporary calculations, etc.)
    round_ctx: Dict[str, Any]


# -----------------------------
# ID helpers (stable & readable)
# -----------------------------
def type_id(color: str, value: int) -> str:
    """Return the canonical type_id for a chip denomination."""
    return f"{color}:{value}"


def chip_id(type_id_: str, serial: int) -> str:
    """Return the canonical chip_id for a specific physical chip instance."""
    return f"{type_id_}#{serial:04d}"


# -----------------------------
# Core state builders / helpers
# -----------------------------
def build_pool(chips_def: List[Dict[str, Any]]) -> GameStateTD:
    """
    Build chip catalog + all identity-preserving chip instances into the central box.
    """
    chip_types: Dict[str, ChipTypeTD] = {}
    chips: Dict[str, ChipTD] = {}
    where: Dict[str, LocationTD] = {}
    box: Set[str] = set()

    for entry in chips_def:
        color = entry["color"]
        name_de = entry["name-DE"]
        inv: Dict[int, int] = entry["inv"]

        for value, count in inv.items():
            tid = type_id(color, int(value))

            chip_types[tid] = {
                "type_id": tid,
                "color": color,
                "name_de": name_de,
                "value": int(value),
                "effects": [],
                "ui": {},
            }

            for serial in range(1, int(count) + 1):
                cid = chip_id(tid, serial)
                chips[cid] = {"chip_id": cid, "type_id": tid, "state": {}}
                where[cid] = {"zone": "box", "player": None}
                box.add(cid)

    return {
        "chip_types": chip_types,
        "chips": chips,
        "where": where,
        "box": box,
        "bags": {},
        "palms": {},          # NEW
        "pots": {},
        "desktops": {},
        "players": {},
        "public_log": [],
        "event_deck": [],
        "event_discard": [],
        "current_event": None,
        "active_blue_event": None,
        "round_ctx": {},
    }


def ensure_player(state: GameStateTD, player_id: int) -> None:
    """
    Ensure the player's containers and central stats exist.
    Creates empty bag/palm/pot lists and initializes stats if missing.
    """
    state["bags"].setdefault(player_id, [])
    state["palms"].setdefault(player_id, [])   # NEW
    state["desktops"].setdefault(player_id, [])  # NEW
    state["pots"].setdefault(player_id, [])

    if player_id not in state["players"]:
        state["players"][player_id] = {
            "coins": 0,
            "victory_points": 0,
            "rubies": 0,
            "droplet_pos": 0,
            "potion_filled": True,  # NEW: starts filled
        }


def clear_round_ctx(state: GameStateTD) -> None:
    """
    Clear round-scoped transient data. Call at round start (and optionally at round end).
    """
    state["round_ctx"].clear()


def validate_unique_location(state: GameStateTD) -> None:
    """
    Debug/integrity check:
    Ensures each chip appears in exactly one container consistent with `where`.
    """
    seen: set[str] = set()

    # box
    for cid in state["box"]:
        assert cid not in seen, f"duplicate chip in containers: {cid}"
        seen.add(cid)
        loc = state["where"][cid]
        assert loc["zone"] == "box" and loc["player"] is None, f"where mismatch for {cid}: {loc}"

    # bags
    for pid, bag in state["bags"].items():
        for cid in bag:
            assert cid not in seen, f"duplicate chip in containers: {cid}"
            seen.add(cid)
            loc = state["where"][cid]
            assert loc["zone"] == "bag" and loc["player"] == pid, f"where mismatch for {cid}: {loc}"

    # palms (NEW)
    for pid, palm in state["palms"].items():
        for cid in palm:
            assert cid not in seen, f"duplicate chip in containers: {cid}"
            seen.add(cid)
            loc = state["where"][cid]
            assert loc["zone"] == "palm" and loc["player"] == pid, f"where mismatch for {cid}: {loc}"

    # pots
    for pid, pot in state["pots"].items():
        for cid in pot:
            assert cid not in seen, f"duplicate chip in containers: {cid}"
            seen.add(cid)
            loc = state["where"][cid]
            assert loc["zone"] == "pot" and loc["player"] == pid, f"where mismatch for {cid}: {loc}"

    # desktops (NEW)
    for pid, desk in state["desktops"].items():
        for cid in desk:
            assert cid not in seen, f"duplicate chip in containers: {cid}"
            seen.add(cid)
            loc = state["where"][cid]
            assert loc["zone"] == "desktop" and loc["player"] == pid, f"where mismatch for {cid}: {loc}"

    assert len(seen) == len(state["chips"]), (
        f"some chips are in no container: seen={len(seen)} total={len(state['chips'])}"
    )

