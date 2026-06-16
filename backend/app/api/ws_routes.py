from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws")
market_service = MarketDataService()

# Keep only one broadcast loop per unique subscription set (symbols+mode).
_active_tasks: Dict[str, asyncio.Task] = {}
_subscribers: Dict[str, Set[WebSocket]] = {}

# In-memory price store per subscription key.
_ram_store: Dict[str, Dict] = {}

# Per-subscription yfinance rate limiter: minimum interval between fetches.
_FETCH_COOLDOWN = 5.0


def _key(symbols: List[str], mode: str, interval: Optional[str], period: Optional[str]) -> str:
    sym = ",".join(sorted(symbols))
    return f"{mode}|{interval or ''}|{period or ''}|{sym}"


def _sub_key_from_init(init_payload: dict) -> str:
    symbols = init_payload.get("symbols") or []
    mode = init_payload.get("mode") or "daily"
    interval = init_payload.get("interval")
    period = init_payload.get("period")
    symbols = sorted(str(s).upper().strip() for s in symbols if str(s).strip())
    return _key(symbols, mode, interval, period)


def _sanitize_error(exc: Exception) -> str:
    msg = str(exc)
    if not msg:
        return "An internal error occurred"
    return msg[:200]


async def _broadcast_loop(sub_key: str, symbols: List[str], mode: str, interval: Optional[str], period: Optional[str]):
    """Poll yfinance periodically and push latest prices. Fully in-memory, no disk I/O."""
    try:
        while True:
            subs = _subscribers.get(sub_key)
            if not subs:
                break

            price_data, errors = await market_service.fetch_prices(
                symbols,
                mode=mode,
                interval=interval,
                period=period,
                refresh=True,
            )

            _ram_store.pop(sub_key, None)
            _ram_store[sub_key] = {
                "price_data": price_data,
                "errors": errors,
                "last_refresh": asyncio.get_event_loop().time(),
            }

            live_prices = market_service.live_prices_from_data(price_data, mode=mode)

            sent = {p.get("symbol"): p for p in live_prices if p and p.get("symbol")}
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).isoformat()

            for sym in symbols:
                sym_up = str(sym).upper().strip()
                if sym_up not in sent:
                    sent[sym_up] = {
                        "symbol": sym_up,
                        "price": 0.0,
                        "change_pct": 0.0,
                        "last_updated": ts,
                        "source": market_service.data_source,
                    }

            live_prices_ordered = [sent[str(s).upper().strip()] for s in symbols if str(s).strip()]

            payload = {
                "type": "live_prices",
                "mode": mode,
                "data_source": market_service.data_source,
                "warnings": market_service.warnings + errors,
                "live_prices": live_prices_ordered,
            }

            msg = json.dumps(payload, separators=(",", ":"))

            dead: List[WebSocket] = []
            for ws in list(subs):
                try:
                    await ws.send_text(msg)
                except WebSocketDisconnect:
                    dead.append(ws)
                except Exception:
                    dead.append(ws)

            if dead:
                for ws in dead:
                    subs.discard(ws)

            await asyncio.sleep(_FETCH_COOLDOWN)

    finally:
        _active_tasks.pop(sub_key, None)
        _ram_store.pop(sub_key, None)


@router.websocket("/prices")
async def websocket_prices(websocket: WebSocket):
    await websocket.accept()

    try:
        init = await websocket.receive_text()
        init_payload = json.loads(init)
        symbols = init_payload.get("symbols") or []
        mode = init_payload.get("mode") or "daily"
        interval = init_payload.get("interval")
        period = init_payload.get("period")

        symbols = [str(s).upper().strip() for s in symbols if str(s).strip()]
        if len(symbols) < 1:
            safe_msg = json.dumps({"type": "error", "message": "At least one symbol is required"})
            await websocket.send_text(safe_msg)
            await websocket.close(code=1008)
            return

        sub_key = _key(symbols, mode, interval, period)
        _subscribers.setdefault(sub_key, set()).add(websocket)

        if sub_key not in _active_tasks:
            _active_tasks[sub_key] = asyncio.create_task(
                _broadcast_loop(sub_key, symbols, mode, interval, period)
            )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error for key %s: %s", _sub_key_from_init(init_payload) if 'init_payload' in dir() else "unknown", _sanitize_error(exc))
    finally:
        for subs in _subscribers.values():
            subs.discard(websocket)

