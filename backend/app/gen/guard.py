"""
DOCS-GUARD-B-201: 민감정보 마스킹 모듈

가이드북 Markdown 원문을 스캔하여 API 키·토큰·비밀번호 등
민감정보를 탐지하고 [MASKED]로 대체한다.

CPU-bound 정규식 작업은 asyncio.to_thread 로 별도 스레드에서 실행한다.
"""

import asyncio
import re
from dataclasses import dataclass, field


# ──────────────────────────────────────────────
# 결과 타입 정의
# ──────────────────────────────────────────────
@dataclass
class DetectedPattern:
    '''단일 탐지 패턴 항목'''

    type: str
    location: str = "document"


@dataclass
class MaskResult:
    '''mask_sensitive_content() 반환 값'''

    masked_content: str
    detected_count: int
    detected_patterns: list[DetectedPattern] = field(default_factory=list)


# ──────────────────────────────────────────────
# 민감정보 탐지 패턴 목록
# 길이 상한을 명시해 ReDoS 위험을 방어한다.
# ──────────────────────────────────────────────
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "aws_access_key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ),
    (
        "openai_key",
        re.compile(r"sk-[a-zA-Z0-9]{32,64}"),
    ),
    (
        "github_token",
        re.compile(r"gh[porus]_[A-Za-z0-9]{20,64}"),
    ),
    (
        "jwt_token",
        re.compile(
            r"eyJ[a-zA-Z0-9_-]{1,1000}"
            r"\.eyJ[a-zA-Z0-9_-]{1,1000}"
            r"\.[a-zA-Z0-9_-]{1,1000}"
        ),
    ),
    (
        "db_connection",
        re.compile(
            r"(?i)(postgresql|mysql|sqlite|mongodb)"
            r"://[^@\s]{1,200}@[^\s]{1,200}"
        ),
    ),
    (
        "password_literal",
        re.compile(
            r'(?i)(password|passwd|pwd|secret)'
            r'\s*[=:]\s*["\']?[\w!@#$%^&*()\-]{4,64}["\']?'
        ),
    ),
    (
        "api_key_literal",
        re.compile(
            r'(?i)(api_key|apikey|api-key|access_token|auth_token)'
            r'\s*[=:]\s*["\']?[\w\-]{8,128}["\']?'
        ),
    ),
]


# ──────────────────────────────────────────────
# 동기 마스킹 함수 (스레드 풀에서 실행)
# ──────────────────────────────────────────────
def _mask_content_sync(content: str) -> MaskResult:
    '''
    정규식 패턴으로 민감정보를 탐지해 [MASKED]로 대체한다.

    동기 함수 — asyncio.to_thread() 로 호출한다.
    '''
    detected: list[DetectedPattern] = []
    masked = content

    for pattern_type, pattern in _PATTERNS:
        ## 람다 기본인수로 루프 변수 캡처 — 클로저 바인딩 오류 방지
        def replacer(m: re.Match[str], pt: str = pattern_type) -> str:
            detected.append(DetectedPattern(type=pt))
            return "[MASKED]"

        masked = pattern.sub(replacer, masked)

    ## 동일 패턴 타입은 중복 제거하여 detectedPatterns 리스트에 한 번만 표시
    seen: set[str] = set()
    unique_patterns: list[DetectedPattern] = []
    for d in detected:
        if d.type not in seen:
            seen.add(d.type)
            unique_patterns.append(d)

    return MaskResult(
        masked_content=masked,
        detected_count=len(detected),
        detected_patterns=unique_patterns,
    )


# ──────────────────────────────────────────────
# 퍼블릭 비동기 진입점
# ──────────────────────────────────────────────
async def mask_sensitive_content(content: str) -> MaskResult:
    '''
    CPU-bound 마스킹 작업을 별도 스레드로 격리 실행한다.

    asyncio 이벤트 루프 블로킹 방어 (CLAUDE.md §7 항목 4).
    '''
    return await asyncio.to_thread(_mask_content_sync, content)
