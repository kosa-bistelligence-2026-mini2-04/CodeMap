# 임베딩 모델 선택 근거: text-embedding-3-large + dimensions=1536

> [!NOTE]
> 본 문서는 CodeMap 프로젝트에서 사용할 임베딩 모델(text-embedding-3-small 1536차원 vs text-embedding-3-large 3072차원 vs text-embedding-3-large + dimensions=1536)에 대한 기술 검토 및 최종 선택 근거를 정리한 아키텍처 결정 문서입니다.

---

## 1. 배경: 이 프로젝트에서 임베딩의 역할

CodeMap의 검색 문제는 **"깊은 의미 검색"보다 "구조 탐색 + 근거 찾기"** 에 가깝습니다.

실행 방법, 환경변수, 라우터, DB 연결, 인증 로직 같은 핵심 정보는 대부분 아래처럼 **명시적인 단서**로 존재합니다.

| 카테고리 | 대표 파일/키워드 |
| --- | --- |
| 실행 방법 | `README.md`, `package.json`, `requirements.txt`, `Dockerfile`, `docker-compose.yml` |
| 환경 설정 | `.env.example`, `config/`, `settings/` |
| 라우팅 | `router/`, `controller/`, `service/` |
| 인증 | `auth/`, `token/`, `jwt/`, `session/`, `user/` |
| DB 연결 | `database/`, `db/`, `model/`, `schema/` |

따라서 임베딩은 **"전체 문제를 해결하는 핵심 엔진"이라기보다 키워드 검색이 놓친 관련 코드 조각을 보완하고, LLM에게 넣을 근거 후보를 좁히는 보조 검색 레이어**입니다.

---

## 2. 선택지 비교

### Option A — `text-embedding-3-small` (1536차원)

| 항목 | 내용 |
| --- | --- |
| 비용 | 가장 저렴 |
| 속도 | 가장 빠름 |
| 구현 복잡도 | 낮음 |
| 한국어→영어 코드 검색 | small보다 large가 유리 (MIRACL 벤치마크 기준 차이 존재) |
| 추천 상황 | 빠른 MVP, 비용 절감, 구조 탐색 중심 프로젝트 |

**한계**: 사용자가 한국어로 "로그인한 사용자의 권한은 어디서 확인하나요?"라고 질문했을 때, 실제 코드에서는 `authorizeRequest`, `permissionGuard`, `validateSession`, `getPrincipal` 같은 영어 식별자로 존재합니다. 단순 키워드 검색만으로는 놓치는 케이스가 생기고, small 임베딩은 이 의미적 다리를 large만큼 잘 연결하지 못할 수 있습니다.

---

### Option B — `text-embedding-3-large` (3072차원 기본값)

| 항목 | 내용 |
| --- | --- |
| 의미 검색 품질 | 가장 높음 |
| 다국어 검색 | MIRACL 벤치마크에서 small 대비 유의미한 우위 |
| 비용 | small 대비 높음 |
| 저장공간 | chunk당 3072차원 → 저장 용량 2배 이상 |
| 검색 속도 | 차원 증가로 ANN 검색 부담 증가 |
| pgvector 제약 | IVFFlat 인덱스 기준 2000차원 이하 권장 → 3072차원은 HNSW 또는 full scan 필요 |
| 추천 상황 | 기업용 SaaS, 대규모 레포, semantic search 중심 서비스 |

**한계**: 레포 하나 분석 시 생성되는 chunk 수가 많아질수록 저장 비용과 인덱스 구성 복잡도가 비선형으로 증가합니다. MVP 단계에서 기본값 3072차원을 고집하면 운영 부담이 예상보다 커질 수 있습니다.

---

### Option C — `text-embedding-3-large` + `dimensions=1536` ✅ **채택**

| 항목 | 내용 |
| --- | --- |
| 의미 검색 품질 | large 모델 기반 → small보다 우수, 특히 한국어↔영어 크로스링구얼 검색 |
| 차원 | 1536 (small과 동일) → 저장공간, 검색속도, pgvector 제약 해소 |
| 비용 | small보다 높지만 3072차원보다 낮음 |
| pgvector 호환 | IVFFlat 인덱스 정상 사용 가능 |
| 구현 복잡도 | API 파라미터 하나 추가로 전환 가능 |
| 추천 상황 | MVP 이후 실제 서비스 확장까지 고려하는 현재 프로젝트 |

**핵심 이유**: `text-embedding-3-large`는 OpenAI의 `dimensions` 파라미터를 통해 출력 차원을 줄여도 모델의 학습된 표현 공간 자체는 large 품질을 유지합니다. 즉, **같은 저장 공간과 검색 속도로 large의 다국어 검색 강점을 활용**할 수 있는 절충안입니다.

```python
# 적용 예시
response = openai.embeddings.create(
    model="text-embedding-3-large",
    input=text,
    dimensions=1536  # ← 핵심 파라미터
)
```

---

## 3. 검색 결과 품질에 더 크게 영향을 주는 요소

임베딩 모델 선택보다 아래 요소들이 실제 검색 품질에 더 크게 작용한다는 점도 설계에 반영합니다.

| 요소 | 적용 방향 |
| --- | --- |
| **청킹 전략** | AST 기반 함수/클래스 단위 분리 (RAG-PARSE-B-207) |
| **파일 경로/파일명 메타데이터** | chunk에 `file_path`, `symbol`, `language` 포함 |
| **설정/핵심 파일 우선순위** | README, package.json, requirements.txt 등을 가중치 부스트 |
| **하이브리드 검색** | 정적 분석 + 키워드 검색 + 벡터 검색 결합 |
| **Reranking** | Thinking 모드에서 추가 적용 |
| **근거 파일 표시** | LLM 응답에 출처 파일명 + 라인 번호 포함 |

---

## 4. Lite / Thinking 모드 구분 전략

> [!IMPORTANT]
> 같은 vector index 안에서는 **임베딩 모델과 차원을 반드시 통일**해야 합니다.
> 문서 chunk는 `text-embedding-3-large + dimensions=1536`으로 만들고, 사용자 질문을 다른 모델로 임베딩하면 embedding space가 달라져 유사도 비교 품질이 손상됩니다.

두 모드 모두 **동일한 임베딩 인덱스**를 사용하고, 차이는 **검색 전략과 생성 모델**에서만 둡니다.

| 항목 | Lite 모드 | Thinking 모드 |
| --- | --- | --- |
| 임베딩 인덱스 | `text-embedding-3-large + dims=1536` | 동일 |
| top_k | 작게 (예: 5~10) | 크게 (예: 20~30) |
| 검색 전략 | 단일 쿼리 벡터 검색 | Multi-query retrieval + Reranking |
| 생성 모델 | GPT-4o-mini (빠른 요약) | GPT-4o (심층 분석) |
| 분석 범위 | 실행 방법, 폴더 구조, 주요 파일 | 인증/DB/API 흐름, 읽는 순서, 근거 파일 상세 |
| 응답 시간 | 빠름 | 상세하지만 더 소요 |

이 방식으로 임베딩 인덱스는 하나만 관리하면서도 두 모드의 분석 깊이 차이를 만들 수 있습니다.

---

## 5. 최종 결정

```
임베딩 모델:  text-embedding-3-large + dimensions=1536
벡터 스토어:  pgvector (PostgreSQL)
인덱스 타입:  IVFFlat (1536차원 범위 내 정상 동작)
검색 방식:    하이브리드 (정적 분석 + 키워드 + 벡터)
Lite/Thinking: 동일 인덱스, 검색 전략과 생성 모델로 차이
```

| 평가 기준 | small 1536 | large 3072 | **large 1536 (채택)** |
| --- | :---: | :---: | :---: |
| 한국어↔영어 의미 검색 | △ | ✅ | ✅ |
| 저장공간 효율 | ✅ | ❌ | ✅ |
| 검색 속도 | ✅ | △ | ✅ |
| pgvector IVFFlat 호환 | ✅ | ❌ | ✅ |
| MVP→서비스 확장성 | △ | ✅ | ✅ |
| 구현 복잡도 | ✅ | △ | ✅ |

---

---

## 6. 팀 논의: 검색 속도 우려 및 서버 환경 검토

> [!NOTE]
> 2026-06-19 팀 논의 내용 기록. 원본 대화 참조: https://chatgpt.com/share/6a34cdd4-4e3c-83e8-8f47-5d8bafad82d7

### Q. `large + dimensions=1536` 사용 시 검색 속도가 느려질 수 있지 않나?

**결론: 우려 수준의 문제는 아님. 단 규모가 커지면 모니터링 필요.**

#### 속도에 영향을 주는 요소와 실제 부담

임베딩 차원 수가 검색 속도에 영향을 주는 것은 맞지만, 실제 부담이 발생하는 구간은 아래와 같습니다.

| 요소 | 설명 |
| --- | --- |
| **벡터 유사도 계산 자체** | 1536차원 코사인 유사도는 CPU/메모리 연산이라 빠름. 차원 2배 = 연산량 2배이지만 절대값이 작음 |
| **ANN 인덱스 (IVFFlat)** | 1536차원은 pgvector IVFFlat 권장 범위 내. 수십만 chunk까지는 수십ms 내 검색 가능 |
| **full scan (인덱스 없음)** | chunk 수천 개 수준에서는 full scan도 수ms 수준. 수십만 개부터 부담 증가 |
| **네트워크/LLM 응답** | 실제 사용자 체감 지연의 대부분은 벡터 검색이 아닌 LLM 생성 단계에서 발생 |

**MVP 규모 예상치**: 레포 1개 분석 시 chunk 수 = 수백~수천 개 수준. 이 규모에서는 1536차원 IVFFlat 검색이 병목이 되기 어렵습니다.

#### Q. 서버가 64비트 공용 PC라서 크게 관계 없지 않나?

**맞습니다. 다만 "64비트"보다 "RAM 용량"과 "pgvector 인덱스 설정"이 더 핵심 변수입니다.**

| 환경 요소 | 검색 속도 영향 |
| --- | --- |
| **64비트 아키텍처** | SIMD 명령어(AVX2 등) 지원 → 벡터 연산 가속. 32비트 대비 실질적 이점 있음 |
| **RAM 용량** | pgvector IVFFlat 인덱스가 메모리에 올라가야 빠름. RAM 부족 시 디스크 I/O 발생 |
| **공용 PC 공유 부하** | 다른 프로세스와 CPU/RAM 경합 가능. 단독 서버 대비 불안정할 수 있음 |

64비트 환경은 SIMD 명령어를 통해 벡터 연산 자체를 가속하므로 "크게 관계없다"는 의견이 맞습니다. 단, 공용 PC의 전체 RAM과 pgvector가 사용할 수 있는 메모리 여유분이 핵심입니다.

#### Q. 문제가 생기면 MacBook Pro 64GB RAM을 활용하는 방법은?

**충분히 현실적인 대안입니다.** 아래 방식으로 전환 가능합니다.

| 방식 | 설명 |
| --- | --- |
| **PostgreSQL + pgvector 로컬 실행** | MacBook Pro에서 직접 실행. 64GB RAM → 대용량 인덱스도 메모리에 적재 가능 |
| **포트 포워딩으로 팀 공유** | `ngrok` 또는 SSH 터널링으로 팀원이 로컬 DB에 접근하도록 구성 |
| **Docker 기반** | `docker run -e POSTGRES_PASSWORD=... pgvector/pgvector` 로 즉시 실행 가능 |
| **성능 이점** | Apple Silicon M-series는 통합 메모리 구조 → 메모리 대역폭이 일반 PC 대비 높아 벡터 연산에 유리 |

### 정리: 속도 걱정 없이 `large + dims=1536`으로 진행해도 됩니다

```
MVP 규모 (레포 1개, chunk 수백~수천): 속도 이슈 없음
중간 규모 (레포 수십 개, chunk 수만): IVFFlat + 적절한 lists 설정으로 대응
대규모 (chunk 수십만+): HNSW 인덱스 전환 고려 또는 pgvector → Qdrant/Weaviate 마이그레이션

현 단계 우선순위: 검색 속도보다 LLM 생성 품질과 청킹 전략이 훨씬 중요
```

---

> **참고 문서**
> - [OpenAI Embeddings 공식 문서](https://platform.openai.com/docs/guides/embeddings)
> - [text-embedding-3 모델 발표 (OpenAI)](https://openai.com/blog/new-embedding-models-and-api-updates)
> - [MIRACL 다국어 검색 벤치마크](https://github.com/project-miracl/miracl)
> - [pgvector 인덱싱 가이드](https://github.com/pgvector/pgvector#indexing)
> - 관련 내부 문서: [`docs/04_Decisions/MODEL_SELECTION_EVIDENCE.md`](MODEL_SELECTION_EVIDENCE.md)
> - 관련 기능 명세: [`docs/03_Specifications/rag/RAG_EMBED_SPEC.md`](../03_Specifications/rag/RAG_EMBED_SPEC.md)
