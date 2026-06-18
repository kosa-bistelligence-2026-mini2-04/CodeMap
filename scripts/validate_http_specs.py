#!/usr/bin/env python3
"""Validate Notion-source preservation and executable HTTP spec structure."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from convert_notion_html_to_http import render_http, visible_text


ROOT = Path(__file__).resolve().parents[1]
HTTP_ROOT = ROOT / "docs" / "http"
SOURCE_ROOT = HTTP_ROOT / "_source-spec"
MANIFEST = SOURCE_ROOT / "manifest.json"
REQUEST_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD|WEBSOCKET)\s+\S+", re.MULTILINE)
ID_RE = re.compile(
    r"\b(?:PROJECT|RAG|AGENT|DOCS)-(?:LIST|REPO|PIPELINE|PARSE|EMBED|GRAPH|CHAT|CORE|SEARCH|GEN|GUARD|UTIL)-(?:API-)?[BF]?[-]?[0-9]{3}\b"
)
TOKEN_ASSIGN_RE = re.compile(
    r"^@(?:accessToken|serviceToken)\s*=\s*(?P<value>\S.*)$",
    re.IGNORECASE | re.MULTILINE,
)


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    if not MANIFEST.exists():
        fail(f"누락: {MANIFEST}", errors)
        report = {}
    else:
        report = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if report.get("source_file_count") != report.get("output_file_count"):
            fail("원본 HTML 수와 변환 HTTP 수가 다릅니다.", errors)
        if report.get("missing_token_count") != 0 or report.get("coverage") != 1.0:
            fail("Notion 원문 토큰 보존율이 100%가 아닙니다.", errors)
        for item in report.get("files", []):
            target = HTTP_ROOT / item["target"]
            if not target.exists():
                fail(f"변환 파일 누락: {target.relative_to(ROOT)}", errors)

        live_source_root = Path(report.get("source_root", ""))
        live_source_verified = live_source_root.is_dir()
        if live_source_verified:
            for item in report.get("files", []):
                source = live_source_root / item["source"]
                target = HTTP_ROOT / item["target"]
                if not source.exists() or not target.exists():
                    continue
                expected = render_http(source, live_source_root, visible_text(source))
                if target.read_text(encoding="utf-8") != expected:
                    fail(f"원문과 변환본 불일치: {target.relative_to(ROOT)}", errors)
        else:
            live_source_verified = False

    source_files = sorted(SOURCE_ROOT.rglob("*.http"))
    executable_files = sorted(
        path for path in HTTP_ROOT.rglob("*.http") if SOURCE_ROOT not in path.parents
    )
    request_count = 0
    api_ids: Counter[str] = Counter()
    feature_ids: set[str] = set()
    source_ids: set[str] = set()

    for path in source_files:
        source_ids.update(ID_RE.findall(path.read_text(encoding="utf-8")))

    for path in executable_files:
        content = path.read_text(encoding="utf-8")
        matches = REQUEST_RE.findall(content)
        request_count += len(matches)
        if not matches:
            fail(f"실행 요청 블록 없음: {path.relative_to(ROOT)}", errors)
        token_values = [match.group("value").strip() for match in TOKEN_ASSIGN_RE.finditer(content)]
        if any(not value.startswith("replace-me") for value in token_values):
            fail(f"토큰 변수는 replace-me placeholder여야 함: {path.relative_to(ROOT)}", errors)
        ids = ID_RE.findall(content)
        feature_ids.update(ids)
        for value in ids:
            if "-API-" in value:
                api_ids[value] += 1

    unmapped_source_ids = sorted(source_ids - feature_ids)
    if unmapped_source_ids:
        fail("실행 명세에 연결되지 않은 원문 ID: " + ", ".join(unmapped_source_ids), errors)

    summary = {
        "notion_html_files": report.get("source_file_count", 0),
        "source_reference_http_files": len(source_files),
        "source_token_coverage": report.get("coverage", 0),
        "live_source_verified": live_source_verified if report else False,
        "executable_http_files": len(executable_files),
        "request_blocks": request_count,
        "referenced_feature_and_api_ids": len(feature_ids),
        "unmapped_source_ids": unmapped_source_ids,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
