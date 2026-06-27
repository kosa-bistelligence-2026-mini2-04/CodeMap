"""
G3-A 팀 운영 순수 가드 헬퍼

DB/인프라 의존 없이 단위 테스트 가능한 순수 함수만 포함한다.
"""

import uuid

from fastapi import HTTPException


# ──────────────────────────────────────────────
# 마지막 owner 보호 가드
# ──────────────────────────────────────────────
def guard_last_owner(owner_count: int) -> None:
    """active owner 수가 1 이하면 추방/탈퇴를 거부한다."""
    if owner_count <= 1:
        raise HTTPException(status_code=409, detail="LAST_OWNER_CANNOT_LEAVE")


# ──────────────────────────────────────────────
# 자기 자신 추방 방지 가드
# ──────────────────────────────────────────────
def guard_not_self(caller_id: uuid.UUID, target_id: uuid.UUID) -> None:
    """호출자 본인을 추방 API로 제거하지 못하게 보호한다."""
    if caller_id == target_id:
        raise HTTPException(status_code=400, detail="CANNOT_REMOVE_SELF")
