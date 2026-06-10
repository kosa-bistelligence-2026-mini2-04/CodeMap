import { describe, expect, test, vi } from "vitest";
import { registerResources } from "@resources";

describe("Resource Registration", () => {
  test("registers server_info resource", () => {
    let capturedName: string | undefined;
    let capturedUri: string | undefined;
    const resourceMock = vi.fn(
      (name: string, uri: string, _handler: unknown) => {
        capturedName = name;
        capturedUri = uri;
      },
    );
    const mockServer = { resource: resourceMock };

    registerResources(mockServer as never);

    expect(resourceMock).toHaveBeenCalledTimes(1);
    expect(capturedName).toBe("server_info");
    expect(capturedUri).toBe("src://server/info");
  });

  test("server_info resource handler returns valid structure", () => {
    let capturedHandler:
      | ((uri: { href: string }) => {
          contents: { uri: string; mimeType: string; text: string }[];
        })
      | undefined;
    const resourceMock = vi.fn(
      (
        _name: string,
        _uri: string,
        handler: (uri: { href: string }) => {
          contents: { uri: string; mimeType: string; text: string }[];
        },
      ) => {
        capturedHandler = handler;
      },
    );
    const mockServer = { resource: resourceMock };

    registerResources(mockServer as never);

    expect(capturedHandler).toBeDefined();
    if (capturedHandler === undefined) {
      throw new Error("Handler should be defined");
    }
    const result = capturedHandler({ href: "src://server/info" });

    expect(result.contents).toHaveLength(1);
    expect(result.contents[0]?.mimeType).toBe("application/json");
    expect(result.contents[0]?.uri).toBe("src://server/info");
  });

  test("server_info resource returns valid JSON with expected properties", () => {
    let capturedHandler:
      | ((uri: { href: string }) => {
          contents: { uri: string; mimeType: string; text: string }[];
        })
      | undefined;
    const resourceMock = vi.fn(
      (
        _name: string,
        _uri: string,
        handler: (uri: { href: string }) => {
          contents: { uri: string; mimeType: string; text: string }[];
        },
      ) => {
        capturedHandler = handler;
      },
    );
    const mockServer = { resource: resourceMock };

    registerResources(mockServer as never);

    if (capturedHandler === undefined) {
      throw new Error("Handler should be defined");
    }
    const result = capturedHandler({ href: "src://server/info" });
    const parsed = JSON.parse(result.contents[0]?.text ?? "{}") as Record<
      string,
      unknown
    >;

    expect(parsed).toHaveProperty("name");
    expect(parsed).toHaveProperty("fullName");
    expect(parsed).toHaveProperty("version");
  });
});
