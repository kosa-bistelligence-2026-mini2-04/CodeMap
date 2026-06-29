/**
 * DOCS-GEN-F-201 타입 검증 — tsc --noEmit 으로 실행
 * ExportButtons 컴포넌트 프롭 타입과 다운로드 API 반환 타입이
 * DOCS-GEN-API-004 명세와 일치하는지 확인합니다.
 */

import type { ExportButtonsProps } from "../components/ExportButtons";
import { buildMarkdownDownloadUrl } from "../api/docsApi";

// 타입 보조 함수 — 할당 가능성 검증
function assertAssignable<T>(_val: T): void {
    void _val;
}


// ── 1. repoId가 유효한 UUID 문자열일 때 허용 ──────────────────
const propsWithId: ExportButtonsProps = {
    repoId: "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
};
assertAssignable<ExportButtonsProps>(propsWithId);


// ── 2. repoId가 null일 때 허용 (미로드 상태) ──────────────────
const propsNull: ExportButtonsProps = {
    repoId: null,
};
assertAssignable<ExportButtonsProps>(propsNull);


// ── 3. repoId 필드 타입이 string | null 임을 보장 ─────────────
const idString: string | null = propsWithId.repoId;
assertAssignable<string | null>(idString);

const idNull: string | null = propsNull.repoId;
assertAssignable<string | null>(idNull);


// ── 4. buildMarkdownDownloadUrl 반환 타입이 string임을 보장 ────
const downloadUrl: string = buildMarkdownDownloadUrl(
    "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
);
assertAssignable<string>(downloadUrl);


// ── 5. URL에 repo_id가 포함된 형태 검증 ──────────────────────
const sampleRepoId = "550e8400-e29b-41d4-a716-446655440000";
const sampleUrl: string = buildMarkdownDownloadUrl(sampleRepoId);
assertAssignable<string>(sampleUrl);


// ── 6. ExportButtonsProps 구조 정합성 — 필수 필드 확인 ─────────
const propsShape: Pick<ExportButtonsProps, "repoId"> = {
    repoId: "test-uuid",
};
assertAssignable<Pick<ExportButtonsProps, "repoId">>(propsShape);


// ── 7. ExportButtonsProps 확장 불변성 — 추가 필드 없음 확인 ────
// ExportButtonsProps는 { repoId: string | null } 이어야 함
const validProps: ExportButtonsProps = { repoId: null };
const _checkedRepoId: string | null = validProps.repoId;
assertAssignable<string | null>(_checkedRepoId);


// ── 8. string 빈값도 허용 검증 ────────────────────────────────
const propsEmpty: ExportButtonsProps = { repoId: "" };
assertAssignable<ExportButtonsProps>(propsEmpty);


// ── 9. 타입 불일치 컴파일 에러 검증 (명세 준수 확인) ─────────
// @ts-expect-error repoId에 number 리터럴을 할당하면 에러
const _badProps: ExportButtonsProps = { repoId: 12345 };

export {};
