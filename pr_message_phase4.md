🎯 작업 목적
- 대시보드의 Mock 차트를 실제 분석 리포트(WorkspaceReport) 데이터로 교체하여 저장소별 언어 분포와 건강도를 시각화합니다. (#163)
- 분석 이력(History)의 검색 및 필터링 기능을 강화하고 삭제(DELETE) API 연동을 통해 사용성을 고도화합니다. (#177, #162)
- 팀 단위의 저장소 공유를 위한 기반 스키마(Team)를 구축하고, 분석 시 Private 설정을 분리할 수 있는 UX를 도입합니다. (#164)

✨ 주요 변경 사항
- [x] 프론트엔드 대시보드: DashboardCharts 컴포넌트에 Mock 대신 실제 report 속성 주입 (#163)
- [x] 프론트엔드 분석 이력: HistoryList 내 상태 필터(Dropdown), 이름 검색 바 구현 및 삭제 버튼 연동 (#177)
- [x] 프론트엔드 분석 폼: RepoInput 컴포넌트에 '나만 보기 (Private)' 토글 스위치 추가 (#164)
- [x] 백엔드 이력 삭제 API: DELETE `/api/list/analysis/{job_id}` 추가 및 `AnalysisJobListRepository` 삭제 로직 연동 (#177)
- [x] 백엔드 팀 인증 모델: `auth/models.py`에 `Team`, `TeamMember` 스키마 추가 및 CRUD 라우터 등록 (#164)

🛠️ 리뷰 및 로컬 테스트 방법
- `npm run dev` 후 `/analyze` 화면에 진입하여 History List의 상단 필터를 변경해보거나 삭제 버튼 동작 여부를 테스트해 주세요.
- 레포지토리를 불러왔을 때 Dashboard의 언어 비중 차트가 실제 라인 수에 비례하여 나오는지 확인 부탁드립니다.

📸 실행 결과 (선택)
(없음)

⚠️ 리뷰어에게 당부하는 점
@woovii000 @KimHyo1 @smmini
- 이번 PR에는 `Team`과 관련된 신규 테이블(users - team_members - teams) 정의가 포함되어 있습니다. 향후 팀 공유 기능을 본격적으로 붙일 때 스키마가 적절한지 미리 검토해 주시면 감사합니다!
