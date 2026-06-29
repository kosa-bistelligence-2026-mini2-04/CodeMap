/**
 * DOCS-GEN-F-202 타입 검증 — tsc --noEmit 으로 실행
 */
import type {
    DocFolderSummary,
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

// 2. DocGetJsonData 구조 검증 (전체 필드)
const jsonData: DocGetJsonData = {
    summary: "테스트 프로젝트 요약",
    stack: ["Next.js", "FastAPI"],
    readingOrder: ["src/app/page.tsx", "src/features/auth/utils/tokenMemory.ts"],
    dangerFiles: ["backend/app/core/config.py"],
    coreFlow: "진입점 → 분석 → 결과",
    folderSummaries: [folder],
    generatedAt: "2026-06-29T00:00:00Z",
    version: 1,
};
assertAssignable<DocGetJsonData>(jsonData);

// 3. DocGetJsonData nullable 필드 검증
const jsonDataNullable: DocGetJsonData = {
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

// 4. DocGetJsonResponse 래퍼 검증
const jsonResponse: DocGetJsonResponse = {
    code: 200,
    message: "ok",
    data: jsonData,
};
assertAssignable<DocGetJsonResponse>(jsonResponse);

// 5. buildFileSummaries 반환 타입 검증
const summaries = buildFileSummaries(
    jsonData.readingOrder,
    jsonData.dangerFiles,
    jsonData.folderSummaries
);
assertAssignable<DocFileSummaryItem[]>(summaries);

// 6. DocFileSummaryItem priority null 허용 검증
const itemWithNullPriority: DocFileSummaryItem = {
    path: "backend/app/core/config.py",
    fileName: "config.py",
    priority: null,
    isDanger: true,
    folderPath: null,
    folderSummary: null,
};
assertAssignable<DocFileSummaryItem>(itemWithNullPriority);

// 7. DocFileSummaryItem 완전한 필드 검증
const itemFull: DocFileSummaryItem = {
    path: "src/app/page.tsx",
    fileName: "page.tsx",
    priority: 1,
    isDanger: false,
    folderPath: "src/app",
    folderSummary: "Next.js App Router 진입 경로",
};
assertAssignable<DocFileSummaryItem>(itemFull);

// 8. buildFileSummaries 빈 입력 검증
const emptySummaries = buildFileSummaries([], [], []);
assertAssignable<DocFileSummaryItem[]>(emptySummaries);

// 9. buildFileSummaries 중복 경로 처리 검증 (danger와 readingOrder 동시 등록)
const overlapping = buildFileSummaries(
    ["src/app/page.tsx"],
    ["src/app/page.tsx"],
    [folder]
);
assertAssignable<DocFileSummaryItem[]>(overlapping);

export {};
