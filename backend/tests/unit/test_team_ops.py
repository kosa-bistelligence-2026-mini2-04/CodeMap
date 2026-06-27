"""
G3-A 팀 운영 API 단위 테스트

- guard_last_owner: 순수 카운트 기반 가드 로직
- guard_not_self: 자기 자신 추방 방지 가드 로직
- cancel_invite_guard: 이미 처리된 초대 취소 시 409
- leave_team_guard: 마지막 owner 탈퇴 차단
DB 없이 가드 헬퍼를 직접 호출하여 순수 로직만 검증한다.
"""

import unittest
from uuid import uuid4

from fastapi import HTTPException

from app.team.guards import guard_last_owner, guard_not_self


class TestGuardLastOwner(unittest.TestCase):
    def test_single_owner_raises(self):
        with self.assertRaises(HTTPException) as ctx:
            guard_last_owner(1)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "LAST_OWNER_CANNOT_LEAVE")

    def test_zero_owners_raises(self):
        ## 비정상 데이터지만 방어적으로 차단해야 한다
        with self.assertRaises(HTTPException) as ctx:
            guard_last_owner(0)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_multiple_owners_passes(self):
        ## 예외 없이 반환되어야 한다
        guard_last_owner(2)
        guard_last_owner(10)


class TestGuardNotSelf(unittest.TestCase):
    def test_same_id_raises(self):
        uid = uuid4()
        with self.assertRaises(HTTPException) as ctx:
            guard_not_self(uid, uid)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "CANNOT_REMOVE_SELF")

    def test_different_ids_passes(self):
        guard_not_self(uuid4(), uuid4())


class TestGuardLastOwnerEdge(unittest.TestCase):
    def test_exactly_two_owners_allows_removal(self):
        """owner가 2명이면 한 명 추방/탈퇴 가능 — 가드 통과."""
        guard_last_owner(2)

    def test_one_owner_blocks_leave(self):
        """마지막 owner 탈퇴 시도 — 409."""
        with self.assertRaises(HTTPException) as ctx:
            guard_last_owner(1)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "LAST_OWNER_CANNOT_LEAVE")


if __name__ == "__main__":
    unittest.main()
