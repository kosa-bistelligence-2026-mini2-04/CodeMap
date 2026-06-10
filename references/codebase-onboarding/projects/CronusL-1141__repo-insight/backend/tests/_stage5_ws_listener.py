"""Stage 5 real e2e WS listener helper. Connects to /ws/progress/{job_id}, collects
events until completion or failure, and prints summary. Not a pytest test file."""
import asyncio
import json
import sys
import time

import websockets


async def listen(job_id: str, timeout_s: float = 150.0) -> dict:
    url = f"ws://127.0.0.1:8770/ws/progress/{job_id}"
    t0 = time.monotonic()
    events: list = []
    terminal: dict | None = None
    async with websockets.connect(url, ping_interval=None, max_size=None) as ws:
        while True:
            elapsed = time.monotonic() - t0
            if elapsed > timeout_s:
                return {"terminal": None, "events": events, "elapsed": elapsed, "reason": "timeout"}
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s - elapsed)
            except asyncio.TimeoutError:
                return {"terminal": None, "events": events, "elapsed": elapsed, "reason": "recv_timeout"}
            except websockets.ConnectionClosed:
                break
            try:
                ev = json.loads(raw)
            except Exception:
                continue
            events.append(ev)
            et = ev.get("type") or ev.get("event")
            if et in ("completed", "failed", "done", "error"):
                terminal = ev
                break
            st = ev.get("status")
            if st in ("completed", "failed"):
                terminal = ev
                break
    return {"terminal": terminal, "events": events, "elapsed": time.monotonic() - t0, "reason": "ok"}


if __name__ == "__main__":
    job_id = sys.argv[1]
    timeout_s = float(sys.argv[2]) if len(sys.argv) > 2 else 150.0
    out = asyncio.run(listen(job_id, timeout_s))
    print(json.dumps(out, ensure_ascii=False, default=str))
