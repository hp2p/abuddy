"""S3에 저장된 concept별 AWS 문서 로드."""
import re

import boto3
import orjson
from loguru import logger

from abuddy.config import settings

_DOC_KEY_PREFIX = "docs/"
_CHUNK_MAX_CHARS = 800
_HEADING_RE = re.compile(r"^#{1,4}\s+(.+)", re.MULTILINE)


def _s3():
    return boto3.client("s3", region_name=settings.aws_region)


# ── S3 로드 / 저장 ────────────────────────────────────────────

def load_doc(concept_id: str) -> dict | None:
    """S3에서 doc JSON 전체 반환. 없으면 None."""
    try:
        obj = _s3().get_object(
            Bucket=settings.s3_bucket,
            Key=f"{_DOC_KEY_PREFIX}{concept_id}.json",
        )
        return orjson.loads(obj["Body"].read())
    except Exception:
        return None


def load_doc_content(concept_id: str) -> str:
    """저장된 요약(summary) 반환. 요약 없으면 raw 첫 페이지로 fallback. 없으면 빈 문자열."""
    doc = load_doc(concept_id)
    if not doc:
        return ""
    if summary := doc.get("summary"):
        return summary
    # 요약 없는 경우 (구버전 데이터) 첫 페이지 raw content로 fallback
    pages = doc.get("pages", [])
    return pages[0]["content"] if pages else ""


def load_raw_pages(concept_id: str) -> str:
    """요약·청킹 생성용: 모든 페이지 raw content를 이어붙여 반환."""
    doc = load_doc(concept_id)
    if not doc:
        return ""
    parts = []
    for page in doc.get("pages", []):
        parts.append(f"## {page['title']}\n\n{page['content']}")
    return "\n\n---\n\n".join(parts)


def load_doc_chunks(concept_id: str) -> list[dict]:
    """저장된 chunks 배열 반환. 없으면 빈 리스트."""
    doc = load_doc(concept_id)
    if not doc:
        return []
    return doc.get("chunks", [])


def doc_exists(concept_id: str) -> bool:
    try:
        _s3().head_object(
            Bucket=settings.s3_bucket,
            Key=f"{_DOC_KEY_PREFIX}{concept_id}.json",
        )
        return True
    except Exception:
        return False


def save_doc(concept_id: str, data: dict) -> None:
    _s3().put_object(
        Bucket=settings.s3_bucket,
        Key=f"{_DOC_KEY_PREFIX}{concept_id}.json",
        Body=orjson.dumps(data, option=orjson.OPT_INDENT_2),
        ContentType="application/json",
    )
    logger.debug(f"Saved doc for concept_id={concept_id}")


# ── 청킹 ─────────────────────────────────────────────────────

def chunk_pages(pages: list[dict], concept_id: str) -> list[dict]:
    """
    pages 목록을 heading 경계 기준으로 청킹.

    규칙:
    - ## / ### / #### heading을 만나면 새 청크 시작
    - heading 없는 텍스트는 빈 줄(단락) 경계로 fallback 분리
    - 청크가 _CHUNK_MAX_CHARS 초과 시 단락 경계에서 추가 분리
    - 작은 청크는 그대로 유지 (병합 없음)
    """
    chunks = []
    for page_idx, page in enumerate(pages):
        raw_blocks = _split_by_heading(page["content"], page["title"])
        sized_blocks = _split_oversized(raw_blocks)
        for chunk_idx, (heading, content) in enumerate(sized_blocks):
            chunks.append({
                "chunk_id": f"{concept_id}_p{page_idx}_c{chunk_idx}",
                "page_index": page_idx,
                "chunk_index": chunk_idx,
                "heading": heading,
                "content": content,
                "char_count": len(content),
            })
    return chunks


def _split_by_heading(text: str, page_title: str) -> list[tuple[str, str]]:
    """텍스트를 heading 경계로 분리. (heading, content) 튜플 리스트 반환."""
    lines = text.splitlines()
    blocks: list[tuple[str, str]] = []
    current_heading = page_title
    current_lines: list[str] = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            # 이전 블록 저장
            content = "\n".join(current_lines).strip()
            if content:
                blocks.append((current_heading, content))
            current_heading = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 마지막 블록
    content = "\n".join(current_lines).strip()
    if content:
        blocks.append((current_heading, content))

    # heading이 하나도 없으면 단락 경계로 fallback
    if not blocks:
        return _split_by_paragraph(text, page_title)

    return blocks


def _split_by_paragraph(text: str, heading: str) -> list[tuple[str, str]]:
    """빈 줄 기준으로 단락 분리."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [(heading, p) for p in paragraphs]


def _split_oversized(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """_CHUNK_MAX_CHARS 초과 블록을 단락 경계에서 추가 분리."""
    result: list[tuple[str, str]] = []
    for heading, content in blocks:
        if len(content) <= _CHUNK_MAX_CHARS:
            result.append((heading, content))
            continue
        # 단락 경계로 분리
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        current_parts: list[str] = []
        current_len = 0
        for para in paragraphs:
            if current_len + len(para) > _CHUNK_MAX_CHARS and current_parts:
                result.append((heading, "\n\n".join(current_parts)))
                current_parts = [para]
                current_len = len(para)
            else:
                current_parts.append(para)
                current_len += len(para)
        if current_parts:
            result.append((heading, "\n\n".join(current_parts)))
    return result
