import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReportContent } from "@/app/report/[scan_id]/ReportContent";

const {
    authMock,
    resolveScanFromShareTokenMock,
    peekScanFromShareTokenMock,
    getScanResultWithStatusMock,
    getPreviousScanMock,
    buildReportViewDataMock,
    trackReportConversionEventMock,
} = vi.hoisted(() => ({
    authMock: vi.fn(),
    resolveScanFromShareTokenMock: vi.fn(),
    peekScanFromShareTokenMock: vi.fn(),
    getScanResultWithStatusMock: vi.fn(),
    getPreviousScanMock: vi.fn(),
    buildReportViewDataMock: vi.fn(),
    trackReportConversionEventMock: vi.fn(),
}));

vi.mock("@/lib/services/scan-share-links", () => ({
    resolveScanFromShareToken: resolveScanFromShareTokenMock,
    peekScanFromShareToken: peekScanFromShareTokenMock,
}));

vi.mock("@/lib/auth", () => ({
    auth: authMock,
}));

vi.mock("@/lib/services/scan-storage", () => ({
    getScanResultWithStatus: getScanResultWithStatusMock,
    getPreviousScan: getPreviousScanMock,
}));

vi.mock("@/lib/services/report-service", () => ({
    buildReportViewData: buildReportViewDataMock,
}));

vi.mock("@/lib/analytics", () => ({
    trackReportConversionEvent: trackReportConversionEventMock,
}));

import SharedReportByTokenPage, { generateMetadata } from "@/app/report/shared/[token]/page";

const scan = {
    id: "scan_1",
    owner: "acme",
    repo: "widget",
    timestamp: Date.now(),
    expiresAt: Date.now() + 60_000,
    depth: "deep",
    summary: { total: 1, critical: 1, high: 0, medium: 0, low: 0, info: 0 },
    findings: [],
    userId: "user_1",
};

describe("shared report page token resolution", () => {
    beforeEach(() => {
        resolveScanFromShareTokenMock.mockReset();
        peekScanFromShareTokenMock.mockReset();
        getScanResultWithStatusMock.mockReset();
        getPreviousScanMock.mockReset();
        buildReportViewDataMock.mockReset();
        trackReportConversionEventMock.mockReset();
        authMock.mockReset();
        authMock.mockResolvedValue(null);
    });

    it("returns branded noindex metadata for invalid share links", async () => {
        peekScanFromShareTokenMock.mockResolvedValue({ status: "invalid" });

        const metadata = await generateMetadata({
            params: Promise.resolve({ token: "bad-token" }),
        });

        expect(metadata.title).toBe("Invalid Share Link");
        expect(metadata.robots?.index).toBe(false);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/homepage.png");
    });

    it("builds detailed metadata for valid shared reports", async () => {
        peekScanFromShareTokenMock.mockResolvedValue({
            status: "ok",
            linkId: "link_1",
            scanId: "scan_1",
            expiresAt: new Date(Date.now() + 60_000),
        });
        getScanResultWithStatusMock.mockResolvedValue({ status: "ok", scan });

        const metadata = await generateMetadata({
            params: Promise.resolve({ token: "valid-token" }),
        });

        expect(metadata.title).toBe("Shared Security Report: acme/widget");
        expect(metadata.robots?.index).toBe(false);
        expect(metadata.openGraph?.images?.[0]?.url).toBe("/og/security-scan-report.png");
    });

    it("tracks invalid link events", async () => {
        resolveScanFromShareTokenMock.mockResolvedValue({ status: "expired" });

        const view = await SharedReportByTokenPage({
            params: Promise.resolve({ token: "bad-token" }),
        }) as ReactElement;

        expect(view.type).not.toBe(ReportContent);
        expect(trackReportConversionEventMock).toHaveBeenCalledWith("report_expired_viewed", undefined, {
            actorUsername: null,
        });
    });

    it("renders shared report content when token resolves", async () => {
        resolveScanFromShareTokenMock.mockResolvedValue({
            status: "ok",
            linkId: "link_1",
            scanId: "scan_1",
            expiresAt: new Date(Date.now() + 60_000),
        });
        getScanResultWithStatusMock.mockResolvedValue({ status: "ok", scan });
        getPreviousScanMock.mockResolvedValue(null);
        buildReportViewDataMock.mockReturnValue({
            priorScanDiff: { new: 1, resolved: 0, unchanged: 0 },
            topFixes: [],
            findingViews: [],
            globalFixPrompt: "Fix everything",
            globalChatHref: "/chat?q=acme%2Fwidget&prompt=Fix%20everything",
        });

        const view = await SharedReportByTokenPage({
            params: Promise.resolve({ token: "valid-token" }),
        }) as ReactElement<{
            isSharedView: boolean;
            canShareReport: boolean;
            canGenerateOutreach: boolean;
            shareMode: string;
            globalFixPrompt: string;
            globalChatHref: string;
        }>;

        expect(trackReportConversionEventMock).toHaveBeenCalledWith("report_viewed_shared", "scan_1", {
            actorUsername: null,
        });
        expect(view.type).toBe(ReportContent);
        expect(view.props.isSharedView).toBe(true);
        expect(view.props.canShareReport).toBe(true);
        expect(view.props.canGenerateOutreach).toBe(false);
        expect(view.props.shareMode).toBe("copy-current-url");
        expect(view.props.globalFixPrompt).toBe("Fix everything");
        expect(view.props.globalChatHref).toContain("/chat?q=acme%2Fwidget");
    });

    it("renders expired report state when scan has expired", async () => {
        resolveScanFromShareTokenMock.mockResolvedValue({
            status: "ok",
            linkId: "link_1",
            scanId: "scan_1",
            expiresAt: new Date(Date.now() + 60_000),
        });
        getScanResultWithStatusMock.mockResolvedValue({ status: "expired", scan });

        const view = await SharedReportByTokenPage({
            params: Promise.resolve({ token: "valid-token" }),
        }) as ReactElement;

        expect(view.type).not.toBe(ReportContent);
        expect(trackReportConversionEventMock).toHaveBeenCalledWith("report_expired_viewed", "scan_1", {
            actorUsername: null,
        });
    });
});
