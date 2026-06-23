import unittest
from uuid import UUID

try:
    from app.parse import schemas as rag_schemas
except ImportError:
    rag_schemas = None


REQUIRED_SCHEMA_NAMES = {
    "CodeChunk",
    "ParsedFile",
    "RunCommandSet",
    "TechStackItem",
    "LanguageCompositionItem",
    "EntryPointItem",
    "FolderSummary",
    "FileSummary",
    "FileMapItem",
    "HeatmapItem",
    "ParseResult",
    "EmbedRequest",
    "EmbedResult",
}
SCHEMAS_READY = rag_schemas is not None and all(
    hasattr(rag_schemas, name) for name in REQUIRED_SCHEMA_NAMES
)


@unittest.skipUnless(SCHEMAS_READY, "RAG 공유 DTO가 아직 구현되지 않음")
class RagSchemaContractTests(unittest.TestCase):
    def test_code_chunk_accepts_documented_types_and_line_range(self):
        chunk = rag_schemas.CodeChunk(
            chunk_index=0,
            content="def run():\n    return True",
            start_line=1,
            end_line=2,
            chunk_type="function",
        )
        self.assertEqual(chunk.chunk_type, "function")
        self.assertLessEqual(chunk.start_line, chunk.end_line)

    def test_directory_content_is_nullable(self):
        directory = rag_schemas.ParsedFile(
            path="backend/app",
            file_type="DIRECTORY",
            depth=1,
        )
        self.assertIsNone(directory.content)
        self.assertEqual(directory.chunks, [])
        self.assertEqual(directory.imports, [])

    def test_parse_result_round_trips_into_embed_request(self):
        job_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        parsed = rag_schemas.ParsedFile(
            path="backend/app/main.py",
            file_type="FILE",
            depth=2,
            content="app = FastAPI()",
        )
        result = rag_schemas.ParseResult(
            job_id=job_id,
            repo_name="sample",
            owner="team",
            branch="main",
            files=[parsed],
            run_command_details=rag_schemas.RunCommandSet(
                install="pip install -r requirements.txt",
                run="uvicorn app.main:app",
            ),
            tech_stack_details=[
                rag_schemas.TechStackItem(
                    name="FastAPI",
                    version="0.115.0",
                    category="framework",
                    source="requirements.txt",
                )
            ],
            language_composition=[
                rag_schemas.LanguageCompositionItem(language="Python", lines=1, percentage=100.0)
            ],
            entry_point_details=[
                rag_schemas.EntryPointItem(path="backend/app/main.py", type="backend")
            ],
        )
        request = rag_schemas.EmbedRequest(job_id=result.job_id, files=result.files)
        self.assertEqual(request.job_id, job_id)
        self.assertEqual(request.files[0].path, "backend/app/main.py")
        self.assertEqual(result.run_command_details.run, "uvicorn app.main:app")
        self.assertEqual(result.tech_stack_details[0].name, "FastAPI")
        self.assertEqual(result.language_composition[0].lines, 1)

    def test_embed_result_tracks_partial_failures(self):
        result = rag_schemas.EmbedResult(
            job_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            total_files=2,
            total_chunks=3,
            failed_paths=["broken.py"],
        )
        self.assertEqual(result.failed_paths, ["broken.py"])
