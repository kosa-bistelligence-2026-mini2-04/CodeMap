import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const { authMock, isAdminUserMock, getAnalyticsDetailsMock } = vi.hoisted(() => ({
    authMock: vi.fn(),
    isAdminUserMock: vi.fn(),
    getAnalyticsDetailsMock: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
    auth: authMock,
}));

vi.mock("@/lib/admin-auth", () => ({
    isAdminUser: isAdminUserMock,
}));

vi.mock("@/lib/analytics", () => ({
    getAnalyticsDetails: getAnalyticsDetailsMock,
}));

import { GET } from "@/app/api/admin/stats/details/route";

describe("GET /api/admin/stats/details", () => {
    beforeEach(() => {
        authMock.mockReset();
        isAdminUserMock.mockReset();
        getAnalyticsDetailsMock.mockReset();

        getAnalyticsDetailsMock.mockResolvedValue({
            activeNow: 0,
            activeUsers24h: 0,
            returningUsers30d: 0,
            retentionRate30d: 0,
            recentVisitors: [],
            loggedInUsers: [],
            nextVisitorCursor: null,
            nextLoggedInCursor: null,
        });
    });

    it("returns 403 for non-admin users", async () => {
        authMock.mockResolvedValue({ user: { id: "u_1" } });
        isAdminUserMock.mockReturnValue(false);

        const response = await GET(new NextRequest("http://localhost/api/admin/stats/details"));
        expect(response.status).toBe(403);
        expect(getAnalyticsDetailsMock).not.toHaveBeenCalled();
    });

    it("uses default limits of 10 when params are absent", async () => {
        authMock.mockResolvedValue({ user: { id: "u_1" } });
        isAdminUserMock.mockReturnValue(true);

        const response = await GET(new NextRequest("http://localhost/api/admin/stats/details"));
        expect(response.status).toBe(200);
        expect(getAnalyticsDetailsMock).toHaveBeenCalledWith({
            visitorLimit: 10,
            visitorCursor: null,
            loggedInLimit: 10,
            loggedInCursor: null,
            includeSelection: true,
            includeFunnel: true,
            includeFalsePositiveReview: false,
            includeKvHistory: true,
        });
    });

    it("clamps custom limits to route bounds", async () => {
        authMock.mockResolvedValue({ user: { id: "u_1" } });
        isAdminUserMock.mockReturnValue(true);

        const response = await GET(
            new NextRequest("http://localhost/api/admin/stats/details?visitorLimit=999&loggedInLimit=0")
        );
        expect(response.status).toBe(200);
        expect(getAnalyticsDetailsMock).toHaveBeenCalledWith({
            visitorLimit: 100,
            visitorCursor: null,
            loggedInLimit: 1,
            loggedInCursor: null,
            includeSelection: true,
            includeFunnel: true,
            includeFalsePositiveReview: false,
            includeKvHistory: true,
        });
    });

    it("passes cursors when provided", async () => {
        authMock.mockResolvedValue({ user: { id: "u_1" } });
        isAdminUserMock.mockReturnValue(true);

        const response = await GET(
            new NextRequest("http://localhost/api/admin/stats/details?visitorCursor=20&loggedInCursor=30")
        );
        expect(response.status).toBe(200);
        expect(getAnalyticsDetailsMock).toHaveBeenCalledWith({
            visitorLimit: 10,
            visitorCursor: "20",
            loggedInLimit: 10,
            loggedInCursor: "30",
            includeSelection: true,
            includeFunnel: true,
            includeFalsePositiveReview: false,
            includeKvHistory: true,
        });
    });
});
