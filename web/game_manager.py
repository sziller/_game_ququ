#!/usr/bin/env python3
"""
web/game_manager.py — In-memory game sessions for the PoC web UI.

This is deliberately minimal:
- Creates games
- Lets players join
- Advances a simple (round, phase, current_player) cursor on confirm

Later, you will replace `advance()` with calls into your real rounds/phase logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import secrets
import time


PHASES: List[str] = [
    "EVENT",
    "DRAW",
    "EVAL",
    "BUY",
    "CLEANUP",
]


def _now_ts() -> float:
    return time.time()


def _new_id(nbytes: int = 8) -> str:
    return secrets.token_hex(nbytes)


@dataclass
class Player:
    pid: int
    name: str
    joined_ts: float = field(default_factory=_now_ts)


@dataclass
class GameSession:
    game_id: str
    join_code: str
    created_ts: float = field(default_factory=_now_ts)

    players: Dict[int, Player] = field(default_factory=dict)

    # Minimal “engine cursor”:
    round_idx: int = 1
    phase_idx: int = 0
    current_pid: int = 0

    log: List[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)
    pending_text_by_pid: Dict[int, str] = field(default_factory=dict)

    def phase_name(self) -> str:
        return PHASES[self.phase_idx]

    def add_log(self, msg: str) -> None:
        self.log.append(f"{time.strftime('%H:%M:%S')} | {msg}")

    def add_player(self, name: str) -> Player:
        pid = 0 if not self.players else (max(self.players.keys()) + 1)
        p = Player(pid=pid, name=name)
        self.players[pid] = p
        self.add_log(f"Player joined: pid={pid} name={name}")
        # Default host is pid 0; current_pid stays 0 unless you want “last join becomes active”.
        self.sync_state_from_cursor()  # TODO check if needed
        return p

    def sync_state_from_cursor(self) -> None:
        """
        Keep `self.state` in sync with the PoC cursor fields.

        This is a transitional bridge so the UI can read from `self.state`
        now, and later you can replace `self.state` with real GameStateTD.
        """
        self.state["round_idx"] = self.round_idx
        self.state["phase"] = self.phase_name()
        self.state["current_pid"] = self.current_pid
        self.state["log"] = self.log
        self.state["players"] = [{"pid": p.pid, "name": p.name} for p in self.players.values()]
        self.state["join_code"] = self.join_code

    def advance(self, pid: int) -> None:
        """
        PoC rule: only current player can confirm, and confirm moves the cursor:
        - phase advances
        - when phase wraps, round advances and current player rotates
        """
        if pid != self.current_pid:
            self.add_log(f"Denied confirm by pid={pid} (current pid={self.current_pid})")
            return

        old_phase = self.phase_name()
        self.phase_idx += 1
        if self.phase_idx >= len(PHASES):
            self.phase_idx = 0
            self.round_idx += 1
            # rotate current player
            if self.players:
                pids = sorted(self.players.keys())
                cur_i = pids.index(self.current_pid) if self.current_pid in pids else 0
                self.current_pid = pids[(cur_i + 1) % len(pids)]
            self.add_log(f"Round advanced to {self.round_idx}. Current player pid={self.current_pid}.")
        else:
            self.add_log(f"Phase advanced: {old_phase} -> {self.phase_name()}")
        self.sync_state_from_cursor()

    def submit_text(self, pid: int, text: str) -> None:
        """
        Store the latest text input for this pid and let the engine consume it.
        For PoC: we just log it and (optionally) advance.
        """
        t = (text or "").strip()
        if not t:
            self.add_log(f"Empty input ignored from pid={pid}")
            self.sync_state_from_cursor()
            return

        self.pending_text_by_pid[pid] = t
        self.add_log(f"INPUT pid={pid}: {t}")

        # PoC behavior: treat input as the 'answer' and then run advance if it is your turn.
        # Later you will route this to your real engine decision logic.
        if pid == self.current_pid:
            # Example: for now, any non-empty input counts as "confirm with text"
            self.advance(pid=pid)
        else:
            self.add_log(f"Input stored, but it's not your turn (current pid={self.current_pid})")

        self.sync_state_from_cursor()


class GameManager:
    """
    Simple in-memory store (good for PoC; later you may persist to disk).

    The host-as-player assumption works fine: game creator joins as pid=0.
    """

    def __init__(self) -> None:
        self._games: Dict[str, GameSession] = {}
        self._code_to_gid: Dict[str, str] = {}

    def create_game(self, host_name: str) -> GameSession:
        gid = _new_id(8)
        code = _new_id(3)  # short join code
        session = GameSession(game_id=gid, join_code=code)
        session.add_player(host_name)  # pid=0
        session.add_log(f"Game created. join_code={code}")
        session.sync_state_from_cursor()
        self._games[gid] = session
        self._code_to_gid[code] = gid
        return session

    def get_game(self, game_id: str) -> Optional[GameSession]:
        return self._games.get(game_id)

    def get_game_by_code(self, join_code: str) -> Optional[GameSession]:
        gid = self._code_to_gid.get(join_code)
        return self._games.get(gid) if gid else None
