#!/usr/bin/env python3
"""
web/server.py — FastAPI PoC server for browser UI.

Run:
  python -m web.server

LAN:
  uvicorn web.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse  # ensure this import exists

from .game_manager import GameManager
from .views import build_public_view
from . import engine_ui

app = FastAPI(title="QuQu Web PoC")
gm = GameManager()

# Static + templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


# -----------------------------
# Pages
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def lobby(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("lobby.html", {"request": request})


@app.post("/create")
def create_game(host_name: str = Form(...)) -> RedirectResponse:
    sess = gm.create_game(host_name=host_name.strip())
    return RedirectResponse(url=f"/g/{sess.game_id}?pid=0", status_code=303)


@app.post("/join")
def join_game(join_code: str = Form(...), player_name: str = Form(...)) -> RedirectResponse:
    sess = gm.get_game_by_code(join_code.strip())
    if not sess:
        return RedirectResponse(url="/?err=unknown_code", status_code=303)

    p = sess.add_player(player_name.strip())
    return RedirectResponse(url=f"/g/{sess.game_id}?pid={p.pid}", status_code=303)


@app.get("/g/{game_id}", response_class=HTMLResponse)
def game_page(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return RedirectResponse(url="/?err=unknown_game", status_code=303)

    pub = build_public_view(sess, pid=pid)
    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "game_id": sess.game_id,
            "join_code": sess.join_code,
            "pid": pid,
            "ui": pub["ui"],
            "meta": pub.get("meta", {}),
        },
    )

# -----------------------------
# Fragments for polling (HTMX)
# -----------------------------
@app.get("/g/{game_id}/f/prompt", response_class=HTMLResponse)
def fragment_prompt(request: Request, game_id: str, pid: int) -> HTMLResponse:

    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    pub = build_public_view(sess, pid=pid)
    print("PROMPT ROUTE DEBUG pub =", pub)
    print("PROMPT ROUTE DEBUG ui.prompt =", pub.get("ui", {}).get("prompt"))
    return templates.TemplateResponse(
        "fragments/prompt.html",
        {"request": request, "ui": pub["ui"]},
    )


@app.post("/g/{game_id}/input")
def post_input(game_id: str, pid: int = Form(...), text: str = Form("")) -> RedirectResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return RedirectResponse(url="/?err=unknown_game", status_code=303)

    t = (text or "").strip()
    if not t:
        sess.add_log(f"Empty input ignored from pid={pid}")
        return RedirectResponse(url=f"/g/{game_id}?pid={pid}", status_code=303)

    sess.state["last_input"] = {"pid": pid, "text": t}
    sess.add_log(f"INPUT pid={pid}: {t}")

    engine_ui.apply_text_input(sess, pid=pid, text=t)
    # apply_text_input() logs acceptance/rejection and advances as needed

    return RedirectResponse(url=f"/g/{game_id}?pid={pid}", status_code=303)


@app.get("/g/{game_id}/f/inputbar", response_class=HTMLResponse)
def fragment_inputbar(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    # We don't even need the full view here, but it’s fine if you want it later.
    return templates.TemplateResponse(
        "fragments/inputbar.html",
        {"request": request, "game_id": sess.game_id, "join_code": sess.join_code, "pid": pid},
    )

@app.post("/g/{game_id}/input")
def post_input(
    game_id: str,
    pid: int = Form(...),
    text: str = Form(...),
) -> RedirectResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return RedirectResponse(url="/?err=unknown_game", status_code=303)

    sess.submit_text(pid=pid, text=text)

    return RedirectResponse(url=f"/g/{game_id}?pid={pid}", status_code=303)


@app.get("/g/{game_id}/f/board", response_class=HTMLResponse)
def fragment_board(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    pub = build_public_view(sess, pid=pid)
    return templates.TemplateResponse(
        "fragments/board.html",
        {"request": request, "game_id": sess.game_id, "join_code": sess.join_code, "pid": pid, "ui": pub["ui"]},
    )


@app.get("/g/{game_id}/f/players", response_class=HTMLResponse)
def fragment_players(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    pub = build_public_view(sess, pid=pid)
    return templates.TemplateResponse(
        "fragments/players.html",
        {"request": request, "game_id": sess.game_id, "join_code": sess.join_code, "pid": pid, "ui": pub["ui"]},
    )

@app.get("/g/{game_id}/f/prompt_input", response_class=HTMLResponse)
def fragment_prompt_input(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    pub = build_public_view(sess, pid=pid)
    is_my_turn = (pid == sess.current_pid)

    return templates.TemplateResponse(
        "fragments/prompt_input.html",
        {
            "request": request,
            "ui": pub["ui"],
            "game_id": sess.game_id,
            "pid": pid,
            "is_my_turn": is_my_turn,
            "current_pid": sess.current_pid,
        },
    )


@app.get("/g/{game_id}/f/actions", response_class=HTMLResponse)
def fragment_actions(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    pub = build_public_view(sess, pid=pid)
    return templates.TemplateResponse(
        "fragments/actions.html",
        {"request": request, "game_id": sess.game_id, "join_code": sess.join_code, "pid": pid, "ui": pub["ui"]},
    )


@app.get("/g/{game_id}/f/log", response_class=HTMLResponse)
def fragment_log(request: Request, game_id: str, pid: int) -> HTMLResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return HTMLResponse("Unknown game", status_code=404)

    pub = build_public_view(sess, pid=pid)
    return templates.TemplateResponse(
        "fragments/log.html",
        {"request": request, "game_id": sess.game_id, "join_code": sess.join_code, "pid": pid, "ui": pub["ui"]},
    )


# -----------------------------
# Actions
# -----------------------------
@app.post("/g/{game_id}/action")
def post_action(game_id: str, pid: int = Form(...), action: str = Form(...)) -> RedirectResponse:
    sess = gm.get_game(game_id)
    if not sess:
        return RedirectResponse(url="/?err=unknown_game", status_code=303)

    # PoC: keep cursor changes in GameSession
    if action == "confirm":
        sess.advance(pid=pid)
    else:
        sess.add_log(f"Unknown action: {action} by pid={pid}")

    return RedirectResponse(url=f"/g/{game_id}?pid={pid}", status_code=303)



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.server:app", host="127.0.0.1", port=8000, reload=True)
