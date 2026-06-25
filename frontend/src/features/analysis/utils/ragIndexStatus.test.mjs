import test from "node:test";
import assert from "node:assert/strict";

import { getRagIndexBanner } from "./ragIndexStatus.mjs";

test("legacy completed jobs without rag_index do not show an indexing banner", () => {
  assert.equal(getRagIndexBanner(undefined, "ko"), null);
});

test("pending and in_progress states do not show a fallback banner", () => {
  assert.equal(getRagIndexBanner("pending", "ko"), null);
  assert.equal(getRagIndexBanner("in_progress", "ko"), null);
});

test("empty skipped and failed states show explicit fallback messages", () => {
  assert.match(getRagIndexBanner("empty", "ko").message, /벡터화할 유효한 코드/);
  assert.match(getRagIndexBanner("skipped", "ko").message, /API 키 미설정/);
  assert.match(getRagIndexBanner("failed", "ko").message, /인덱싱 실패/);
});

test("failed state uses error tone while empty and skipped use warning tone", () => {
  assert.equal(getRagIndexBanner("failed", "en").tone, "error");
  assert.equal(getRagIndexBanner("empty", "en").tone, "warning");
  assert.equal(getRagIndexBanner("skipped", "en").tone, "warning");
});
