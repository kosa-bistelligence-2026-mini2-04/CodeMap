# RAG-PARSE report_json 결과 계약 정리

## 배경

RAG-PARSE-B-201 ~ B-209는 README, 디렉토리, 진입점, 실행 명령, 기술
스택, AST 청킹, import 관계, 계층형 요약을 작은 단위 PR로 나누어
구현되었다. 이 방식은 리뷰와 충돌 관리에는 유리하지만, 최종 B-210 통합
파이프라인과 RAG-PARSE API가 읽어야 하는 `report_json`의 형태가 단일
계약으로 고정되지 않으면 다음 문제가 생길 수 있다.

- `repo.analyzer`가 저장하던 기존 키(`stack`, `entrypoints`,
  `executive_summary`)와 RAG-PARSE 모듈의 키(`tech_stack`,
  `entry_points`, `readme_summary`, `master_summary`)가 섞인다.
- API-001은 문자열 배열 중심 응답을 사용하지만, API-003 ~ API-006은
  객체형 응답을 요구한다.
- EMBED 단계는 파일/청크 계약을 안정적으로 받아야 하므로 PARSE 결과
  DTO가 먼저 고정되어야 한다.

## 결정

`backend/app/parse/schemas.py`의 `ParseResult`를 RAG-PARSE 최종 산출물
기준 DTO로 확장한다. 기존 API-001 호환 필드는 유지하면서, 후속 API와
B-210 통합에서 사용할 객체형 필드를 함께 둔다.

| 필드 | 목적 |
|---|---|
| `tech_stack` | API-001 호환용 기술 스택 문자열 배열 |
| `tech_stack_details` | API-004 객체형 기술 스택 목록 |
| `language_composition` | 실제 소스 라인 기준 언어 구성 |
| `run_commands` | 기존 문자열 배열 호환 필드 |
| `run_command_details` | 설치/실행/빌드 명령 구조화 객체 |
| `entry_points` | API-001 호환용 진입점 경로 배열 |
| `entry_point_details` | API-003 객체형 진입점 목록 |
| `config_files` | 설정 파일 경로 목록 |
| `folder_summaries` | API-006 폴더 단위 요약 목록 |
| `file_map` | API-005 파일별 코드맵 항목 |
| `directory_tree` | API-001/API-003에서 재사용할 트리 텍스트 |

### `file_map` 파일 메타데이터 확장

Issue #167, #168 및 3차 리뷰 합의에 따라 `file_map` 각 항목은 파일 규모 지표를 포함하며, 파일 크기는 오직 `bytes`로 단일화하여 통일합니다. (레거시 `size` 필드는 완전 폐기 및 삭제됩니다.)

| 필드 | 목적 |
|---|---|
| `path` | repo 내부 상대 파일 경로 |
| `summary` | 파일 단위 요약 |
| `language` | 감지된 언어 |
| `lines` | 파일 총 라인 수 |
| `bytes` | 파일 총 크기 (바이트 수) |
| `chars` | 디코딩된 텍스트 기준 글자 수 |

프론트 타입에서는 `WorkspaceFile` DTO에 대응하여 오직 `bytes` 필드만 필수 계약으로 소모합니다. DashboardCharts 실제 데이터 연결(Issue #163)은 이 값과 `language_composition`을 우선 사용합니다.

## 호환 정책

B-210 통합 전까지는 기존 분석 잡이 legacy `report_json`을 저장할 수
있다. 따라서 API 읽기 경로에는 `backend/app/parse/report.py`의 helper를
두어 다음 fallback을 허용한다.

- `tech_stack`이 없으면 `stack`을 읽는다.
- `entry_points`가 없으면 `entrypoints`를 읽는다.
- `readme_summary` 또는 `master_summary`가 없으면 `executive_summary`를
  읽는다.
- `run_commands`는 기존 배열 형태와 신규 객체 형태를 모두
  `RunCommandSet`으로 정규화한다.

이 호환 레이어는 기존 동작을 보존하면서 B-210에서 canonical
`ParseResult` 형태로 저장하도록 전환하기 위한 임시 연결부이다.

## 후속 PR 연결

- PR #73 / #74 / #79의 단위 분석 결과를 B-210에서 하나의
  `ParseResult`로 조립한다.
- PR #80의 기술 스택 객체, Docker/docker-compose 탐지,
  `languageComposition` 결과를 `tech_stack_details`와
  `language_composition`에 연결한다.
- 이후 RAG-PARSE API 완성 PR에서 API-002 ~ API-006 응답을 이 계약에
  맞춰 읽도록 분리한다.
