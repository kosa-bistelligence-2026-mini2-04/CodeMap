/**
 * DOCS-GUARD-API-001 타입 검증 — tsc --noEmit 으로 실행
 * DocGuardPatternItem / DocGuardData / DocGuardResponse 와
 * callGuardCheck 반환 타입이 DOCS-GUARD-API-001 명세와 일치하는지 확인합니다.
 */

import type {
    DocGuardPatternItem,
    DocGuardData,
    DocGuardResponse,
} from "@/common/types/contracts";
import type { RiskWarningModalProps } from "../components/RiskWarningModal";
import { callGuardCheck } from "../api/docsApi";

// 타입 보조 함수 — 할당 가능성 검증
function assertAssignable<T>(_val: T): void {
    void _val;
}


// ── 1. DocGuardPatternItem 형태 검증 ─────────────────────────
const pattern: DocGuardPatternItem = {
    type: "api_key",
    location: "document",
};
assertAssignable<DocGuardPatternItem>(pattern);


// ── 2. DocGuardData 형태 검증 ────────────────────────────────
const guardData: DocGuardData = {
    maskedContent: "## 설정\nOPENAI_API_KEY=[MASKED]",
    detectedCount: 1,
    detectedPatterns: [pattern],
};
assertAssignable<DocGuardData>(guardData);


// ── 3. detectedPatterns 빈 배열 허용 ─────────────────────────
const guardDataEmpty: DocGuardData = {
    maskedContent: "# 가이드북 내용",
    detectedCount: 0,
    detectedPatterns: [],
};
assertAssignable<DocGuardData>(guardDataEmpty);


// ── 4. DocGuardResponse 래퍼 검증 ────────────────────────────
const guardResp: DocGuardResponse = {
    code: 200,
    message: "success",
    data: guardData,
};
assertAssignable<DocGuardResponse>(guardResp);


// ── 5. 탐지 없음 응답 검증 ───────────────────────────────────
const guardRespClean: DocGuardResponse = {
    code: 200,
    message: "success",
    data: guardDataEmpty,
};
assertAssignable<DocGuardResponse>(guardRespClean);


// ── 6. callGuardCheck 반환 타입이 Promise<DocGuardResponse> ──
const _callResult: Promise<DocGuardResponse> = callGuardCheck(
    "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
    "# 온보딩\nAPI_KEY=sk-abcdefghijklmnopqrstuvwxyz01234567890123456789",
);
assertAssignable<Promise<DocGuardResponse>>(_callResult);


// ── 7. RiskWarningModalProps — 탐지 있음 ─────────────────────
const modalPropsWithWarning: RiskWarningModalProps = {
    detectedCount: 2,
    detectedPatterns: [
        { type: "openai_key", location: "document" },
        { type: "password_literal", location: "document" },
    ],
};
assertAssignable<RiskWarningModalProps>(modalPropsWithWarning);


// ── 8. RiskWarningModalProps — 탐지 없음 ─────────────────────
const modalPropsClean: RiskWarningModalProps = {
    detectedCount: 0,
    detectedPatterns: [],
};
assertAssignable<RiskWarningModalProps>(modalPropsClean);


// ── 9. RiskWarningModalProps — onClose optional ───────────────
const modalPropsNoClose: RiskWarningModalProps = {
    detectedCount: 1,
    detectedPatterns: [{ type: "jwt_token", location: "document" }],
};
assertAssignable<RiskWarningModalProps>(modalPropsNoClose);

const modalPropsWithClose: RiskWarningModalProps = {
    detectedCount: 1,
    detectedPatterns: [{ type: "jwt_token", location: "document" }],
    onClose: () => { /* 닫기 핸들러 */ },
};
assertAssignable<RiskWarningModalProps>(modalPropsWithClose);


// ── 10. DocGuardPatternItem 필드 타입 확인 ───────────────────
const patternType: string = pattern.type;
const patternLoc: string = pattern.location;
assertAssignable<string>(patternType);
assertAssignable<string>(patternLoc);


// ── 11. 다수 패턴 타입 혼합 검증 ─────────────────────────────
const multiPatterns: DocGuardPatternItem[] = [
    { type: "aws_access_key", location: "document" },
    { type: "github_token", location: "document" },
    { type: "db_connection", location: "document" },
];
assertAssignable<DocGuardPatternItem[]>(multiPatterns);

export {};
