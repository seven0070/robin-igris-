"""FastAPI voice bridge: TTS (+ optional chat fallback) for the companion stage."""

from __future__ import annotations

import io
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="Robin Igris Voice Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeechRequest(BaseModel):
    input: str = Field(..., min_length=1)
    voice: str = "alloy"
    format: Literal["mp3", "wav"] = "mp3"


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "tts": os.getenv("TTS_PROVIDER", "edge"),
        "hermes": os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642/v1"),
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
    # Keep TTS snappy for avatar lip-sync turns
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


def main() -> None:
    import uvicorn

    host = os.getenv("VOICE_HOST", "127.0.0.1")
    port = int(os.getenv("VOICE_PORT", "8787"))
    uvicorn.run("robin_igris.voice_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
