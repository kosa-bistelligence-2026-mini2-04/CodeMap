"""RAG-PARSE 서비스 진입점.

각 기능은 app/parse/<module>.py에 구현하고 여기서 re-export한다.
(테스트가 app.parse.service 기준으로 함수를 참조/patch하므로 모듈 속성으로 노출해야 한다.)

작업 단위별로 아래 import에 한 줄씩 추가된다:
  directory : analyze_directory, find_entry_points         (B-202/203)  ← 구현됨
  manifest  : tag_config_files, extract_run_commands, detect_tech_stack (B-204/205/206)
  readme    : parse_readme                                  (B-201)
  chunking  : chunk_by_ast                                  (B-207)
  imports   : analyze_imports                               (B-208)
  summary   : build_hierarchical_summary, run_structure_agent (B-209/210)
  run_parse_pipeline : 오케스트레이터                        (통합)
"""

from app.parse.directory import analyze_directory, find_entry_points

__all__ = [
    "analyze_directory",
    "find_entry_points",
]
