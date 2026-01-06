#!/usr/bin/env python3
"""
simulate.py — game runner for Quacks round framework (manual confirmations)

Run:
    python simulate.py
"""

# simulate.py

from catalog import CHIPS
from state import build_pool, validate_unique_location
from setup import setup_new_game
from setup import (
    setup_players_base,
    setup_players_with_arbitrary_bags,
)
from rounds import run_game

PLAYER_COUNT = 2


def main() -> None:
    player_count = PLAYER_COUNT
    state = build_pool(CHIPS)

    # # 1) Starting stats
    # setup_players_base(
    #     state,
    #     player_count=player_count,
    #     start_rubies=2,
    #     droplet_pos_by_player={1: 2},  # player 2 = pid 1
    # )
    # 
    # # 2) Arbitrary bags (example)
    # setup_players_with_arbitrary_bags(
    #     state,
    #     player_count=player_count,
    #     bag_by_player={
    #         0: {("gray", 1): 4, ("gray", 2): 2, ("orange", 1): 1},
    #         1: {("gray", 1): 4, ("gray", 3): 1, ("green", 1): 1, ("blue", 1): 1},
    #     },
    # )
    
    # 3.) Alternative approach!
    setup_new_game(
        state,
        player_count=player_count,
        start_rubies=2,
        droplet_pos_by_player={1: 2},
        bag_by_player={
            0: {("gray", 1): 4, ("gray", 2): 2, ("orange", 1): 1},
            1: {("gray", 1): 4, ("gray", 3): 1, ("green", 1): 1, ("blue", 1): 1} } )
    
    validate_unique_location(state)
    run_game(state, player_count=player_count, seed=42, gray_limit=7)


if __name__ == "__main__":
    main()

