import starkbank
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.stark_client import get_project

import sqlite3 
from pathlib import Path

from app.event_store import save_event

router = APIRouter()

DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "events.db"

@router.post("/webhook/starkbank")
async def receive_starkbank_webhook(request: Request):
    signature = request.headers.get("Digital-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Digital-Signature header")
    
    body = await request.body()

    try:
        content = body.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Request body must use UTF-8")

    project = get_project()

    try:
        event = await run_in_threadpool(
            starkbank.event.parse,
            content=content,
            signature=signature,
            user=project
        )
    except starkbank.error.InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    try:
        saved = await run_in_threadpool(
            save_event, 
            database_path=DATABASE_PATH,
            event_id=event.id,
            content=content
        )
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Could not store event")
    
    return {"event_id": event.id, "status": "received" if saved else "duplicate"}