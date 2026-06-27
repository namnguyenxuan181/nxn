from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from ai_platform.auth import CurrentUser, auth_config, get_current_user, require_role
from ai_platform.chat import stream_chat
from ai_platform.data_access import get_all_symbols
from ai_platform.report import generate_report
from ai_platform.screener import screen_stocks
from stock.scrapers.intraday import fetch_intraday_ohlc, is_market_open

app = FastAPI(title="NXN AI Platform")

_STATIC = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    history: List[Dict] = []


class ScreenRequest(BaseModel):
    query: str


# ── Public endpoints ──────────────────────────────────────────────────────────

@app.get("/api/auth")
def get_auth_config():
    """Return Keycloak config so the browser knows how to login."""
    return auth_config()


@app.get("/api/symbols")
def symbols(user: Optional[CurrentUser] = Depends(get_current_user)):
    return get_all_symbols()


# ── Protected endpoints ───────────────────────────────────────────────────────

@app.post("/api/chat")
def chat(
    req: ChatRequest,
    user: Optional[CurrentUser] = Depends(
        require_role("ai_user", "analyst", "data_engineer", "admin")
    ),
):
    def generate():
        for chunk in stream_chat(req.message, req.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/report/{symbol}")
def report(
    symbol: str,
    user: Optional[CurrentUser] = Depends(require_role("analyst", "data_engineer", "admin")),
):
    result = generate_report(symbol.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data available for {symbol.upper()}")
    return result


@app.post("/api/screen")
def screen(
    req: ScreenRequest,
    user: Optional[CurrentUser] = Depends(require_role("analyst", "data_engineer", "admin")),
):
    result = screen_stocks(req.query)
    if result.get("error") == "Could not parse query":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/intraday/{symbol}")
def intraday(
    symbol: str,
    resolution: int = 5,
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    if resolution not in (1, 5, 10):
        raise HTTPException(status_code=400, detail="resolution must be 1, 5, or 10")
    bars = fetch_intraday_ohlc(symbol.upper(), resolution)
    return {
        "symbol": symbol.upper(),
        "resolution": resolution,
        "market_open": is_market_open(),
        "bars": bars,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return (_STATIC / "index.html").read_text(encoding="utf-8")
