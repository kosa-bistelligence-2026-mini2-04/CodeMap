"""
DOCS-GEN Markdown 변환 유틸리티

GenFormSupervisor가 생성한 master_report dict를
온보딩 가이드북 Markdown 전문으로 변환한다.

호출 경로: background.py → master_report_to_markdown()
"""

from typing import Any


# ──────────────────────────────────────────────
# master_report → 온보딩 가이드북 Markdown 변환
# ──────────────────────────────────────────────
def master_report_to_markdown(
    report: dict[str, Any],
    repo_name: str = "",
) -> str:
    '''
    GenFormSupervisor.run() 결과인 master_report dict를
    온보딩 가이드북 Markdown 전문으로 변환한다.

    Args:
        report:    master_report_node가 반환한 dict
        repo_name: 저장소 이름 (헤더 제목용)

    Returns:
        Markdown 전문 문자열
    '''
    lines: list[str] = []
    title = repo_name if repo_name else "프로젝트"
    lines.append(f"# {title} 온보딩 가이드북\n")

    ## 1. 프로젝트 개요 (doc_summary)
    summary = report.get("summary") or {}
    if isinstance(summary, dict):
        purpose = summary.get("purpose", "")
        if purpose:
            lines.append("## 프로젝트 개요\n")
            lines.append(f"{purpose}\n")
        key_features = summary.get("key_features") or []
        if key_features:
            lines.append("### 핵심 기능\n")
            for feat in key_features:
                lines.append(f"- {feat}")
            lines.append("")
        tech_context = summary.get("tech_context", "")
        if tech_context:
            lines.append(f"**기술 컨텍스트**: {tech_context}\n")
    elif isinstance(summary, str) and summary:
        lines.append("## 프로젝트 개요\n")
        lines.append(f"{summary}\n")

    ## 2. 기술 스택
    ## stack은 {technologies, primary_language, languages, frameworks} 형태의 dict
    stack = report.get("stack") or {}
    if isinstance(stack, dict):
        technologies = stack.get("technologies") or []
        primary_lang = stack.get("primary_language", "")
        languages = stack.get("languages") or []
        if technologies or primary_lang:
            lines.append("## 기술 스택\n")
            if primary_lang:
                lines.append(f"**주 언어**: {primary_lang}\n")
            for tech in technologies:
                lines.append(f"- {tech}")
            for lang in languages:
                if lang not in technologies:
                    lines.append(f"- {lang}")
            lines.append("")
    elif isinstance(stack, list) and stack:
        lines.append("## 기술 스택\n")
        for tech in stack:
            lines.append(f"- {tech}")
        lines.append("")

    ## 3. 폴더 구조 설명 (folder_summaries)
    ## file_map은 {folder_summaries, entrypoints, total_files, total_lines} 형태의 dict
    file_map = report.get("file_map") or {}
    folder_summaries = (
        file_map.get("folder_summaries") if isinstance(file_map, dict) else {}
    ) or {}
    if folder_summaries:
        lines.append("## 폴더 구조\n")
        for folder, desc in folder_summaries.items():
            lines.append(f"### `{folder}`\n")
            desc_text = desc if isinstance(desc, str) else str(desc)
            lines.append(f"{desc_text}\n")

    ## 4. 온보딩 가이드 (onboarding_guide)
    guide = report.get("guide") or report.get("recommendations") or {}
    if isinstance(guide, dict):
        reading_order = guide.get("reading_order") or []
        if reading_order:
            lines.append("## 추천 파일 읽기 순서\n")
            for i, item in enumerate(reading_order, start=1):
                ## reading_order 항목은 파일 경로 문자열
                if isinstance(item, str):
                    lines.append(f"{i}. `{item}`")
                elif isinstance(item, dict):
                    path = item.get("path", "")
                    reason = item.get("reason", "")
                    lines.append(f"{i}. `{path}` — {reason}")
            lines.append("")

        risk_files = guide.get("risk_files") or []
        if risk_files:
            lines.append("## 주의 / 위험 파일\n")
            for rf in risk_files:
                if isinstance(rf, dict):
                    ## risk_files 항목 키는 "file" (nodes.py LLM 프롬프트 기준)
                    file_path = rf.get("file", "") or rf.get("path", "")
                    reason = rf.get("reason", "")
                    lines.append(f"- **`{file_path}`**: {reason}")
                elif isinstance(rf, str):
                    lines.append(f"- **`{rf}`**")
            lines.append("")

        first_tasks = guide.get("first_tasks") or []
        if first_tasks:
            lines.append("## 첫 기여 추천 작업\n")
            for task_item in first_tasks:
                ## first_tasks 항목은 작업 설명 문자열
                if isinstance(task_item, str):
                    lines.append(f"- {task_item}")
                elif isinstance(task_item, dict):
                    task = task_item.get("task", "")
                    difficulty = task_item.get("difficulty", "")
                    lines.append(f"- {task} *(난이도: {difficulty})*")
            lines.append("")

    return "\n".join(lines)
