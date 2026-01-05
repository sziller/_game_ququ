# Contributing

Thank you for considering contributing to this project.

This repository implements a Python-based game engine and rule framework for a Quacks-style board game (turn/round phases, event cards, player state, and a steadily expanding ruleset). The codebase is intentionally structured for incremental correctness: we prefer small, reviewable changes over “big bang” rewrites.

## Project goals

- Provide a readable, testable rules engine (round/phase flow, event cards, actions, state transitions).
- Keep game logic explicit and auditable (avoid “magic” behavior).
- Make it easy to add new rules, chips, and event cards without hard-coded branching.
- Maintain a developer-friendly console output for debugging and verification.

Non-goals (for now):
- Full UI/graphics polish.
- Multiplayer networking.
- Perfect simulation accuracy for every expansion rule (these are added incrementally).

---

## Ground rules (high signal expectations)

### 1) Keep PRs small
Prefer PRs that do one thing:
- one refactor,
- one new card implementation,
- one bugfix,
- one test set,
- one documentation improvement.

If you want to do a larger change, open a Discussion or Issue first.

### 2) No “drive-by architecture”
This project has an intentionally explicit architecture:
- state is stored centrally,
- phases are sequenced,
- rules are implemented as functions invoked by dispatch tables.

If you disagree with the approach, that’s fine—open a Discussion. Do not “sneak” architectural rewrites into a PR.

### 3) Be deterministic where possible
If you introduce randomness (e.g., card shuffling, chip draws), ensure:
- there is a clear seeding strategy for tests or debug runs, or
- deterministic hooks exist (e.g., injectable RNG).

---

## How to get started

### 1) Fork and branch
- Fork the repo.
- Create a feature branch from `main`:
  - `feature/<short-description>`
  - `fix/<short-description>`
  - `docs/<short-description>`

### 2) Local setup
This project is plain Python.

Recommended:
- Python 3.11+ (3.10 may work depending on typing features used)
- A virtual environment

Example:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
