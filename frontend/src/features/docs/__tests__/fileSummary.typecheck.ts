/**
 * DOCS-GEN-F-202 타입 검증 — tsc --noEmit 으로 실행
 */
import type {
    DocFolderSummary,
    DocReadingOrderItem,
    DocDangerFileItem,
    DocGetJsonData,
    DocGetJsonResponse,
    DocFileSummaryItem,
} from "@/common/types/contracts";
import { buildFileSummaries } from "../utils/buildFileSummaries";

function assertAssignable<T>(_val: T): void {
    void _val;
}

// 1. DocFolderSummary 구조 검증
const folder: DocFolderSummary = { path: "src/features", summary: "주요 기능 모듈" };
assertAssignable<DocFolderSummary>(folder);

// 2. DocReadingOrderItem 구조 검증
const readingItem: DocReadingOrderItem = {
    rank: 1,
    path: "src/app/page.tsx",
    reason: "진입점",
};
assertAssignable<DocReadingOrderItem>(readingItem);

// 3. DocDangerFileItem 구조 검증
const dangerItem: DocDangerFileItem = {
    path: "backend/app/core/config.py",
    reason: "환경 변수 직접 노출",
};
assertAssignable<DocDangerFileItem>(dangerItem);

// 4. DocGetJsonData 전체 필드 검증
const jsonData: DocGetJsonData = {
    repoId: "550e8400-e29b-41d4-a716-446655440000",
    repoName: "test-repo",
    summary: "테스트 프로젝트",
    stack: ["Next.js", "FastAPI"],
    readingOrder: [readingItem],
    dangerFiles: [dangerItem],
    coreFlow: "진입점 → 분석 → 결과",
    folderSummaries: [folder],
    generatedAt: "2026-06-29T00:00:00Z",
    version: 1,
};
assertAssignable<DocGetJsonData>(jsonData);

// 5. DocGetJsonData nullable 필드 검증
const jsonDataNullable: DocGetJsonData = {
    repoId: "550e8400-e29b-41d4-a716-446655440000",
    repoName: "test-repo",
    summary: null,
    stack: [],
    readingOrder: [],
    dangerFiles: [],
    coreFlow: null,
    folderSummaries: [],
    generatedAt: "2026-06-29T00:00:00Z",
    version: 0,
};
assertAssignable<DocGetJsonData>(jsonDataNullable);

// 6. DocGetJsonResponse 래퍼 검증
const jsonResponse: DocGetJsonResponse = {
    code: 200,
    message: "ok",
    data: jsonData,
};
assertAssignable<DocGetJsonResponse>(jsonResponse);

// 7. buildFileSummaries 반환 타입 검증
const summaries = buildFileSummaries(
    jsonData.readingOrder,
    jsonData.dangerFiles,
    jsonData.folderSummaries
);
assertAssignable<DocFileSummaryItem[]>(summaries);

// 8. DocFileSummaryItem nullable 필드 검증
const itemNullable: DocFileSummaryItem = {
    path: "backend/app/core/config.py",
    fileName: "config.py",
    priority: null,
    isDanger: true,
    dangerReason: null,
    folderPath: null,
    folderSummary: null,
};
assertAssignable<DocFileSummaryItem>(itemNullable);

// 9. DocFileSummaryItem 완전한 필드 검증
const itemFull: DocFileSummaryItem = {
    path: "src/app/page.tsx",
    fileName: "page.tsx",
    priority: 1,
    isDanger: false,
    dangerReason: null,
    folderPath: "src/app",
    folderSummary: "Next.js App Router 진입 경로",
};
assertAssignable<DocFileSummaryItem>(itemFull);

// 10. buildFileSummaries 빈 입력 검증
const emptySummaries = buildFileSummaries([], [], []);
assertAssignable<DocFileSummaryItem[]>(emptySummaries);

// 11. buildFileSummaries 중복 경로 처리 검증
const overlapping = buildFileSummaries(
    [readingItem],
    [dangerItem],
    [folder]
);
assertAssignable<DocFileSummaryItem[]>(overlapping);

export {};
