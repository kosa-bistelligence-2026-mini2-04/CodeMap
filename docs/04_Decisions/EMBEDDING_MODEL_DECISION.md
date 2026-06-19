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
| pgvector 호환 | HNSW 인덱스 정상 사용 가능 |
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
인덱스 타입:  HNSW (IVFFlat 대비 빠른 빌드 시간, 증분 삽입 지원, 1536차원에서 안정적 성능)
검색 방식:    하이브리드 (정적 분석 + 키워드 + 벡터)
Lite/Thinking: 동일 인덱스, 검색 전략과 생성 모델로 차이
```

| 평가 기준 | small 1536 | large 3072 | **large 1536 (채택)** |
| --- | :---: | :---: | :---: |
| 한국어↔영어 의미 검색 | △ | ✅ | ✅ |
| 저장공간 효율 | ✅ | ❌ | ✅ |
| 검색 속도 | ✅ | △ | ✅ |
| pgvector HNSW 호환 | ✅ | ❌ | ✅ |
| MVP→서비스 확장성 | △ | ✅ | ✅ |
| 구현 복잡도 | ✅ | △ | ✅ |

---

---

## 6. 팀 논의: 검색 속도 우려 및 서버 환경 검토

> [!NOTE]
> 2026-06-19 팀 논의 내용 기록. 원본 대화 참조: https://chatgpt.com/share/6a34cdd4-4e3c-83e8-8f47-5d8bafad82d7

### 결론

**`text-embedding-3-large + dimensions=1536` 때문에 검색 속도가 심각하게 느려질 가능성은 낮다.**

팀프로젝트 / MVP / 레포 단위 분석 규모에서 병목은 **검색 속도**가 아니라 아래 쪽에서 생길 가능성이 더 크다.

```
1. GitHub 레포 clone 시간
2. 파일 읽기 / 필터링 / chunking 시간
3. OpenAI API로 embedding 생성하는 시간
4. LLM이 최종 분석 문서를 생성하는 시간
5. DB 인덱스 없이 전체 vector scan 하는 경우
```

즉, 걱정해야 할 포인트는 **"large 1536이라 검색이 느리다"** 보다:

> **임베딩 생성 시간이 얼마나 걸리는가, 벡터 인덱스를 잘 잡았는가, chunk 수가 너무 많지 않은가**

---

### 6-1. "64비트 PC라서 괜찮다"는 의견 — 반은 맞고 반은 애매함

64비트인 것은 기본 조건에 가깝고, 속도를 직접 보장하는 요소는 아니다.

검색 속도에 더 중요한 요소:

```
CPU 성능
RAM 용량
SSD 여부
PostgreSQL/벡터DB 설정
인덱스 사용 여부
chunk 개수
동시 사용자 수
벡터 차원 수
```

따라서 "64비트라서 괜찮다"보다:

> **공용 PC의 RAM이 충분하고, SSD를 쓰고, 벡터 인덱스를 제대로 만들고, chunk 수가 과도하지 않으면 괜찮다**

라고 보는 게 맞다.

64비트 자체는 "큰 메모리를 쓸 수 있다"는 의미에 가깝지, 벡터 검색이 자동으로 빨라진다는 뜻은 아님.

---

### 6-2. `large + dimensions=1536`이면 3072보다 훨씬 부담이 적음

핵심: large 기본 3072차원을 쓰는 게 아니라 **large 모델을 쓰되 결과 벡터를 1536차원으로 줄이는 것**이다.

DB 검색 관점에서:

```
text-embedding-3-small 1536
text-embedding-3-large dimensions=1536
```

둘 다 **검색 시 벡터 차원은 1536**이다. 검색 속도만 놓고 보면 두 모델의 차이는 "임베딩 모델 차이"가 아니라 **같은 1536차원 벡터를 검색하는 문제**가 된다.

차이가 생기는 곳:

```
embedding 생성 단계:
  small이 더 저렴하고 빠를 가능성이 높음
  large가 더 비싸고 느릴 가능성이 있음

vector search 단계:
  둘 다 1536차원이면 검색 부담은 비슷함
```

따라서 팀원에게 이렇게 설명하면 된다.

> `text-embedding-3-large + dimensions=1536`은 검색 단계에서는 1536차원 벡터를 쓰는 것이기 때문에, 3072차원 large를 그대로 쓰는 것보다 검색/저장 부담이 훨씬 낮다. 속도 차이는 검색보다 임베딩 생성 API 호출 쪽에서 더 생길 가능성이 크다.

---

### 6-3. 실제 병목은 "검색"보다 "임베딩 생성"일 가능성이 큼

레포를 처음 분석할 때 각 chunk를 OpenAI embedding API에 보내야 한다.

예시 — 레포에서 chunk가 500개 생기면:

```
500개 chunk
→ embedding API 요청
→ embedding 저장
```

이 단계가 시간이 걸린다. 반면 저장된 벡터에서 top-k 검색하는 건, 데이터가 엄청 많지 않으면 꽤 빠른 편이다.

사용자 경험상 느리게 느껴지는 구간은 보통:

```
"레포 분석 중..."
```

이지,

```
"이미 분석된 레포에서 질문 검색 중..."
```

이 아닐 가능성이 크다.

#### A. 최초 분석 속도

```
GitHub clone
파일 필터링
chunking
embedding 생성      ← 느릴 수 있음 (한 번만 하는 작업)
DB 저장
```

`large`를 쓰면 `small`보다 비용/응답 시간이 늘 수 있다. 하지만 **한 번만 하는 작업**이다.

#### B. 질문 검색 속도

```
사용자 질문 embedding 생성 (1회)
vector search                     ← 빠름
관련 chunk top_k 추출
LLM 답변 생성                     ← 가장 느린 구간
```

검색 자체보다 **질문 embedding 1회 + LLM 답변 생성**이 더 큰 비중이다.

#### C. 온보딩 문서 생성 속도

```
섹션별 retrieval 여러 번
LLM 요약 여러 번
최종 문서 합치기
```

검색보다 LLM 생성 시간이 훨씬 클 가능성이 높다.

---

### 6-4. 공용 PC vs MacBook Pro 64GB

#### 공용 PC로 충분한 경우

```
동시 사용자가 거의 없음
분석하는 레포가 몇 개 안 됨
chunk 수가 수천~수만 이하
PostgreSQL + pgvector 또는 Chroma/FAISS 인덱스 사용
SSD 사용
RAM 16GB 이상
```

팀프로젝트 시연/MVP라면 보통 이 정도로 충분하다.

#### MacBook Pro 64GB가 유리한 경우

```
Docker로 백엔드/프론트/DB/vector store를 같이 띄움
레포 chunk 수가 많음
여러 레포를 반복 분석함
로컬 벡터DB/FAISS/Chroma를 메모리에 올림
개발 중 재색인/테스트를 자주 함
공용 PC 성능이나 권한이 불안정함
```

MacBook Pro는 **개발/테스트/데모 서버**로 좋은 선택이다.

단, OpenAI 임베딩은 어차피 API 호출이기 때문에, MacBook RAM이 많다고 임베딩 API 자체가 빨라지는 건 아니다.

MacBook Pro 64GB가 도와주는 건 주로:

```
로컬 DB
Docker
파일 처리
벡터 인덱스
동시 실행 안정성
개발 환경 안정성
```

---

### 6-5. 속도 걱정보다 "측정 가능하게 설계"하는 게 중요

모델을 논쟁으로 정하기보다, **분석 파이프라인에서 아래 시간을 로그로 기록**하면 된다.

```
repo_clone_time
file_scan_time
chunking_time
embedding_time
db_insert_time
indexing_time
retrieval_time
llm_generation_time
total_analysis_time
```

예시 결과:

```
clone:          3.2s
file scan:      0.8s
chunking:       1.1s
embedding:     18.5s   ← 병목
db insert:      1.7s
retrieval:      0.2s   ← 빠름
llm generation: 25.0s  ← 병목
```

이 결과가 나오면 검색 속도 걱정은 별로 의미 없고, **embedding과 generation을 최적화**해야 하는 것이다. 이런 방식으로 설계하면 팀 내 의사결정도 훨씬 깔끔해진다.

---

### 6-6. 속도 문제가 생기면 최적화 우선순위

속도가 걱정된다면 모델을 바로 낮추기보다 아래 순서로 최적화한다.

#### 1순위: 불필요 파일 제외 (가장 중요)

```
.git / node_modules / dist / build
.venv / venv / __pycache__ / coverage
.cache / .next
이미지, 동영상, 폰트
lock 파일 일부 (package-lock.json 등)
minified 파일
```

이걸 안 하면 임베딩 비용과 시간이 폭발한다.

#### 2순위: chunk 수 제한

처음부터 모든 파일을 다 임베딩하지 말고, 중요 파일 중심으로 가도 충분하다.

```
README
package/requirements/pyproject
Dockerfile / docker-compose.yml
.env.example
src/app 주요 코드
router/controller/service/model/config
```

#### 3순위: 캐싱

같은 레포/같은 commit hash는 다시 임베딩하지 않도록 구성한다.

```
캐시 키: repo_url + commit_hash + file_path + content_hash
```

#### 4순위: 배치 임베딩

```
Bad:  chunk 1개당 API 1번 → API overhead 큼
Good: chunk 여러 개를 batch로 API 요청 → 훨씬 효율적
```

#### 5순위: 인덱스 사용

pgvector를 쓴다면 HNSW나 IVFFlat 인덱스를 반드시 사용한다. 데이터가 적을 때는 큰 차이가 안 나도, chunk가 늘어나면 필수이다.

#### 6순위: Lite / Thinking 분리

속도 최적화는 임베딩 모델을 둘로 나누기보다 retrieval/LLM 쪽에서 나누는 게 좋다.

```
Lite 모드:
  top_k 5
  섹션 수 적게
  짧은 답변
  빠른 생성 모델 (GPT-4o-mini)

Thinking 모드:
  top_k 15~20
  섹션별 multi-query
  reranking
  상세 답변
  강한 생성 모델 (GPT-4o)
```

---

### 6-7. 임베딩을 Lite/Thinking에서 다르게 하면 속도 이점이 있을까?

기술적으로 가능하지만 **초기에는 비추천**이다.

예를 들어 `Lite: small 1536 / Thinking: large 1536`으로 분리하면 아래 문제가 생긴다.

```
DB 테이블/컬렉션 2개 필요
저장공간 증가
재임베딩 로직 필요
검색 결과 차이 디버깅 어려움
구현 복잡도 증가
```

**권장 방향:**

```
임베딩은 large dimensions=1536으로 통일
Lite/Thinking은 검색량과 생성 모델로 분리
```

---

### 6-8. 최종 판단 요약

```
text-embedding-3-large + dimensions=1536 사용:
  검색 속도 리스크는 크지 않음

주의할 병목:
  검색보다 embedding 생성 시간, LLM 생성 시간, chunk 수

64비트 PC:
  필수 조건에 가깝지만 속도 보장의 핵심은 아님
  진짜 핵심: RAM, SSD, 인덱스 설정, chunk 수

MacBook Pro 64GB:
  개발/테스트/데모 서버로 충분히 활용 가능
  다만 OpenAI API 임베딩 자체를 빠르게 만드는 건 아님

추천:
  large 1536으로 통일하고,
  성능 로그를 찍어서 실제 병목을 보고 최적화
```

> **한마디 정리**: `large + dimensions=1536` 때문에 검색이 느려질까 봐 걱정하기보다는, **chunk 수 관리·배치 임베딩·캐싱·벡터 인덱스·LLM 생성 시간을 관리하는 게 훨씬 중요하다.**

---

> **참고 문서**
> - [OpenAI Embeddings 공식 문서](https://platform.openai.com/docs/guides/embeddings)
> - [text-embedding-3 모델 발표 (OpenAI)](https://openai.com/blog/new-embedding-models-and-api-updates)
> - [MIRACL 다국어 검색 벤치마크](https://github.com/project-miracl/miracl)
> - [pgvector 인덱싱 가이드](https://github.com/pgvector/pgvector#indexing)
> - 관련 내부 문서: [`docs/04_Decisions/MODEL_SELECTION_EVIDENCE.md`](MODEL_SELECTION_EVIDENCE.md)
> - 관련 기능 명세: [`docs/03_Specifications/02_RAG/spec/RAG_EMBED_SPEC.md`](../03_Specifications/02_RAG/spec/RAG_EMBED_SPEC.md)

