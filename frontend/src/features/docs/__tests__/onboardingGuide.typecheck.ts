/**
 * DOCS-GEN-F-203 타입 정합성 검증 (tsc --noEmit)
 * OnboardingGuidePanel 프롭 타입과 관련 계약 타입이
 * API 명세(DOCS-GEN-API-001)와 일치하는지 확인합니다.
 */

import type {
    DocReadingOrderItem,
    DocDangerFileItem,
    DocGetJsonData,
} from "@/common/types/contracts";
import type { OnboardingGuidePanelProps } from "../components/OnboardingGuidePanel";

// 타입 보조 함수 — 할당 가능성 검증
function assertAssignable<T>(_val: T): void { /* 타입 검증 전용 */ }


// ── 1. DocReadingOrderItem 형태 검증 ──────────────────────
const readingItem: DocReadingOrderItem = {
    rank: 1,
    path: "backend/app/main.py",
    reason: "FastAPI 진입점",
};
assertAssignable<DocReadingOrderItem>(readingItem);


// ── 2. DocDangerFileItem 형태 검증 ────────────────────────
const dangerItem: DocDangerFileItem = {
    path: "backend/app/infra/config.py",
    reason: "환경변수 관리 파일 — 직접 수정 주의",
};
assertAssignable<DocDangerFileItem>(dangerItem);


// ── 3. 빈 배열 허용 검증 ──────────────────────────────────
const emptyProps: OnboardingGuidePanelProps = {
    readingOrder: [],
    dangerFiles: [],
};
assertAssignable<OnboardingGuidePanelProps>(emptyProps);


// ── 4. 다수 항목 허용 검증 ────────────────────────────────
const fullProps: OnboardingGuidePanelProps = {
    readingOrder: [
        { rank: 1, path: "README.md", reason: "프로젝트 목적 파악" },
        { rank: 2, path: "backend/app/main.py", reason: "앱 진입점" },
        { rank: 3, path: "frontend/src/app/page.tsx", reason: "UI 진입점" },
    ],
    dangerFiles: [
        { path: "backend/app/infra/config.py", reason: "API 키 환경변수" },
        { path: ".env", reason: "시크릿 파일 — 커밋 금지" },
    ],
};
assertAssignable<OnboardingGuidePanelProps>(fullProps);


// ── 5. DocGetJsonData에서 프롭 추출 검증 ──────────────────
declare const jsonData: DocGetJsonData;

const fromJsonData: OnboardingGuidePanelProps = {
    readingOrder: jsonData.readingOrder,
    dangerFiles: jsonData.dangerFiles,
};
assertAssignable<OnboardingGuidePanelProps>(fromJsonData);


// ── 6. readingOrder 요소가 DocReadingOrderItem 배열임을 보장
const orderList: DocReadingOrderItem[] = fullProps.readingOrder;
assertAssignable<DocReadingOrderItem[]>(orderList);


// ── 7. dangerFiles 요소가 DocDangerFileItem 배열임을 보장
const dangerList: DocDangerFileItem[] = fullProps.dangerFiles;
assertAssignable<DocDangerFileItem[]>(dangerList);


// ── 8. rank는 number 타입이어야 함 ────────────────────────
const rank: number = readingItem.rank;
assertAssignable<number>(rank);


// ── 9. path/reason은 string 타입이어야 함 ─────────────────
const itemPath: string = readingItem.path;
const itemReason: string = readingItem.reason;
assertAssignable<string>(itemPath);
assertAssignable<string>(itemReason);


// ── 10. DangerFileItem path/reason은 string ───────────────
const dangerPath: string = dangerItem.path;
const dangerReason: string = dangerItem.reason;
assertAssignable<string>(dangerPath);
assertAssignable<string>(dangerReason);


// ── 11. DocGetJsonData 전체 필드 — F-203 관련 필드 존재 확인
const _readingOrder: DocReadingOrderItem[] = jsonData.readingOrder;
const _dangerFiles: DocDangerFileItem[] = jsonData.dangerFiles;
assertAssignable<DocReadingOrderItem[]>(_readingOrder);
assertAssignable<DocDangerFileItem[]>(_dangerFiles);

export {};
