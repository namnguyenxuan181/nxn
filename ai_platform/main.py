from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from ai_platform.auth import CurrentUser, auth_config, get_current_user, require_role
from ai_platform.chat import stream_chat
from ai_platform.data_access import get_all_symbols, set_query_user
from ai_platform.opa_client import check_access
from ai_platform.report import generate_report
from ai_platform.screener import screen_stocks
from services.stock.scrapers.intraday import fetch_intraday_ohlc, is_market_open

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
    return auth_config()


@app.get("/api/symbols")
async def symbols(user: Optional[CurrentUser] = Depends(get_current_user)):
    policy = await check_access(user, table="stock_prices")
    all_syms = get_all_symbols()
    if policy.symbol_whitelist is not None:
        return [s for s in all_syms if s in policy.symbol_whitelist]
    return all_syms


# ── Protected endpoints ───────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(
    req: ChatRequest,
    user: Optional[CurrentUser] = Depends(
        require_role("ai_user", "analyst", "data_engineer", "admin")
    ),
):
    policy = await check_access(user, table="stock_prices")
    if not policy.allow:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập dữ liệu")
    if user:
        set_query_user(user.username)

    def generate():
        for chunk in stream_chat(req.message, req.history, policy=policy):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/report/{symbol}")
async def report(
    symbol: str,
    user: Optional[CurrentUser] = Depends(require_role("analyst", "data_engineer", "admin")),
):
    policy = await check_access(user, table="stock_prices")
    sym = symbol.upper()
    _, blocked = policy.filter_symbols([sym])
    if blocked:
        raise HTTPException(status_code=403, detail=f"Không có quyền truy vấn {sym}")
    if user:
        set_query_user(user.username)
    result = generate_report(sym)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {sym}")
    return result


@app.post("/api/screen")
async def screen(
    req: ScreenRequest,
    user: Optional[CurrentUser] = Depends(require_role("analyst", "data_engineer", "admin")),
):
    policy = await check_access(user, table="stock_prices")
    if not policy.allow:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập dữ liệu")
    if user:
        set_query_user(user.username)
    result = screen_stocks(req.query)
    if result.get("error") == "Could not parse query":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/intraday/{symbol}")
async def intraday(
    symbol: str,
    resolution: int = 5,
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    if resolution not in (1, 5, 10):
        raise HTTPException(status_code=400, detail="resolution must be 1, 5, or 10")
    policy = await check_access(user, table="intraday")
    sym = symbol.upper()
    _, blocked = policy.filter_symbols([sym])
    if blocked:
        raise HTTPException(status_code=403, detail=f"Không có quyền truy vấn {sym}")
    bars = fetch_intraday_ohlc(sym, resolution)
    return {
        "symbol": sym,
        "resolution": resolution,
        "market_open": is_market_open(),
        "bars": bars,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return (_STATIC / "index.html").read_text(encoding="utf-8")
