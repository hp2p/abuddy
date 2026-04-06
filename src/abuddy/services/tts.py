"""edge-tts 서버사이드 TTS + S3 영구 캐시"""

import hashlib
import tempfile
from pathlib import Path

import boto3
import edge_tts
from botocore.exceptions import ClientError
from loguru import logger

from abuddy.config import settings

_s3 = boto3.client("s3", region_name=settings.aws_region)

# 목소리 별칭 → 실제 voice name 매핑
VOICE_MAP = {
    "ko-female": settings.tts_voice_ko_female,  # ko-KR-SunHiNeural
    "ko-male": settings.tts_voice_ko_male,       # ko-KR-InJoonNeural
    "en-female": settings.tts_voice_en_female,   # en-US-AriaNeural
    "en-male": settings.tts_voice_en_male,       # en-US-GuyNeural
}


def _cache_key(text: str, voice: str) -> str:
    """S3 캐시 키 생성. 텍스트+목소리 해시로 고유 식별."""
    h = hashlib.sha256(f"{voice}:{text}".encode()).hexdigest()[:16]
    return f"{settings.tts_s3_prefix}{voice.replace(':', '-')}/{h}.mp3"


def _presigned_url(s3_key: str, expires: int = 3600) -> str:
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=expires,
    )


def _s3_exists(s3_key: str) -> bool:
    try:
        _s3.head_object(Bucket=settings.s3_bucket, Key=s3_key)
        return True
    except ClientError:
        return False
    except Exception:
        return False


async def get_tts_url(text: str, voice_alias: str = "ko-female") -> str:
    """
    텍스트를 읽어주는 MP3의 presigned URL 반환.
    S3 캐시 HIT → 즉시 반환. MISS → edge-tts 생성 후 저장.

    voice_alias: "ko-female" | "ko-male" | "en-female" | "en-male"
    """
    voice = VOICE_MAP.get(voice_alias, settings.tts_voice_ko_female)
    s3_key = _cache_key(text, voice_alias)

    # 캐시 HIT
    if _s3_exists(s3_key):
        logger.debug(f"TTS cache HIT: {s3_key}")
        return _presigned_url(s3_key)

    # 캐시 MISS → edge-tts 생성
    logger.info(f"TTS generating: voice={voice_alias}, text={text[:40]!r}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        _s3.put_object(
            Bucket=settings.s3_bucket,
            Key=s3_key,
            Body=audio_bytes,
            ContentType="audio/mpeg",
        )
        logger.info(f"TTS cached to S3: {s3_key} ({len(audio_bytes)} bytes)")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return _presigned_url(s3_key)
