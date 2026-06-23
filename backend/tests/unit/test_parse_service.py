import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

from tests.fixtures.mock_parse_result import build_mock_parse_result

try:
    from app.parse import service as parse_service
    from app.parse import schemas as rag_schemas
except ImportError:
    parse_service = None
    rag_schemas = None


FUNCTION_NAMES = {
    "parse_readme",
    "analyze_directory",
    "find_entry_points",
    "tag_config_files",
    "extract_run_commands",
    "detect_tech_stack",
    "chunk_by_ast",
    "analyze_imports",
    "build_hierarchical_summary",
    "run_structure_agent",
    "run_parse_pipeline",
}


def _has(*names: str) -> bool:
    """parse_service에 주어진 함수들이 모두 구현돼 있는지 (작업 단위별 게이팅용)."""
    return (
        parse_service is not None
        and rag_schemas is not None
        and all(hasattr(parse_service, name) for name in names)
    )


PARSE_READY = _has(*FUNCTION_NAMES)
FIXTURE_REPO = Path(__file__).resolve().parents[1] / "fixtures" / "sample_repo"


class ParseServiceFeatureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # 모든 기능 테스트가 analyze_directory(B-202) 결과(self.files)에 의존한다.
        if not _has("analyze_directory"):
            self.skipTest("analyze_directory(B-202) 미구현")
        self.files = await parse_service.analyze_directory(str(FIXTURE_REPO))

    async def test_analyze_directory_uses_repository_relative_paths(self):
        paths = {item.path for item in self.files}
        self.assertIn("backend/app/main.py", paths)
        self.assertIn("package.json", paths)
        self.assertTrue(all(not Path(path).is_absolute() for path in paths))

    @unittest.skipUnless(_has("find_entry_points"), "find_entry_points(B-203) 미구현")
    async def test_entry_points_prioritize_main_before_index(self):
        entry_points = await parse_service.find_entry_points(self.files)
        self.assertIn("backend/app/main.py", entry_points)
        self.assertLess(
            entry_points.index("backend/app/main.py"),
            entry_points.index("frontend/src/index.ts"),
        )

    @unittest.skipUnless(_has("tag_config_files"), "tag_config_files(B-204) 미구현")
    async def test_config_files_are_tagged(self):
        tagged = await parse_service.tag_config_files(self.files)
        by_path = {item.path: item for item in tagged}
        for path in ("package.json", "requirements.txt", "Dockerfile"):
            self.assertTrue((by_path[path].metadata or {}).get("is_config"))

    @unittest.skipUnless(_has("extract_run_commands"), "extract_run_commands(B-205) 미구현")
    async def test_run_commands_are_extracted_from_known_manifests(self):
        commands = await parse_service.extract_run_commands(self.files)
        self.assertTrue(any("npm run dev" in command for command in commands))
        self.assertTrue(any("pip install" in command for command in commands))

    @unittest.skipUnless(_has("detect_tech_stack"), "detect_tech_stack(B-206) 미구현")
    async def test_tech_stack_is_detected_from_dependencies(self):
        stack = await parse_service.detect_tech_stack(self.files)
        self.assertIn("FastAPI", stack)
        self.assertIn("Next.js", stack)

    @unittest.skipUnless(_has("chunk_by_ast"), "chunk_by_ast(B-207) 미구현")
    async def test_ast_chunking_keeps_line_and_type_metadata(self):
        chunked = await parse_service.chunk_by_ast(self.files)
        code_files = [item for item in chunked if item.path.endswith((".py", ".ts"))]
        self.assertTrue(code_files)
        self.assertTrue(any(item.chunks for item in code_files))
        for item in code_files:
            for chunk in item.chunks:
                self.assertLessEqual(chunk.start_line, chunk.end_line)
                self.assertIn(chunk.chunk_type, {"function", "class", "module", "other"})

    @unittest.skipUnless(_has("analyze_imports"), "analyze_imports(B-208) 미구현")
    async def test_imports_are_normalized_to_repository_paths(self):
        analyzed = await parse_service.analyze_imports(self.files)
        by_path = {item.path: item for item in analyzed}
        self.assertIn("backend/app/service.py", by_path["backend/app/main.py"].imports)
        self.assertIn("backend/app/config.py", by_path["backend/app/service.py"].imports)

    @unittest.skipUnless(_has("analyze_imports"), "analyze_imports(B-208) 미구현")
    async def test_imports_resolve_from_package_import_module(self):
        # `from pkg import mod` / `from . import mod`(import한 이름이 모듈인 형태)도
        # 내부 파일로 정규화되어야 한다 (PR #73 리뷰 보완).
        files = [
            rag_schemas.ParsedFile(
                path="pkg/a.py",
                file_type="FILE",
                depth=1,
                content="from . import c\nfrom backend.app import service\n",
            ),
            rag_schemas.ParsedFile(path="pkg/c.py", file_type="FILE", depth=1, content="x = 1\n"),
            rag_schemas.ParsedFile(
                path="backend/app/service.py", file_type="FILE", depth=2, content="y = 2\n"
            ),
        ]
        analyzed = await parse_service.analyze_imports(files)
        by_path = {item.path: item for item in analyzed}
        self.assertIn("pkg/c.py", by_path["pkg/a.py"].imports)
        self.assertIn("backend/app/service.py", by_path["pkg/a.py"].imports)

    @unittest.skipUnless(_has("parse_readme"), "parse_readme(B-201) 미구현")
    async def test_missing_readme_returns_none_without_model_call(self):
        empty = FIXTURE_REPO / "frontend"
        self.assertIsNone(await parse_service.parse_readme(str(empty)))

    @unittest.skipUnless(_has("parse_readme"), "parse_readme(B-201) 미구현")
    async def test_existing_readme_returns_summary(self):
        # README가 있으면 비어있지 않은 요약을 반환. LLM 응답 문구에 의존하지 않도록
        # _summarize_with_llm을 None으로 mock(휴리스틱 폴백 고정)해 결정성 확보. (#74 리뷰 보완)
        from app.parse import readme as readme_module

        with patch.object(readme_module, "_summarize_with_llm", AsyncMock(return_value=None)):
            summary = await parse_service.parse_readme(str(FIXTURE_REPO))
        self.assertIsInstance(summary, str)
        self.assertTrue(summary.strip())


@unittest.skipUnless(PARSE_READY, "PARSE 파이프라인 진입점이 아직 구현되지 않음")
class ParsePipelineOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_returns_the_shared_parse_result_contract(self):
        expected = build_mock_parse_result()
        with (
            patch.object(parse_service, "parse_readme", AsyncMock(return_value=expected.readme_summary)),
            patch.object(parse_service, "analyze_directory", AsyncMock(return_value=expected.files)),
            patch.object(parse_service, "find_entry_points", AsyncMock(return_value=expected.entry_points)),
            patch.object(parse_service, "tag_config_files", AsyncMock(return_value=expected.files)),
            patch.object(parse_service, "extract_run_commands", AsyncMock(return_value=expected.run_commands)),
            patch.object(parse_service, "detect_tech_stack", AsyncMock(return_value=expected.tech_stack)),
            patch.object(parse_service, "chunk_by_ast", AsyncMock(return_value=expected.files)),
            patch.object(parse_service, "analyze_imports", AsyncMock(return_value=expected.files)),
            patch.object(
                parse_service,
                "build_hierarchical_summary",
                AsyncMock(return_value=(expected.files, expected.master_summary)),
            ),
            patch.object(parse_service, "run_structure_agent", AsyncMock(return_value=expected.files)),
        ):
            result = await parse_service.run_parse_pipeline(
                job_id=expected.job_id,
                repo_name=expected.repo_name,
                owner=expected.owner,
                branch=expected.branch,
                clone_path=str(FIXTURE_REPO),
            )
        self.assertIsInstance(result, rag_schemas.ParseResult)
        self.assertEqual(result.job_id, expected.job_id)
        self.assertEqual(result.master_summary, expected.master_summary)
