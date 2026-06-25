export function getRagIndexBanner(status, locale = "ko") {
  if (!status || status === "ready" || status === "pending" || status === "in_progress") {
    return null;
  }
  if (status === "failed") {
    return {
      tone: "error",
      message: locale === "ko"
        ? "AI 벡터 인덱싱 실패 — 키워드 검색으로 대화가 가능합니다."
        : "AI vector indexing failed — keyword-based chat is available.",
    };
  }
  if (status === "empty") {
    return {
      tone: "warning",
      message: locale === "ko"
        ? "벡터화할 유효한 코드가 없습니다 — 키워드 검색으로 대화가 가능합니다."
        : "No valid code to vectorize — keyword-based chat is available.",
    };
  }
  return {
    tone: "warning",
    message: locale === "ko"
      ? "AI 벡터 인덱싱 생략됨 (API 키 미설정) — 키워드 검색으로 대화가 가능합니다."
      : "AI vector indexing skipped (no API key) — keyword-based chat is available.",
  };
}
