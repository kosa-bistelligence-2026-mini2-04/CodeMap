import { describe, expect, test } from "vitest";
import { features, getFeature, infoFeature } from "@features/index";

describe("Features Index", () => {
  test("features array contains infoFeature", () => {
    expect(features).toContain(infoFeature);
  });

  test("features array is not empty", () => {
    expect(features.length).toBeGreaterThan(0);
  });

  test("getFeature returns feature by name", () => {
    const feature = getFeature("get_server_info");

    expect(feature).toBeDefined();
    expect(feature?.name).toBe("get_server_info");
  });

  test("getFeature returns undefined for unknown feature", () => {
    const feature = getFeature("unknown_feature");

    expect(feature).toBeUndefined();
  });

  test("all features have required properties", () => {
    for (const feature of features) {
      expect(feature.name).toBeDefined();
      expect(feature.description).toBeDefined();
      expect(feature.schema).toBeDefined();
      expect(feature.execute).toBeDefined();
      expect(typeof feature.execute).toBe("function");
    }
  });
});
