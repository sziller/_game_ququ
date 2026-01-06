#!/usr/bin/env python3
"""
web/engine_ui.py — Adapter between web UI and the QuQu engine.

This module is the ONLY place that translates engine state into:
- prompt line text
- available actions (buttons)
- applying a UI action to the engine

The web templates and server must remain dumb.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict


# Phase → allowed commands (PoC)
PHASE_COMMANDS: Dict[str, List[str]] = {
    "EVENT":   ["ok"],
    "DRAW":    ["draw", "stop"],
    "EVAL":    ["ok"],
    "BUY":     ["buy", "skip"],
    "CLEANUP": ["ok"],
}

def normalize_cmd(text: str) -> str:
    return (text or "").strip().lower()

def allowed_commands(state: dict) -> List[str]:
    phase = str(state.get("phase", "EVENT"))
    return PHASE_COMMANDS.get(phase, ["ok"])

def compute_prompt(state: dict, pid: int) -> str:
    round_idx = state.get("round_idx", "?")
    phase = state.get("phase", "?")
    current_pid = int(state.get("current_pid", 0))

    if pid != current_pid:
        return f"Round {round_idx} — Phase {phase}. Waiting for pid={current_pid}."

    cmds = allowed_commands(state)
    return f"Round {round_idx} — Phase {phase}. Enter one of: {', '.join(cmds)}"

class UiActionTD(TypedDict, total=False):
    action_id: str
    label: str
    enabled: bool
    reason: str


# -------------------------------------------------------------------
# IMPORTANT: Replace the three "ENGINE HOOKS" below with your real ones.
# -------------------------------------------------------------------

def engine_get_phase(state: Dict[str, Any]) -> str:
    """
    ENGINE HOOK #1
    Return a stable phase identifier from your real engine state.
    Example: "EVENT", "DRAW", "BUY", ...
    """
    # If you already store phase in state:
    if "phase" in state:
        return str(state["phase"])
    # If not, adapt here.
    return "UNKNOWN"


def engine_get_current_pid(state: Dict[str, Any]) -> int:
    """
    ENGINE HOOK #2
    Return which player is currently allowed/expected to act.
    """
    if "current_pid" in state:
        return int(state["current_pid"])
    return 0


def engine_apply_ui_action(state: Dict[str, Any], pid: int, action_id: str, payload: Optional[Dict[str, Any]]) -> None:
    """
    ENGINE HOOK #3
    Apply a UI action to the engine state.

    This is where you call your real dispatch tables / phase logic.
    """
    # Minimal fallback (so nothing explodes). Replace with your real engine call.
    # Example idea:
    from rounds import apply_ui_action
    apply_ui_action(state, pid=pid, action_id=action_id, payload=payload)

    if action_id == "confirm":
        # If you still have a session.advance() in the web layer, you can remove it later.
        # Here you want the engine to do whatever "confirm" means.
        state.setdefault("log", []).append(f"confirm by pid={pid} (ENGINE HOOK NOT CONNECTED)")
    else:
        state.setdefault("log", []).append(f"unknown action_id={action_id} by pid={pid} (ENGINE HOOK NOT CONNECTED)")


# -------------------------------------------------------------------
# UI-facing logic (derived from engine hooks)
# -------------------------------------------------------------------

def compute_prompt(state: dict, pid: int) -> str:
    round_idx = state.get("round_idx", "?")
    phase = state.get("phase", "?")
    current_pid = int(state.get("current_pid", 0))

    if pid != current_pid:
        return f"Round {round_idx} — Phase {phase}. Waiting for pid={current_pid}."

    # Current player prompt (phase-specific)
    if phase == "EVENT":
        return f"Round {round_idx} — Event phase: resolve the event card, then Confirm."
    if phase == "DRAW":
        return f"Round {round_idx} — Draw phase: draw chips (later UI), then Confirm."
    if phase == "EVAL":
        return f"Round {round_idx} — Eval phase: evaluate pot results, then Confirm."
    if phase == "BUY":
        return f"Round {round_idx} — Buy phase: buy chips (later UI), then Confirm."
    if phase == "CLEANUP":
        return f"Round {round_idx} — Cleanup phase: reset for next round, then Confirm."

    return f"Round {round_idx} — Phase {phase}. Your turn. Confirm to continue."


def legal_actions(state: dict, pid: int) -> list[dict]:
    current_pid = int(state.get("current_pid", 0))
    phase = state.get("phase", "?")

    # Not your turn => everything disabled
    if pid != current_pid:
        return [
            {"action_id": "confirm", "label": "Confirm / Next", "enabled": False, "reason": "Not your turn."}
        ]

    # Your turn => confirm enabled
    # (Later you will add phase-specific actions here.)
    label = "Confirm / Next"
    if phase == "BUY":
        label = "Confirm / Finish buying"
    elif phase == "DRAW":
        label = "Confirm / Finish drawing"
    elif phase == "EVENT":
        label = "Confirm / Finish event"

    return [
        {"action_id": "confirm", "label": label, "enabled": True}
    ]



def apply_action(state: Dict[str, Any], pid: int, action_id: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """
    Single entry point for the web layer.
    """
    payload = payload or {}
    # Always delegate to the engine hook
    engine_apply_ui_action(state, pid=pid, action_id=action_id, payload=payload)

def apply_text_input(sess, pid: int, text: str) -> bool:
    """
    Returns True if input was accepted (and phase may advance),
    False if rejected (no advance).
    """
    cmd = normalize_cmd(text)
    phase = sess.state.get("phase", sess.phase_name())

    # Not your turn: reject
    if pid != sess.current_pid:
        sess.add_log(f"Rejected input '{cmd}' from pid={pid}: not your turn.")
        return False

    allowed = PHASE_COMMANDS.get(phase, ["ok"])
    if cmd not in allowed:
        sess.add_log(f"Rejected input '{cmd}' in phase {phase}. Allowed: {', '.join(allowed)}")
        return False

    # Phase-specific PoC effects
    if phase == "DRAW":
        if cmd == "draw":
            sess.add_log("DRAW: player chose to draw (PoC: no chip logic yet).")
            # stay in DRAW for now if you want multi-draw; or advance if you prefer:
            # sess.advance(pid)
            return True
        if cmd == "stop":
            sess.add_log("DRAW: player chose to stop drawing.")
            sess.advance(pid)
            return True

    if phase == "BUY":
        if cmd == "buy":
            sess.add_log("BUY: player chose to buy (PoC: no shop yet).")
            sess.advance(pid)
            return True
        if cmd == "skip":
            sess.add_log("BUY: player skipped buying.")
            sess.advance(pid)
            return True

    # Default: ok advances
    sess.add_log(f"{phase}: ok")
    sess.advance(pid)
    return True
