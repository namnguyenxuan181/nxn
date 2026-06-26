from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from ai_platform.chat import stream_chat
from ai_platform.data_access import get_all_symbols
from ai_platform.report import generate_report

app = FastAPI(title="NXN AI Platform")

_STATIC = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str
    history: List[Dict] = []


@app.get("/api/symbols")
def symbols():
    return get_all_symbols()


@app.post("/api/chat")
def chat(req: ChatRequest):
    def generate():
        for chunk in stream_chat(req.message, req.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/report/{symbol}")
def report(symbol: str):
    result = generate_report(symbol.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data available for {symbol.upper()}")
    return result


@app.get("/", response_class=HTMLResponse)
def index():
    path = _STATIC / "index.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "<h1>NXN AI Platform — frontend not yet built</h1>"
