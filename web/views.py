#!/usr/bin/env python3
"""
web/views.py — View-model builder for the web UI.

This module converts internal session/state into a UI-friendly dict that templates
can render. The web layer should not interpret engine state; it renders this view.

PoC contract expected by web/server.py:

build_public_view(sess, pid) -> {
  "ui": {
    "prompt": str,
    "actions": [ {action_id,label,enabled,reason?}, ... ],
    "board": {...},
    "players": [...],
    "log": [...]
  },
  "meta": {... optional ...}
}
"""

from __future__ import annotations
from typing import Any, Dict, List, TypedDict, Optional
from . import engine_ui


class UiActionTD(TypedDict, total=False):
    action_id: str
    label: str
    enabled: bool
    reason: str


class UiViewTD(TypedDict):
    prompt: str
    actions: List[UiActionTD]
    board: Dict[str, Any]
    players: List[Dict[str, Any]]
    log: List[str]


def _compute_prompt(round_idx: int, phase: str, current_pid: int, pid: int) -> str:
    if pid != current_pid:
        return f"Round {round_idx} — Phase {phase}. Waiting for pid={current_pid} to act."
    return f"Round {round_idx} — Phase {phase}. Your turn (pid={pid}). Choose an action."


def _legal_actions(current_pid: int, pid: int) -> List[UiActionTD]:
    if pid != current_pid:
        return [
            {
                "action_id": "noop",
                "label": "Waiting…",
                "enabled": False,
                "reason": "Not your turn.",
            }
        ]
    return [
        {"action_id": "confirm", "label": "Confirm / Next", "enabled": True},
    ]

from typing import Any, Dict, List
from . import engine_ui


def build_public_view(sess: Any, pid: int) -> Dict[str, Any]:
    """
    Expects sess.state to be the engine state dict (or GameStateTD).
    If you don't have sess.state yet, see Step 3.
    """
    state = getattr(sess, "state", None)
    if state is None:
        # Backwards compatibility: allow the old cursor-style session
        state = {
            "round_idx": getattr(sess, "round_idx", 1),
            "phase": sess.phase_name() if hasattr(sess, "phase_name") else getattr(sess, "phase", "EVENT"),
            "current_pid": getattr(sess, "current_pid", 0),
            "log": getattr(sess, "log", []),
        }

    ui = {
        "prompt": engine_ui.compute_prompt(state, pid),
        "actions": engine_ui.legal_actions(state, pid),
        "board": {
            "round_idx": state.get("round_idx", getattr(sess, "round_idx", 1)),
            "phase": state.get("phase", getattr(sess, "phase", "EVENT")),
            "current_pid": state.get("current_pid", getattr(sess, "current_pid", 0)),
        },
        # For now: keep players from session until you move them into engine state
        "players": [{"pid": int(p.pid), "name": str(p.name)} for p in getattr(sess, "players", {}).values()]
                   if isinstance(getattr(sess, "players", None), dict)
                   else [],
        "log": list(state.get("log", []))[-200:],
    }

    return {"ui": ui, "meta": {}}

