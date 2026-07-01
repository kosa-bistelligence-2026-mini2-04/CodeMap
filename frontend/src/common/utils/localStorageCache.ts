import type { JobStatusData, WorkspaceReport as WorkspaceReportData } from "@/common/types/contracts";

export interface AnalysisCacheData {
  job: JobStatusData;
  report: WorkspaceReportData | null;
}

const CACHE_KEYS_KEY = "codemap_analysis_lru_keys";
const CACHE_PREFIX = "codemap_analysis_data_";

function getKeys(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const keysStr = localStorage.getItem(CACHE_KEYS_KEY);
    return keysStr ? JSON.parse(keysStr) : [];
  } catch {
    return [];
  }
}

function saveKeys(keys: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(CACHE_KEYS_KEY, JSON.stringify(keys));
  } catch (e) {
    console.warn("Failed to save cache keys to localStorage", e);
  }
}

/**
 * 캐시에서 데이터를 가져옵니다.
 * 성공적으로 가져오면 LRU 알고리즘에 의해 가장 최근 사용된 항목으로 업데이트됩니다.
 */
export function getAnalysisCache(jobId: string): AnalysisCacheData | null {
  if (typeof window === "undefined") return null;

  try {
    const dataStr = localStorage.getItem(`${CACHE_PREFIX}${jobId}`);
    if (!dataStr) return null;

    const data = JSON.parse(dataStr) as AnalysisCacheData;

    // LRU 갱신: 가장 최근에 접근했으므로 키 목록의 맨 뒤로 보냄
    const keys = getKeys();
    const newKeys = keys.filter((k) => k !== jobId);
    newKeys.push(jobId);
    saveKeys(newKeys);

    return data;
  } catch (e) {
    console.warn("Failed to read from localStorage", e);
    return null;
  }
}

/**
 * 분석 데이터를 캐시에 저장합니다.
 * 기본적으로 최대 5개까지만 유지하며, 초과 시 또는 용량 부족(QuotaExceeded) 시
 * 가장 오래된 항목(LRU)부터 삭제합니다.
 */
export function setAnalysisCache(jobId: string, data: AnalysisCacheData, maxItems: number = 5) {
  if (typeof window === "undefined") return;

  let keys = getKeys();

  // 기존 키가 있으면 먼저 제거 (최신 위치로 다시 추가하기 위해)
  keys = keys.filter((k) => k !== jobId);
  keys.push(jobId);

  // 최대 개수 초과 시 오래된 항목 삭제
  while (keys.length > maxItems) {
    const oldestKey = keys.shift();
    if (oldestKey) {
      localStorage.removeItem(`${CACHE_PREFIX}${oldestKey}`);
    }
  }

  // 데이터 저장 시도 (용량 초과 대응)
  let saved = false;
  while (!saved && keys.length > 0) {
    try {
      localStorage.setItem(`${CACHE_PREFIX}${jobId}`, JSON.stringify(data));
      saved = true;
    } catch (e: unknown) {
      // QuotaExceededError 발생 시 오래된 캐시부터 삭제하며 재시도
      const isQuotaExceeded =
        e instanceof DOMException &&
        (e.name === "QuotaExceededError" ||
          e.name === "NS_ERROR_DOM_QUOTA_REACHED" ||
          e.code === 22 ||
          e.code === 1014);

      if (isQuotaExceeded) {
        // 자기 자신만 남았는데도 초과하면 어쩔 수 없이 포기
        if (keys.length <= 1) {
          console.warn("localStorage is full even after clearing other caches.");
          return; // 저장 실패
        }
        const oldestKey = keys.shift();
        if (oldestKey) {
          localStorage.removeItem(`${CACHE_PREFIX}${oldestKey}`);
        }
      } else {
        console.warn("Failed to write to localStorage", e);
        return; // 알 수 없는 에러면 중단
      }
    }
  }

  // 성공적으로 저장(또는 삭제 후 저장) 완료 시 키 목록 저장
  saveKeys(keys);
}
