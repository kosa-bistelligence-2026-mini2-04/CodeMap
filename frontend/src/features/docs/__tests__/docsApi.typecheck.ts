/**
 * DOCS-GEN-F-101 타입 검증 파일
 *
 * 테스트 프레임워크 없이 TypeScript 컴파일러(tsc --noEmit)로 타입 안전성을 검증한다.
 * "type asserting" 패턴: 잘못된 타입을 할당하면 컴파일 에러가 발생해 CI 에서 잡힌다.
 */

import type {
  DocFolderSummary,
  DocGetJsonData,
  DocGetJsonResponse,
  DocGetMarkdownData,
  DocGetMarkdownResponse,
  DocReadingOrderItem,
  DocDangerFileItem,
} from "@/common/types/contracts";
import type { GuideViewerProps } from "@/features/docs/components/GuideViewer";
import type { ExportButtonsProps } from "@/features/docs/components/ExportButtons";

// ── 헬퍼: 값이 특정 타입에 할당 가능한지 컴파일 타임에 확인 ────────────────
function assertAssignable<T>(_val: T): void {
  void _val; // 런타임 실행 불필요 — 컴파일 타임 검증 전용
}

// ── 1. DocFolderSummary 구조 ───────────────────────────────────────────────
const folderSummary: DocFolderSummary = {
  path: "src/app",
  summary: "Next.js 앱 라우터 루트 디렉토리",
};
assertAssignable<DocFolderSummary>(folderSummary);

// ── 2. DocGetMarkdownData 구조 ────────────────────────────────────────────
const markdownData: DocGetMarkdownData = {
  repoId:      "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
  repoName:    "CodeMap",
  content:     "# 온보딩 가이드\n...",
  generatedAt: "2026-06-27T00:00:00Z",
  version:     1,
};
assertAssignable<DocGetMarkdownData>(markdownData);

// ── 3. DocGetJsonData 구조 — 모든 필드 검증 ─────────────────────────────
const readingOrderItem: DocReadingOrderItem = {
  rank:   1,
  path:   "src/app/page.tsx",
  reason: "FastAPI 앱 진입점",
};
assertAssignable<DocReadingOrderItem>(readingOrderItem);

const dangerFileItem: DocDangerFileItem = {
  path:   "backend/app/core/config.py",
  reason: "환경변수 및 API 키 관리 파일",
};
assertAssignable<DocDangerFileItem>(dangerFileItem);

const jsonData: DocGetJsonData = {
  repoId:          "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
  repoName:        "CodeMap",
  summary:         "CodeMap 프로젝트 요약",
  stack:           ["Next.js", "FastAPI", "PostgreSQL"],
  readingOrder:    [readingOrderItem],
  dangerFiles:     [dangerFileItem],
  coreFlow:        "사용자 요청 → FastAPI 라우터 → 서비스 → DB",
  folderSummaries: [folderSummary],
  fileSummaries: [{ path: "src/app/page.tsx", summary: "페이지 진입점" }],
  generatedAt:     "2026-06-27T00:00:00Z",
  version:         1,
};
assertAssignable<DocGetJsonData>(jsonData);

// ── 4. nullable 필드가 null 허용 ─────────────────────────────────────────
const jsonDataNullable: DocGetJsonData = {
  repoId:          "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
  repoName:        "CodeMap",
  summary:         null,
  stack:           [],
  readingOrder:    [],
  dangerFiles:     [],
  coreFlow:        null,
  folderSummaries: [],
  fileSummaries: [],
  generatedAt:     "2026-06-27T00:00:00Z",
  version:         2,
};
assertAssignable<DocGetJsonData>(jsonDataNullable);

// ── 5. 응답 래퍼 구조 ────────────────────────────────────────────────────
const markdownResp: DocGetMarkdownResponse = {
  code:    200,
  message: "success",
  data:    markdownData,
};
assertAssignable<DocGetMarkdownResponse>(markdownResp);

const jsonResp: DocGetJsonResponse = {
  code:    200,
  message: "success",
  data:    jsonData,
};
assertAssignable<DocGetJsonResponse>(jsonResp);

// ── 6. GuideViewerProps 타입 확인 ────────────────────────────────────────
const propsLoading: GuideViewerProps = {
  data:      null,
  isLoading: true,
  error:     null,
};
assertAssignable<GuideViewerProps>(propsLoading);

const propsData: GuideViewerProps = {
  data:      jsonData,
  isLoading: false,
  error:     null,
};
assertAssignable<GuideViewerProps>(propsData);

const propsError: GuideViewerProps = {
  data:      null,
  isLoading: false,
  error:     "가이드북을 불러오지 못했습니다.",
};
assertAssignable<GuideViewerProps>(propsError);

// ── 7. ExportButtonsProps 타입 확인 ─────────────────────────────────────
const exportPropsActive: ExportButtonsProps = {
  repoId: "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
};
assertAssignable<ExportButtonsProps>(exportPropsActive);

const exportPropsNull: ExportButtonsProps = {
  repoId: null,
};
assertAssignable<ExportButtonsProps>(exportPropsNull);

// ── 8. buildMarkdownDownloadUrl 반환 타입 확인 ───────────────────────────
import { buildMarkdownDownloadUrl } from "@/features/docs/api/docsApi";

const downloadUrl: string = buildMarkdownDownloadUrl(
  "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
);
assertAssignable<string>(downloadUrl);

// ── 9. 타입 불일치 시 컴파일 에러 발생 검증 (주석 해제 시 에러 확인 가능) ──
// @ts-expect-error version은 string 불가
const _badVersion: DocGetJsonData = { ...jsonData, version: "v1" };
void _badVersion;

// @ts-expect-error repoId는 null 불가
const _badMarkdown: DocGetMarkdownData = { ...markdownData, repoId: null };
void _badMarkdown;

export {};
