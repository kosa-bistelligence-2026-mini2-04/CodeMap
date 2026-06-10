import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const { fixMermaidSyntaxMock } = vi.hoisted(() => ({
    fixMermaidSyntaxMock: vi.fn(),
}));

vi.mock("@/lib/gemini", () => ({
    fixMermaidSyntax: fixMermaidSyntaxMock,
}));

import { POST } from "@/app/api/fix-mermaid/route";

describe("POST /api/fix-mermaid", () => {
    beforeEach(() => {
        fixMermaidSyntaxMock.mockReset();
    });

    it("accepts legacy payload with only code", async () => {
        fixMermaidSyntaxMock.mockResolvedValue("flowchart TD\nA-->B");

        const request = new NextRequest("http://localhost/api/fix-mermaid", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ code: "flowchart TD\nA-->B" }),
        });

        const response = await POST(request);
        const body = await response.json();

        expect(response.status).toBe(200);
        expect(body).toEqual({ fixed: "flowchart TD\nA-->B" });
        expect(fixMermaidSyntaxMock).toHaveBeenCalledWith("flowchart TD\nA-->B", {
            syntaxError: undefined,
            diagramType: undefined,
        });
    });

    it("forwards syntaxError and diagramType when provided", async () => {
        fixMermaidSyntaxMock.mockResolvedValue("classDiagram\nclass Repo");

        const request = new NextRequest("http://localhost/api/fix-mermaid", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
                code: "classDiagram\nclass Repo",
                syntaxError: "Parse error on line 2",
                diagramType: "classDiagram",
            }),
        });

        const response = await POST(request);
        const body = await response.json();

        expect(response.status).toBe(200);
        expect(body).toEqual({ fixed: "classDiagram\nclass Repo" });
        expect(fixMermaidSyntaxMock).toHaveBeenCalledWith("classDiagram\nclass Repo", {
            syntaxError: "Parse error on line 2",
            diagramType: "classDiagram",
        });
    });

    it("returns 400 when code is missing", async () => {
        const request = new NextRequest("http://localhost/api/fix-mermaid", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ syntaxError: "Parse error" }),
        });

        const response = await POST(request);
        const body = await response.json();

        expect(response.status).toBe(400);
        expect(body).toEqual({ error: "Missing code parameter" });
        expect(fixMermaidSyntaxMock).not.toHaveBeenCalled();
    });
});
