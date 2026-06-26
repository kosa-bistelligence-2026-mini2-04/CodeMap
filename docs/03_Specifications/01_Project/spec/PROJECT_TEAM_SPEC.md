# PROJECT TEAM 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-TEAM | **최종 업데이트**: 2026-06-26

## 배경

팀 회의에서 분석 검색 기록과 채팅 내용의 공유 범위를 계정/팀 단위로 명확히 분리해야 한다는 요구가 나왔다. 현재 구현은 인증 계정은 존재하지만 `analysis_jobs`, `chat_conversations`, `chat_messages`가 사용자 또는 팀 소유권을 직접 갖지 않아, 기록 조회 API가 사용자별 private 영역과 팀 공유 영역을 구분하기 어렵다.

이 문서는 Issue #164의 기준 명세로 사용한다.

## 목표

- 개인 사용자가 만든 private 분석 이력과 채팅은 같은 DB에 저장되더라도 다른 사용자에게 보이지 않는다.
- 팀 workspace에서 만든 분석 이력과 채팅은 초대 수락을 완료한 팀원에게만 보인다.
- 팀 초대는 초대 생성 -> 초대 수락/거절 -> 멤버십 활성화 흐름을 따른다.
- LIST, REPO, CHAT 도메인은 모두 같은 visibility/ownership 계약을 사용한다.

## 비목표

- 외부 조직 SSO, GitHub OAuth 조직 동기화, 세밀한 RBAC 권한은 Phase 2 이후로 둔다.
- 공개 링크 공유, 이메일/Slack 발송 공유는 DOCS/UTIL 공유 기능과 분리한다.
- 같은 GitHub repo URL의 분석 결과를 팀 간 자동 공유하지 않는다.

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 상태 |
| --- | --- | --- | --- | --- |
| PROJECT-TEAM-B-101 | 팀 생성 API | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-B-102 | 팀 초대 생성 API | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-B-103 | 팀 초대 수락/거절 API | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-B-104 | 팀 멤버 조회 API | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-B-201 | 분석 job ownership/visibility 저장 | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-B-202 | 채팅 thread/message visibility 저장 | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-B-203 | LIST/CHAT/REPO 권한 필터링 | Backend | Phase 2 | 제안 |
| PROJECT-TEAM-F-101 | 개인/팀 workspace 전환 UI | Frontend | Phase 2 | 제안 |
| PROJECT-TEAM-F-102 | 개인 private 기록 섹션 | Frontend | Phase 2 | 제안 |
| PROJECT-TEAM-F-103 | 팀 기록 섹션 및 초대 수락 UI | Frontend | Phase 2 | 제안 |

## 핵심 개념

| 개념 | 설명 |
| --- | --- |
| `user` | 로그인 계정. private 기록의 소유자다. |
| `team` | 여러 사용자가 공유하는 workspace 단위다. |
| `team_member` | 사용자가 팀에 속한다는 활성 멤버십이다. |
| `team_invite` | 아직 수락 전인 초대 상태다. 이메일 또는 user id를 대상으로 한다. |
| `visibility=private` | 생성자만 볼 수 있는 분석/채팅 기록이다. |
| `visibility=team` | 연결된 `team_id`의 활성 멤버만 볼 수 있는 분석/채팅 기록이다. |

## 데이터 모델 초안

### `teams`

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID PK | 팀 ID |
| `name` | String | 팀 표시 이름 |
| `created_by_user_id` | UUID FK(users.id) | 팀 생성자 |
| `created_at` | DateTime | 생성 시각 |
| `updated_at` | DateTime | 수정 시각 |

### `team_members`

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `team_id` | UUID FK(teams.id) | 팀 ID |
| `user_id` | UUID FK(users.id) | 멤버 user ID |
| `role` | String | `owner`, `member` |
| `status` | String | `active`, `removed` |
| `joined_at` | DateTime | 가입 시각 |

`team_id + user_id`는 unique로 관리한다.

### `team_invites`

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID PK | 초대 ID |
| `team_id` | UUID FK(teams.id) | 초대 대상 팀 |
| `email` | String | 초대 대상 이메일 |
| `invited_by_user_id` | UUID FK(users.id) | 초대한 사용자 |
| `status` | String | `pending`, `accepted`, `declined`, `expired`, `cancelled` |
| `expires_at` | DateTime | 만료 시각 |
| `created_at` | DateTime | 생성 시각 |
| `responded_at` | DateTime nullable | 응답 시각 |

### `analysis_jobs` 확장

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `created_by_user_id` | UUID FK(users.id) | 분석을 생성한 사용자 |
| `visibility` | String | `private` 또는 `team` |
| `team_id` | UUID nullable FK(teams.id) | 팀 공유 분석이면 팀 ID |

제약:

- `visibility='private'`이면 `team_id IS NULL`이어야 한다.
- `visibility='team'`이면 `team_id IS NOT NULL`이어야 한다.
- private job은 `created_by_user_id`만 조회/채팅 가능하다.
- team job은 `team_members.status='active'`인 멤버만 조회/채팅 가능하다.

### `chat_conversations` 확장

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `created_by_user_id` | UUID FK(users.id) | 대화 생성자 |
| `visibility` | String | `private` 또는 `team` |
| `team_id` | UUID nullable FK(teams.id) | 팀 공유 대화이면 팀 ID |

채팅 visibility는 기본적으로 연결된 `analysis_jobs`의 visibility를 따른다. 별도 전환은 Phase 2 이후로 둔다.

## 권한 규칙

| 작업 | private 기록 | team 기록 |
| --- | --- | --- |
| 분석 이력 목록 조회 | 생성자만 가능 | 팀 active member만 가능 |
| 분석 상세 조회 | 생성자만 가능 | 팀 active member만 가능 |
| chat run 생성 | 생성자만 가능 | 팀 active member만 가능 |
| thread 목록/메시지 조회 | 생성자만 가능 | 팀 active member만 가능 |
| 팀 초대 생성 | 팀 owner만 가능 | 팀 owner만 가능 |
| 팀 초대 수락 | 초대 이메일과 로그인 이메일이 일치해야 가능 | 수락 후 active member 생성 |

권한 실패는 403 `FORBIDDEN` 또는 세부 코드 `TEAM_ACCESS_DENIED` / `PRIVATE_RESOURCE_DENIED`로 반환한다.

## 사용자 흐름

### 개인 private 분석

1. 사용자가 로그인한다.
2. workspace selector에서 `개인`을 선택한다.
3. GitHub URL 또는 로컬 폴더 분석을 시작한다.
4. `analysis_jobs.visibility=private`, `created_by_user_id=current_user.id`로 저장한다.
5. HistoryList의 개인 섹션에만 표시한다.
6. 채팅 thread/message도 private scope로 저장한다.

### 팀 분석 공유

1. 팀 owner가 팀을 생성한다.
2. 팀 owner가 이메일로 팀원을 초대한다.
3. 초대받은 사용자가 로그인 후 초대를 수락한다.
4. workspace selector에서 팀을 선택한다.
5. 분석 생성 시 `visibility=team`, `team_id=selected_team.id`로 저장한다.
6. 같은 팀 active member에게만 팀 HistoryList와 chat thread가 보인다.

## API 연동 기준

- 모든 보호 API는 `get_current_user`를 통해 current user를 확보한다.
- `GET /api/list/analysis`는 `scope=private|team|all`, `teamId` 쿼리를 지원한다.
- `POST /api/repo/analysis`와 `POST /api/repo/analysis/local`은 `visibility`, `teamId` 입력을 받는다.
- `POST /api/chat/{repo_id}/runs`와 thread 조회 API는 repo 권한을 먼저 확인한다.
- `repo_id`만으로 권한을 판단하지 않는다. 반드시 job owner/team membership을 함께 확인한다.

## 완료 기준

- 사용자 A의 private 분석/채팅은 사용자 B에게 보이지 않는다.
- 사용자 A와 B가 같은 팀 active member이면 team 분석/채팅이 둘 다에게 보인다.
- 팀 초대 pending/accepted/declined/expired 상태 전이가 API와 UI에 반영된다.
- LIST/REPO/CHAT API 테스트에 private/team 권한 우회 방지 케이스가 포함된다.
- 기존 legacy job은 마이그레이션 정책에 따라 안전하게 private 또는 관리자 검토 대상으로 분류된다.
