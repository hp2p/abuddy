"""
CCA/skilljar/ 아래 모든 .md 파일에서 "## Header Navigation" 섹션 제거

- 섹션 내용이 아래 기준 텍스트와 일치(공백 무시)하면 삭제
- 내용이 다르면 삭제하지 않고 경고 출력

사용법:
  uv run scripts/clean_skilljar_md.py
"""

import re
from pathlib import Path

MD_DIR = Path(__file__).parent.parent / "CCA" / "skilljar"

# "## Header Navigation" 부터 다음 "##" 헤딩 직전까지 (또는 파일 끝까지)
SECTION_PATTERN = re.compile(
    r"(\n## Header Navigation\n.*?)(?=\n## |\Z)", re.DOTALL
)

# 삭제해도 되는 기준 텍스트 (공백 정규화 후 비교)
EXPECTED_LINES = [
    "## Header Navigation",
    "[Anthropic Academy](https://www.anthropic.com/learn)",
    "[Courses](https://anthropic.skilljar.com)",
    "- My Profile",
    "[My Profile](https://anthropic.skilljar.com/accounts/profile)",
    "- Sign Out",
    "[Sign Out](https://anthropic.skilljar.com/auth/logout)",
    "[Anthropic Academy](https://www.anthropic.com/learn)",
    "[Courses](https://anthropic.skilljar.com)",
    "[My Profile](https://anthropic.skilljar.com/accounts/profile)",
    "[Sign Out](https://anthropic.skilljar.com/auth/logout)",
]


def normalize(text: str) -> list[str]:
    """각 줄 strip 후 빈 줄 제거"""
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_expected(section_text: str) -> bool:
    return normalize(section_text) == EXPECTED_LINES


def clean_file(path: Path) -> tuple[str, str | None]:
    """
    Returns:
      ("deleted", None)   — 삭제 성공
      ("skipped", diff)   — 내용 달라서 스킵, diff는 실제 내용
      ("unchanged", None) — 섹션 없음
    """
    text = path.read_text(encoding="utf-8")
    match = SECTION_PATTERN.search(text)
    if not match:
        return "unchanged", None

    section = match.group(1)
    if is_expected(section):
        cleaned = SECTION_PATTERN.sub("", text)
        path.write_text(cleaned, encoding="utf-8")
        return "deleted", None
    else:
        return "skipped", section.strip()


def main():
    files = sorted(MD_DIR.rglob("*.md"))
    deleted = skipped = 0

    for f in files:
        status, diff = clean_file(f)
        rel = f.relative_to(MD_DIR)
        if status == "deleted":
            deleted += 1
            print(f"  [삭제] {rel}")
        elif status == "skipped":
            skipped += 1
            print(f"  [스킵] {rel} — Header Navigation 내용이 다름:")
            for line in (diff or "").splitlines():
                print(f"         | {line}")

    print(f"\n✓ 삭제 {deleted}개 / 스킵 {skipped}개 / 전체 {len(files)}개")


if __name__ == "__main__":
    main()
