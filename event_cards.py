#!/usr/bin/env python3
"""
event_cards.py — Event card deck definition (Quacks)

Cards are drawn randomly WITHOUT replacement.
Each card has a color:
- purple: execute immediately after draw + unanimous confirmation (one-shot; may mutate state)
- blue: active modifier for the duration of the round (end phases)

This module defines structure + deck data (no effect mechanics yet).

by Sziller
"""

from __future__ import annotations

from typing import Literal, Optional, TypedDict, List


EventColor = Literal["blue", "purple"]
EventScope = Literal["global", "per_player"]


class EventCardTD(TypedDict, total=False):
    # Stable unique identifier for the card (never change once adopted)
    card_id: str

    # Display metadata
    title: str
    color: EventColor
    description: str

    # Placeholder for future effect dispatch
    effect_id: Optional[str]

    # For PURPLE cards only: whether the immediate action is resolved globally or per player.
    # Blue cards can omit this.
    scope: Optional[EventScope]


# ---------------------------------------------------------------------
# Authoritative deck (as provided by you) with stable IDs assigned here
# ---------------------------------------------------------------------
EVENT_DECK: List[EventCardTD] = [
    # {
    #     "card_id": "EV01",
    #     "color": "purple",
    #     "title": "A good start",
    #     "description": "Choose: Use your rat stone normally OR pass up on 1-3 rat tails and take 1-3 rubies instead",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV02",
    #     "color": "purple",
    #     "title": "The pot is filling up",
    #     "description": "Move your droplet 1 space forward",
    #     "scope": "global"
    # },
    # {
    #     "card_id": "EV03",
    #     "color": "purple",
    #     "title": "Donations",
    #     "description": "Everyone rolls the die once and receives a bonus accordingly",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV04",
    #     "color": "purple",
    #     "title": "Wheel and deal",
    #     "description": "You can trade 1 ruby for any one 1-chip (not purple or black)",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV05",
    #     "color": "purple",
    #     "title": "Less is more",
    #     "description": "All players draw 5 chips. The player(s) with the lowest sum get(s) to take 1 blue 2-chip."
    #                    "All other players receive 1 ruby. Then, put all the chips back in the bag!",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV06",
    #     "color": "purple",
    #     "title": "An opportunistic moment",
    #     "description": "Draw 4 chips from your bag. You can trade in one of them for the chip of the same color,"
    #                    "with the next highest value. Take one green 1-chip, if you can't make a trade."
    #                    "Then, put all the chips back in the bag!",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV07",
    #     "color": "purple",
    #     "title": "Beginner’s bonus",
    #     "description": "The player(s) with the fewest victory points receive(s) one green 1-chip.",
    #     "scope": "global"
    # },
    # {
    #     "card_id": "EV08",
    #     "color": "purple",
    #     "title": "Just in time",
    #     "description": "Choose: Take 4 victory points OR remove one white 1-chip from your bag.",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV09",
    #     "color": "purple",
    #     "title": "But you only get to choose one",
    #     "description": "Choose: Take 1 black chip OR any one 2-chip OR 3 rubies.",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV10",
    #     "color": "blue",
    #     "title": "Rat infestation",
    #     "description": "Double the number of rat tails in this round.",
    #     "scope": "per_player"
    # },
    # {
    #     "card_id": "EV11",
    #     "color": "purple",
    #     "title": "Rats are your friends",
    #     "description": "Choose: Take any one 4-chip OR 1 victory point for each rat tail you will receive.",
    #     "scope": "per_player"
    # },
    {
        "card_id": "EV12",
        "color": "purple",
        "title": "Alms",
        "description": "The player(s) with the fewest rubies receive(s) 1 ruby.",
        "scope": "global"
    },
    {
        "card_id": "EV13",
        "color": "purple",
        "title": "Choose wisely - I.",
        "description": "Choose: Move your droplet 2 spaces forward OR take 1 purple chip.",
        "scope": "per_player"
    },
    {
        "card_id": "EV14",
        "color": "purple",
        "title": "Choose wisely - II.",
        "description": "Choose: Move your droplet 2 spaces forward OR take 1 purple chip.",
        "scope": "per_player"
    },
    # {
    #     "card_id": "EV15",
    #     "color": "blue",
    #     "title": "Well stirred",
    #     "description": "In this round, you get to put the first white chip you draw back into the bag."
    # },
    # {
    #     "card_id": "EV16",
    #     "color": "blue",
    #     "title": "Strong ingredient",
    #     "description": "Beginning with the start player: If you stopped without an explosion,"
    #                    "draw up to 5 chips from your bag and place 1 of them in your pot."
    # },
    # {
    #     "card_id": "EV17",
    #     "color": "blue",
    #     "title": "A second chance",
    #     "description": "After the first 5 chips have landed in your pot, choose: Continue OR begin the round all over"
    #                    "again – possible only once (1x)."
    # },
    # {
    #     "card_id": "EV18",
    #     "color": "blue",
    #     "title": "Seasoned perfectly",
    #     "description": "If your white chips total exactly 7 at the end of the round, you get to move your droplet"
    #                    "1 field forward."
    # },
    # {
    #     "card_id": "EV19",
    #     "color": "blue",
    #     "title": "Magic potion",
    #     "description": "At the end of the round, all the flasks get a free refill."
    # },
    # {
    #     "card_id": "EV20",
    #     "color": "blue",
    #     "title": "Living in luxury",
    #     "description": "The threshold for white chips is raised in this round from 7 to 9."
    # },
    # {
    #     "card_id": "EV21",
    #     "color": "blue",
    #     "title": "Malicious joy",
    #     "description": "If your pot explodes in this round, the player to your left gets any one 2-chip."
    # },
    # {
    #     "card_id": "EV22",
    #     "color": "blue",
    #     "title": "Pumpkin patch party",
    #     "description": "In this round, every orange chip is moved 1 extra space forward."
    # },
    # {
    #     "card_id": "EV23",
    #     "color": "blue",
    #     "title": "Lucky devil",
    #     "description": "Regardless if your pot has exploded or not:"
    #                    "If you reach a scoring field with a ruby in this round, you get an extra 2 victory points."
    # },
    # {
    #     "card_id": "EV24",
    #     "color": "blue",
    #     "title": "The pot is full",
    #     "description": "The player(s) who get(s) to roll the die in this round roll(s) twice (2x)."
    # },
    # {
    #     "card_id": "EV25",
    #     "color": "blue",
    #     "title": "Shining extra bright",
    #     "description": "If you reach a scoring field with a ruby in this round, you get an extra ruby.",
    # }
]

