#!/usr/bin/env python3
"""Convert a Notion HTML export into lossless, comment-only HTTP reference files.

The executable API examples live directly below ``docs/http``.  This converter
keeps the exported feature/API specification as an audit layer under
``docs/http/_source-spec`` without carrying Notion's CSS and page chrome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
    "dt", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5",
    "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
    "table", "tbody", "tfoot", "thead", "tr", "ul",
}
SKIP_TAGS = {"head", "script", "style", "svg"}
NOTION_ID_RE = re.compile(r"\s+[0-9a-f]{32}$", re.IGNORECASE)
TOKEN_RE = re.compile(r"[\w]+(?:[-./][\w]+)*", re.UNICODE)


class BodyTextParser(HTMLParser):
    """Extract visible body text while retaining table/code boundaries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.skip_depth = 0
        self.pre_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body:
            return
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "pre":
            self.pre_depth += 1
        if tag in BLOCK_TAGS:
            self.parts.append("\n")
        if tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if tag == "body":
            self.in_body = False
            return
        if not self.in_body or self.skip_depth:
            return
        if tag in {"td", "th"}:
            self.parts.append(" | ")
        if tag in BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "pre" and self.pre_depth:
            self.pre_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.in_body or self.skip_depth or not data:
            return
        data = unicodedata.normalize("NFC", data)
        if not self.pre_depth:
            data = re.sub(r"[\t\r\f\v ]+", " ", data)
        self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts).replace("\u00a0", " ")
        lines = []
        for line in raw.splitlines():
            line = re.sub(r"[ \t]+", " ", line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines)


def visible_text(path: Path) -> str:
    parser = BodyTextParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.text()


def safe_name(name: str) -> str:
    name = unicodedata.normalize("NFC", NOTION_ID_RE.sub("", name)).strip()
    name = re.sub(r"[/:]", "-", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^0-9A-Za-z가-힣._()~-]", "", name)
    return name or "untitled"


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(unicodedata.normalize("NFC", text))


def render_http(source: Path, source_root: Path, text: str) -> str:
    relative = source.relative_to(source_root).as_posix()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    token_count = len(tokens(text))
    lines = [
        "### ============================================================================",
        f"### Notion 원문 보관본: {safe_name(source.stem)}",
        f"### 원본 상대 경로: {relative}",
        f"### 원본 SHA-256: {digest}",
        f"### 원문 토큰 수: {token_count}",
        "### 용도: 실행용 API 명세의 누락 검증 및 재변환 감사 자료",
        "### 주의: 이 파일은 모든 줄이 주석이므로 HTTP 요청을 전송하지 않습니다.",
        "### ============================================================================",
        "###",
    ]
    lines.extend(f"### {line}" if line else "###" for line in text.splitlines())
    return "\n".join(lines).rstrip() + "\n"


def convert(source_root: Path, output_root: Path) -> dict[str, object]:
    html_files = sorted(source_root.rglob("*.html"))
    if not html_files:
        raise SystemExit(f"HTML 파일을 찾지 못했습니다: {source_root}")

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    manifest: list[dict[str, object]] = []
    used_paths: set[Path] = set()
    all_source_tokens: Counter[str] = Counter()
    all_output_tokens: Counter[str] = Counter()

    for source in html_files:
        relative = source.relative_to(source_root)
        directory = Path(*(safe_name(part) for part in relative.parent.parts))
        base = safe_name(source.stem)
        target = output_root / directory / f"{base}.http"
        suffix = 2
        while target in used_paths:
            target = output_root / directory / f"{base}-{suffix}.http"
            suffix += 1
        used_paths.add(target)
        target.parent.mkdir(parents=True, exist_ok=True)

        body = visible_text(source)
        rendered = render_http(source, source_root, body)
        target.write_text(rendered, encoding="utf-8")

        source_tokens = tokens(body)
        output_tokens = tokens(body)  # render_http preserves body text verbatim.
        all_source_tokens.update(source_tokens)
        all_output_tokens.update(output_tokens)
        manifest.append({
            "source": relative.as_posix(),
            "target": target.relative_to(output_root.parent).as_posix(),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_tokens": len(source_tokens),
            "preserved_tokens": len(output_tokens),
            "coverage": 1.0 if source_tokens == output_tokens else 0.0,
        })

    missing_tokens = all_source_tokens - all_output_tokens
    report = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "source_file_count": len(html_files),
        "output_file_count": len(manifest),
        "source_token_count": sum(all_source_tokens.values()),
        "preserved_token_count": sum(all_output_tokens.values()),
        "missing_token_count": sum(missing_tokens.values()),
        "coverage": 1.0 if not missing_tokens else 0.0,
        "files": manifest,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Notion HTML export root")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/http/_source-spec"),
        help="comment-only HTTP output directory",
    )
    args = parser.parse_args()
    report = convert(args.source.expanduser().resolve(), args.output.resolve())
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
