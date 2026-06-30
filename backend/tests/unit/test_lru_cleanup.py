import asyncio
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


from app.repo.models import AnalysisJob
from app.repo.repository import AnalysisJobRepository
from app.repo.service import AnalysisService
from app.chat.service import RepositoryChatService
from app.chat.schemas import ChatRunRequest


class TestLRUCleanupAndLazyLoading:
    @pytest.mark.anyio
    async def test_touch_last_accessed_updates_time(self):
        """touch_last_accessed 메소드가 last_accessed_at을 성공적으로 업데이트하는지 검증한다."""
        class FakeSession:
            pass

        mock_db = FakeSession()
        job_id = uuid.uuid4()
        
        # mock repository
        mock_job = MagicMock(spec=AnalysisJob)
        mock_job.last_accessed_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # update_last_accessed 모킹
        async def _fake_update_last_accessed(jid):
            mock_job.last_accessed_at = datetime.now(timezone.utc)
            return True

        with patch.object(AnalysisJobRepository, "update_last_accessed", AsyncMock(side_effect=_fake_update_last_accessed)):
            from app.common.access import touch_last_accessed
            touch_last_accessed(mock_db, job_id)
            await asyncio.sleep(0.1)  # 백그라운드 갱신 태스크 대기
            # 최근 접근 시각이 최신(1분 이내)으로 업데이트되었는지 확인
            assert (datetime.now(timezone.utc) - mock_job.last_accessed_at).total_seconds() < 10

    @pytest.mark.anyio
    async def test_disk_usage_lru_cleanup(self):
        """디스크 용량이 임계치를 초과할 때 LRU 기준으로 프로젝트 디렉토리가 지워지는지 검증한다."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        # 3개의 가상 AnalysisJob 생성 (마지막 접근 시각이 서로 다름)
        job1 = MagicMock(spec=AnalysisJob)
        job1.id = uuid.uuid4()
        job1.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=3)
        
        job2 = MagicMock(spec=AnalysisJob)
        job2.id = uuid.uuid4()
        job2.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=2)
        
        job3 = MagicMock(spec=AnalysisJob)
        job3.id = uuid.uuid4()
        job3.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=1)

        # DB execute 결과 모킹 (오래된 순으로 정렬되어 반환)
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [job1, job2, job3]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        service = AnalysisService(mock_db)

        # 디스크 용량 모킹 (최초 85% -> 두 번째 호출 시 68%로 떨어지게 모킹)
        disk_usage_call_count = 0
        def fake_disk_usage(path):
            nonlocal disk_usage_call_count
            disk_usage_call_count += 1
            if disk_usage_call_count == 1:
                return (100, 85, 15)  # 85% 사용량 (임계치 초과)
            return (100, 65, 35)      # 65% 사용량 (정리 후 안전 상태)

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("shutil.disk_usage", side_effect=fake_disk_usage),
            patch("app.repo.service.settings") as mock_settings,
            patch("app.repo.service._safe_remove", MagicMock()) as mock_safe_remove,
            patch("app.repo.service._remove_empty_parent", MagicMock())
        ):
            mock_settings.CLONE_BASE_DIR = tmpdir
            
            # 각각의 jobs 디렉토리 모의 생성
            import os
            for j in [job1, job2, job3]:
                os.makedirs(os.path.join(tmpdir, str(j.id), "repo"), exist_ok=True)

            # 디스크 자동 클린업 기동
            final_percent = await service.auto_cleanup_disk_usage(threshold_percent=80.0, target_percent=70.0)
            
            # 최종 점유율이 70% 이하(65%)로 떨어졌는지 확인
            assert final_percent == 65.0
            # 85% -> 65%로 떨어지며 첫 번째 job(가장 오래된 job1)의 디렉토리가 삭제 대상이 되었는지 확인
            mock_safe_remove.assert_called_once()
            called_path = mock_safe_remove.call_args[0][0]
            assert str(job1.id) in str(called_path)

    @pytest.mark.anyio
    async def test_lazy_loading_recovery_during_chat(self):
        """챗 생성 시점에 로컬 캐시 누락(Cache Miss)이 감지되면 자동 재클론 복구가 일어나는지 검증한다."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo_id = uuid.uuid4()
        
        # mock job
        mock_job = MagicMock(spec=AnalysisJob)
        mock_job.id = repo_id
        mock_job.repo_url = "https://github.com/test/repo"
        mock_job.branch = "main"

        # mock request
        mock_request = ChatRunRequest(
            sessionId=uuid.uuid4(),
            question="test question",
            mode="lite"
        )

        chat_service = RepositoryChatService(mock_db)

        # Mocking db queries and methods
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(AnalysisJobRepository, "get_job_by_id", AsyncMock(return_value=mock_job)),
            patch.object(AnalysisJobRepository, "update_last_accessed", AsyncMock()),
            patch.object(RepositoryChatService, "can_access_job", AsyncMock(return_value=True)),
            patch("app.chat.service.get_settings") as mock_settings,
            patch("app.repo.service.AnalysisService.restore_workspace", AsyncMock()) as mock_restore
        ):
            mock_settings.return_value.CLONE_BASE_DIR = tmpdir
            
            # 캐시가 없는 상태(clone_path 미존재)에서 prepare_run_context 호출
            job, mode, clone_path = await chat_service.prepare_run_context(repo_id, mock_request)
            
            # 1. 자동 복구 공개 메소드 restore_workspace 호출 확인
            mock_restore.assert_called_once_with(repo_id)
            assert job == mock_job
            assert mode == "lite"
            assert str(repo_id) in clone_path

    @pytest.mark.anyio
    async def test_disk_usage_lru_cleanup_excludes_local_uploads(self):
        """디스크 클린업 후보 선정 시 local-upload:// 접두사 주소를 가진 잡은 오름차순(LRU)에 관계없이 제외되는지 검증한다."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        # 1. 로컬 업로드 잡 (가장 오래됨)
        job_local = MagicMock(spec=AnalysisJob)
        job_local.id = uuid.uuid4()
        job_local.repo_url = "local-upload://tmp-abcdef"
        job_local.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=5)
        
        # 2. 일반 깃허브 잡 (더 최신임)
        job_git = MagicMock(spec=AnalysisJob)
        job_git.id = uuid.uuid4()
        job_git.repo_url = "https://github.com/user/project"
        job_git.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=2)

        # DB execute 결과 모킹 (실제 쿼리 결과처럼 모킹 - local-upload는 where절에서 탈락하여 git job만 반환)
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [job_git]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        service = AnalysisService(mock_db)

        # 디스크 용량 모킹 (임계 초과 -> 정리 후 안전)
        disk_usage_call_count = 0
        def fake_disk_usage(path):
            nonlocal disk_usage_call_count
            disk_usage_call_count += 1
            if disk_usage_call_count == 1:
                return (100, 85, 15)  # 85% 사용량 (임계치 초과)
            return (100, 65, 35)      # 65% 사용량 (정리 후 안전)

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("shutil.disk_usage", side_effect=fake_disk_usage),
            patch("app.repo.service.settings") as mock_settings,
            patch("app.repo.service._safe_remove", MagicMock()) as mock_safe_remove,
            patch("app.repo.service._remove_empty_parent", MagicMock())
        ):
            mock_settings.CLONE_BASE_DIR = tmpdir
            
            # jobs 디렉토리 생성
            import os
            for j in [job_local, job_git]:
                os.makedirs(os.path.join(tmpdir, str(j.id), "repo"), exist_ok=True)

            # 디스크 자동 클린업 기동
            final_percent = await service.auto_cleanup_disk_usage(threshold_percent=80.0, target_percent=70.0)
            
            # 최종 용량이 떨어졌고, 가장 오래된 local_upload 대신 git job이 삭제 대상으로 검출 및 매칭되었는지 검증
            assert final_percent == 65.0
            mock_safe_remove.assert_called_once()
            called_path = mock_safe_remove.call_args[0][0]
            assert str(job_git.id) in str(called_path)
            assert str(job_local.id) not in str(called_path)

