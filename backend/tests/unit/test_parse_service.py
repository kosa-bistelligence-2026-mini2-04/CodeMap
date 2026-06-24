import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
    "extract_run_command_details",
    "detect_tech_stack",
    "detect_tech_stack_details",
    "analyze_language_composition",
    "chunk_by_ast",
    "analyze_imports",
    "build_file_map",
    "build_heatmap",
    "build_hierarchical_summary",
    "build_file_summaries",
    "build_folder_summaries",
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

    @unittest.skipUnless(_has("tag_config_files"), "tag_config_files(B-204) 미구현")
    async def test_config_files_include_ci_and_infra_configs(self):
        files = [
            rag_schemas.ParsedFile(
                path=".github/workflows/test.yml",
                file_type="FILE",
                depth=2,
                content="name: test\n",
            ),
            rag_schemas.ParsedFile(
                path="infra/main.tf",
                file_type="FILE",
                depth=1,
                content='resource "x" "y" {}\n',
            ),
            rag_schemas.ParsedFile(
                path="docker-compose.dev.yml",
                file_type="FILE",
                depth=0,
                content="services: {}\n",
            ),
        ]
        tagged = await parse_service.tag_config_files(files)
        self.assertTrue(all((item.metadata or {}).get("is_config") for item in tagged))

    @unittest.skipUnless(_has("extract_run_commands"), "extract_run_commands(B-205) 미구현")
    async def test_run_commands_are_extracted_from_known_manifests(self):
        commands = await parse_service.extract_run_commands(self.files)
        self.assertTrue(any("npm run dev" in command for command in commands))
        self.assertTrue(any("pip install" in command for command in commands))

    @unittest.skipUnless(_has("extract_run_command_details"), "extract_run_command_details(B-205) 미구현")
    async def test_run_command_details_include_install_run_and_build(self):
        commands = await parse_service.extract_run_command_details(self.files)
        self.assertEqual(commands.install, "npm install")
        self.assertEqual(commands.run, "npm run dev")
        self.assertEqual(commands.build, "docker compose build")

    @unittest.skipUnless(_has("extract_run_command_details"), "extract_run_command_details(B-205) 미구현")
    async def test_run_command_details_detect_python_entrypoint_without_node(self):
        files = [
            rag_schemas.ParsedFile(
                path="requirements.txt",
                file_type="FILE",
                depth=0,
                content="fastapi==0.115.0\n",
            ),
            rag_schemas.ParsedFile(
                path="app/main.py",
                file_type="FILE",
                depth=1,
                content="from fastapi import FastAPI\napp = FastAPI()\n",
            ),
        ]
        commands = await parse_service.extract_run_command_details(files)
        self.assertEqual(commands.install, "pip install -r requirements.txt")
        self.assertEqual(commands.run, "uvicorn app.main:app --reload")

    @unittest.skipUnless(_has("extract_run_command_details"), "extract_run_command_details(B-205) 미구현")
    async def test_run_command_details_does_not_use_api_router_as_app(self):
        files = [
            rag_schemas.ParsedFile(
                path="app/api.py",
                file_type="FILE",
                depth=1,
                content="from fastapi import APIRouter\nrouter = APIRouter()\n",
            ),
            rag_schemas.ParsedFile(
                path="requirements.txt",
                file_type="FILE",
                depth=0,
                content="fastapi==0.115.0\n",
            ),
        ]

        commands = await parse_service.extract_run_command_details(files)

        self.assertEqual(commands.install, "pip install -r requirements.txt")
        self.assertEqual(commands.run, "")

    @unittest.skipUnless(
        _has("extract_run_command_details", "extract_run_commands"),
        "extract_run_command_details/extract_run_commands(B-205) 미구현",
    )
    async def test_run_command_details_detects_compose_variant_file(self):
        files = [
            rag_schemas.ParsedFile(
                path="docker-compose.dev.yml",
                file_type="FILE",
                depth=0,
                content="services:\n  app:\n    image: nginx\n",
            )
        ]

        details = await parse_service.extract_run_command_details(files)
        commands = await parse_service.extract_run_commands(files)

        self.assertEqual(details.run, "docker compose up")
        self.assertEqual(details.build, "docker compose build")
        self.assertIn("docker compose up", commands)
        self.assertIn("docker compose build", commands)

    @unittest.skipUnless(_has("detect_tech_stack"), "detect_tech_stack(B-206) 미구현")
    async def test_tech_stack_is_detected_from_dependencies(self):
        stack = await parse_service.detect_tech_stack(self.files)
        self.assertIn("FastAPI", stack)
        self.assertIn("Next.js", stack)
        self.assertIn("PostgreSQL", stack)
        self.assertIn("React", stack)
        self.assertIn("SQLAlchemy", stack)
        self.assertIn("Python", stack)
        self.assertIn("Docker", stack)
        self.assertIn("Docker Compose", stack)
        self.assertIn("pgvector", stack)

    @unittest.skipUnless(_has("detect_tech_stack_details"), "detect_tech_stack_details(B-206) 미구현")
    async def test_tech_stack_details_include_source_version_and_category(self):
        details = await parse_service.detect_tech_stack_details(self.files)
        by_name = {item["name"]: item for item in details}

        self.assertEqual(by_name["Node.js"]["category"], "runtime")
        self.assertEqual(by_name["JavaScript"]["category"], "language")
        self.assertEqual(by_name["FastAPI"]["version"], "0.115.0")
        self.assertEqual(by_name["FastAPI"]["category"], "framework")
        self.assertEqual(by_name["FastAPI"]["source"], "requirements.txt")
        self.assertEqual(by_name["Next.js"]["version"], "16.0.0")
        self.assertEqual(by_name["Next.js"]["source"], "package.json")
        self.assertEqual(by_name["Python"]["version"], "3.12")
        self.assertEqual(by_name["Python"]["source"], "Dockerfile")
        self.assertEqual(by_name["PostgreSQL"]["version"], "16")
        self.assertEqual(by_name["PostgreSQL"]["source"], "docker-compose.yml")
        self.assertEqual(by_name["pgvector"]["category"], "extension")

    @unittest.skipUnless(_has("detect_tech_stack_details"), "detect_tech_stack_details(B-206) 미구현")
    async def test_tech_stack_details_cover_typescript_flutter_and_llm_fallback(self):
        from app.parse import manifest as manifest_module

        files = [
            rag_schemas.ParsedFile(
                path="package.json",
                file_type="FILE",
                depth=0,
                content='{"dependencies": {"solid-js": "1.9.0"}}',
            ),
            rag_schemas.ParsedFile(path="tsconfig.json", file_type="FILE", depth=0, content="{}"),
            rag_schemas.ParsedFile(
                path="pubspec.yaml",
                file_type="FILE",
                depth=0,
                content="dependencies:\n  flutter:\n    sdk: flutter\n",
            ),
            rag_schemas.ParsedFile(
                path="Dockerfile",
                file_type="FILE",
                depth=0,
                content="FROM golang:1.22-alpine\n",
            ),
            rag_schemas.ParsedFile(
                path="pyproject.toml",
                file_type="FILE",
                depth=0,
                content='[project]\ndependencies = ["litestar==2.9.0"]\n',
            ),
        ]
        llm_items = [
            {
                "name": "SolidJS",
                "version": "1.9.0",
                "category": "framework",
                "source": "package.json",
            },
            {
                "name": "Litestar",
                "version": "2.9.0",
                "category": "framework",
                "source": "pyproject.toml",
            },
        ]

        with patch.object(
            manifest_module,
            "_classify_unknown_tech_with_llm",
            AsyncMock(return_value=llm_items),
        ) as classify:
            details = await parse_service.detect_tech_stack_details(files)

        classify.assert_awaited_once()
        by_name = {item["name"]: item for item in details}
        self.assertEqual(by_name["TypeScript"]["category"], "language")
        self.assertEqual(by_name["Flutter"]["category"], "framework")
        self.assertEqual(by_name["Dart"]["category"], "language")
        self.assertEqual(by_name["Go"]["version"], "1.22")
        self.assertEqual(by_name["SolidJS"]["source"], "package.json")
        self.assertEqual(by_name["Litestar"]["source"], "pyproject.toml")

    @unittest.skipUnless(_has("analyze_language_composition"), "analyze_language_composition 미구현")
    async def test_language_composition_counts_lines_by_extension(self):
        files = [
            rag_schemas.ParsedFile(path="README.md", file_type="FILE", depth=0, content="# Title\nBody\n"),
            rag_schemas.ParsedFile(path="src/app.ts", file_type="FILE", depth=1, content="a\nb\nc\n"),
            rag_schemas.ParsedFile(path="api/main.py", file_type="FILE", depth=1, content="x\ny\n"),
            rag_schemas.ParsedFile(path="docker-compose.yml", file_type="FILE", depth=0, content="services:\n"),
            rag_schemas.ParsedFile(path="workflow.yml", file_type="FILE", depth=0, content="name: ci\n"),
            rag_schemas.ParsedFile(path="schema.sql", file_type="FILE", depth=0, content="select 1;\n"),
            rag_schemas.ParsedFile(path="empty.py", file_type="FILE", depth=0, content=None),
        ]

        composition = parse_service.analyze_language_composition(files)
        by_language = {item["language"]: item for item in composition}

        self.assertEqual(by_language["TypeScript"]["lines"], 3)
        self.assertEqual(by_language["Markdown"]["lines"], 2)
        self.assertEqual(by_language["Python"]["lines"], 2)
        self.assertEqual(by_language["Config"]["lines"], 1)
        self.assertEqual(by_language["YAML"]["lines"], 1)
        self.assertEqual(by_language["SQL"]["lines"], 1)
        self.assertAlmostEqual(sum(item["percentage"] for item in composition), 100.0, delta=0.2)

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

    @unittest.skipUnless(_has("analyze_imports"), "analyze_imports(B-208) 미구현")
    async def test_imports_resolve_monorepo_package_root(self):
        # 패키지 루트가 하위 디렉토리(backend/)에 있는 모노레포에서, 절대 import
        # `from app.service import run`이 backend/app/service.py로 접미사 해석돼야 한다 (#101).
        # 단, 단일 세그먼트(import json 등)는 외부 모듈 오탐 방지를 위해 해석하지 않는다.
        files = [
            rag_schemas.ParsedFile(
                path="backend/app/main.py",
                file_type="FILE",
                depth=2,
                content="from app.service import run\nimport json\n",
            ),
            rag_schemas.ParsedFile(
                path="backend/app/service.py", file_type="FILE", depth=2, content="def run(): ...\n"
            ),
            rag_schemas.ParsedFile(
                path="backend/app/json.py", file_type="FILE", depth=2, content="x = 1\n"
            ),
        ]
        analyzed = await parse_service.analyze_imports(files)
        imports = {item.path: item for item in analyzed}["backend/app/main.py"].imports
        self.assertIn("backend/app/service.py", imports)       # 다중 세그먼트 → 접미사 해석
        self.assertNotIn("backend/app/json.py", imports)       # 단일 세그먼트(import json) → 오탐 안 함

    @unittest.skipUnless(_has("build_file_map", "build_heatmap"), "Code Map 품질 보강 미구현")
    async def test_file_map_adds_imported_by_and_risk_score(self):
        chunked = await parse_service.chunk_by_ast(self.files)
        analyzed = await parse_service.analyze_imports(chunked)
        tagged = await parse_service.tag_config_files(analyzed)

        file_map = await parse_service.build_file_map(tagged)
        by_path = {item.path: item for item in file_map}

        self.assertIn("backend/app/main.py", by_path["backend/app/service.py"].imported_by)
        self.assertGreaterEqual(by_path["backend/app/service.py"].risk_score, 1)
        self.assertEqual(by_path["backend/app/main.py"].language, "Python")

        heatmap = await parse_service.build_heatmap(tagged)
        self.assertTrue(heatmap)
        self.assertGreaterEqual(heatmap[0].score, heatmap[-1].score)

    @unittest.skipUnless(_has("parse_readme"), "parse_readme(B-201) 미구현")
    async def test_missing_readme_returns_none_without_model_call(self):
        empty = FIXTURE_REPO / "frontend"
        self.assertIsNone(await parse_service.parse_readme(str(empty)))

    @unittest.skipUnless(_has("parse_readme"), "parse_readme(B-201) 미구현")
    async def test_missing_readme_falls_back_to_manifest_summary(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                '{"name":"fallback-app","scripts":{"dev":"next dev"},"dependencies":{"next":"16.0.0"}}',
                encoding="utf-8",
            )
            summary = await parse_service.parse_readme(str(root))
        self.assertIsInstance(summary, str)
        self.assertIn("README가 없어", summary)
        self.assertIn("fallback-app", summary)

    @unittest.skipUnless(_has("parse_readme"), "parse_readme(B-201) 미구현")
    async def test_existing_readme_returns_summary(self):
        # README가 있으면 비어있지 않은 요약을 반환. LLM 응답 문구에 의존하지 않도록
        # _summarize_with_llm을 None으로 mock(휴리스틱 폴백 고정)해 결정성 확보. (#74 리뷰 보완)
        from app.parse import readme as readme_module

        with patch.object(readme_module, "_summarize_with_llm", AsyncMock(return_value=None)):
            summary = await parse_service.parse_readme(str(FIXTURE_REPO))
        self.assertIsInstance(summary, str)
        self.assertTrue(summary.strip())

    @unittest.skipUnless(_has("build_hierarchical_summary"), "build_hierarchical_summary(B-209) 미구현")
    async def test_hierarchical_summary_fills_files_and_master(self):
        # 파일 요약(file.summary)이 채워지고, 마스터 요약 문자열이 반환되는지 검증.
        # 마스터 LLM은 mock(None=휴리스틱 폴백)해 결정성 확보.
        from app.parse import summary as summary_module

        with patch.object(
            summary_module, "_master_summary_with_llm", AsyncMock(return_value=None)
        ):
            summarized, master = await parse_service.build_hierarchical_summary(self.files)

        by_path = {item.path: item for item in summarized}
        self.assertTrue((by_path["backend/app/main.py"].summary or "").strip())
        self.assertIsInstance(master, str)
        self.assertTrue(master.strip())

    @unittest.skipUnless(
        _has("build_hierarchical_summary", "build_file_summaries", "build_folder_summaries"),
        "B-209 요약 실사용 유틸리티 미구현",
    )
    async def test_hierarchical_summary_fills_file_and_folder_contracts(self):
        from app.parse import summary as summary_module

        chunked = await parse_service.chunk_by_ast(self.files)
        with patch.object(
            summary_module, "_master_summary_with_llm", AsyncMock(return_value=None)
        ):
            summarized, master = await parse_service.build_hierarchical_summary(chunked)

        self.assertIn("총", master)
        main = next(item for item in summarized if item.path == "backend/app/main.py")
        self.assertIsInstance(main.summary, str)
        self.assertTrue(main.summary)

        file_summaries = await parse_service.build_file_summaries(summarized)
        folder_summaries = await parse_service.build_folder_summaries(summarized)
        self.assertTrue(any(item.path == "backend/app/main.py" for item in file_summaries))
        self.assertTrue(any(item.path == "backend/app" for item in folder_summaries))


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
