"""TTS API 엔드포인트"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from abuddy.services.tts import VOICE_MAP, get_tts_url

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("")
async def tts_endpoint(
    text: str = Query(..., max_length=2000),
    voice: str = Query("ko-female"),
):
    """
    텍스트 → MP3 presigned URL 반환.

    voice: ko-female | ko-male | en-female | en-male
    """
    if voice not in VOICE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown voice: {voice}. Valid: {list(VOICE_MAP)}")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is empty")

    url = await get_tts_url(text.strip(), voice)
    return JSONResponse({"url": url})
