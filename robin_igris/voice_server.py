"""FastAPI voice bridge + optional companion UI for USB portable mode."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="Robin Igris Voice Bridge", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_COMPANION_MOUNTED = False


class SpeechRequest(BaseModel):
    input: str = Field(..., min_length=1)
    voice: str = "alloy"
    format: Literal["mp3", "wav"] = "mp3"


@app.get("/health")
def health() -> dict:
    dist = os.getenv("ROBIN_COMPANION_DIST", "")
    return {
        "ok": True,
        "tts": os.getenv("TTS_PROVIDER", "edge"),
        "hermes": os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642/v1"),
        "companion": bool(dist and (Path(dist) / "index.html").exists()),
        "usb_root": os.getenv("ROBIN_USB_ROOT"),
    }


def _edge_tts(text: str, voice: str | None = None) -> bytes:
    import asyncio

    import edge_tts

    voice_id = voice or os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text, voice_id)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    return asyncio.run(_run())


def _openai_tts(text: str, voice: str, fmt: str) -> bytes:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    with client.audio.speech.with_streaming_response.create(
        model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        voice=voice,
        input=text,
        response_format=fmt,
    ) as response:
        return response.read()


@app.post("/v1/audio/speech")
def speech(body: SpeechRequest) -> Response:
    text = body.input.strip()
    if not text:
        raise HTTPException(400, "empty input")
    if len(text) > 4000:
        text = text[:4000]

    provider = os.getenv("TTS_PROVIDER", "edge").lower()
    try:
        if provider == "openai":
            audio = _openai_tts(text, body.voice, body.format)
            media = "audio/mpeg" if body.format == "mp3" else "audio/wav"
        else:
            audio = _edge_tts(text)
            media = "audio/mpeg"
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"TTS failed: {exc}") from exc

    if not audio:
        raise HTTPException(502, "TTS returned empty audio")
    return Response(content=audio, media_type=media)


def _hermes_root() -> str:
    return os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642/v1").rstrip("/").removesuffix(
        "/v1"
    )


def _hermes_key() -> str:
    return os.getenv("HERMES_API_KEY", os.getenv("VITE_HERMES_API_KEY", "robin-igris-dev"))


@app.api_route("/hermes/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def hermes_proxy(path: str, request: Request) -> Response:
    url = f"{_hermes_root()}/{path}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length"}
    }
    headers["Authorization"] = f"Bearer {_hermes_key()}"
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.request(request.method, url, content=body, headers=headers)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": str(exc), "hint": "Is hermes gateway running on the USB kit?"},
            status_code=502,
        )
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type"),
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    payload: dict[str, Any] = await request.json()
    messages = payload.get("messages") or []
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{_hermes_root()}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {_hermes_key()}",
                    "Content-Type": "application/json",
                    "X-Hermes-Session-Key": "robin-igris-usb",
                },
                json=payload,
            )
            if r.is_success:
                return Response(
                    content=r.content,
                    status_code=r.status_code,
                    media_type="application/json",
                )
    except Exception:
        pass

    user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user = m.get("content") or ""
            break
    try:
        from robin_igris.system3.monitor import ExecutiveMonitor

        root = os.getenv("ROBIN_SYSTEM3_ROOT")
        kwargs = {}
        if root:
            kwargs["data_root"] = Path(root)
        reply = ExecutiveMonitor(**kwargs).wake(user or "Hello", kind="user")
    except Exception:
        try:
            from robin_igris.agent import Agent

            reply = Agent().chat(user or "Hello")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"No brain available: {exc}") from exc

    return JSONResponse(
        {
            "id": "robin-usb",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }
            ],
        }
    )


def mount_companion() -> None:
    global _COMPANION_MOUNTED
    if _COMPANION_MOUNTED or os.getenv("ROBIN_SERVE_COMPANION", "0") != "1":
        return
    dist = Path(os.getenv("ROBIN_COMPANION_DIST", "companion/dist")).resolve()
    if not (dist / "index.html").exists():
        return

    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(dist / "index.html")

    _COMPANION_MOUNTED = True


mount_companion()


def main() -> None:
    import uvicorn

    mount_companion()
    host = os.getenv("VOICE_HOST", "127.0.0.1")
    port = int(os.getenv("VOICE_PORT", "8787"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
