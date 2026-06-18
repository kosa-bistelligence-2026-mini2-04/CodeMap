# CodeMap 프로젝트: OpenAI 모델 선택 및 아키텍처 매칭 근거

> [!NOTE]
> 본 문서는 CodeMap 프로젝트(Agentic RAG 기반 소스코드 분석 시스템)의 핵심 엔진 구성을 위해 제안된 OpenAI 모델 조합(GPT-4o, text-embedding-3-large, GPT-4o-mini)의 타당성을 OpenAI 공식 문서 및 벤치마크 지표를 바탕으로 검증한 기술 검토 문서입니다.

---

## 1. 메인 에이전트 모델: `gpt-4o` (Agentic Search 및 판단 로직)

CodeMap의 지능(Brain) 역할을 수행하며, 직접 파일 시스템 도구를 호출하고 코드를 탐색하는 메인 에이전트로 `gpt-4o`를 채택해야 하는 객관적인 이유입니다.

### 📌 공식적인 도구 호출(Function Calling) 최적화 및 병렬 처리

**객관적 근거**

OpenAI는 공식 릴리즈를 통해 GPT-4o가 외부 시스템 API와 상호작용하는 도구 호출(Function Calling)에 있어 기존 모델 대비 비약적으로 향상된 성능을 지니고 있음을 명시했습니다. 특히, 여러 개의 도구를 한 번의 응답으로 실행하는 **병렬 도구 호출(Parallel Tool Calling)**을 완벽히 지원합니다.

**프로젝트 매칭**

CodeMap은 제한 시간(20초) 및 제한 횟수(5회) 내에 `grep`, `tree` 등의 탐색 도구를 능동적으로 사용해야 합니다. GPT-4o의 검증된 병렬 도구 호출 능력은 Agentic RAG의 탐색 루프를 가장 빠르고 정확하게 완수할 수 있는 핵심 기술 기반이 됩니다.

**공식 참조 문서**

[Hello GPT-4o (OpenAI 공식 블로그)](https://openai.com/index/hello-gpt-4o/)

### 📌 다단계 추론(Multi-step Reasoning) 우위

**객관적 근거**

업계의 다양한 에이전트 벤치마크(예: Hugging Face Agent Leaderboard)에서 GPT-4o는 복잡한 맥락을 이해하고 다단계 계획을 수립하는 영역에서 최상위권의 추론 점수를 기록하고 있습니다.

**프로젝트 매칭**

얽혀있는 스파게티 코드의 의존성 구조를 해석하고, 첫 번째 탐색 실패 시 논리적으로 다음 탐색 경로를 유추하는 "자가 교정(Self-Correction)" 과정을 수행하려면 가장 지능이 높은 모델이 필수적입니다.

---

## 2. 코드 임베딩 모델: `text-embedding-3-large` (RAG 및 pgvector 구축)

방대한 코드와 문서를 수학적 벡터 공간으로 변환하여 정밀 검색을 가능하게 하는 임베딩 모델로 `text-embedding-3-large`를 채택해야 하는 이유입니다.

### 📌 MTEB 및 MIRACL 벤치마크 점수 압도적 1위

**객관적 근거**

2024년 1월에 발표된 공식 성능 평가에 따르면, 기존 세대인 `text-embedding-ada-002` 대비 검색 정확도가 획기적으로 상승했습니다.

- **MTEB (영어 텍스트 평가)**: `64.6%` (기존 61.0% 대비 상승)
- **MIRACL (다국어 정보 검색 평가)**: `54.9%` (기존 31.4% 대비 비약적 상승)

**프로젝트 매칭**

한국어로 작성된 주석 및 명세서(`README.md`)와 영문 소스코드가 혼재된 GitHub 환경에서 분석을 수행해야 합니다. 다국어 검색(MIRACL)에서 압도적인 점수를 획득한 이 모델은, 최대 3072차원의 세밀한 벡터를 통해 변수명 중복을 넘어선 "코드의 미묘한 의미적 차이"까지 정확히 찾아냅니다.

**공식 참조 문서**

[New embedding models and API updates (OpenAI 공식 블로그)](https://openai.com/index/new-embedding-models-and-api-updates/)

### 📌 마트료시카 표현 학습(Matryoshka Representation Learning) 공식 지원

**객관적 근거**

해당 모델은 `dimensions` API 파라미터를 사용하여 모델의 차원을 줄이더라도(예: 3072차원 -> 1024차원) 임베딩의 핵심 정보력과 성능을 거의 그대로 유지하는 기능을 공식적으로 지원합니다.

**프로젝트 매칭**

PostgreSQL의 pgvector를 활용하는 CodeMap 환경에서, 향후 DB 저장 공간 절약이나 벡터 인덱스 쿼리 속도 최적화가 필요해질 경우, 검색 품질을 희생하지 않으면서도 시스템 부하를 줄일 수 있는 강력한 아키텍처적 유연성을 제공합니다.

---

## 3. 하이브리드 병행 모델: `gpt-4o-mini` (Map-Reduce 요약 파이프라인)

초기 데이터 구축 파이프라인에서 막대한 텍스트 처리를 담당하는 모델로 `gpt-4o-mini`를 병행 사용하는 '하이브리드 전략'을 채택해야 하는 이유입니다.

### 📌 압도적인 비용 효율성 (Cost Efficiency)

**객관적 근거**

GPT-4o-mini의 가격 정책은 입력 토큰 100만 개당 `$0.15`로, 이전 세대인 GPT-3.5 Turbo 대비 **60% 이상 저렴**하며, 메인 모델인 GPT-4o와 비교하면 입력 기준 **약 33배 저렴**한 공식 단가를 가집니다.

**프로젝트 매칭**

CodeMap의 4대 핵심 기능 중 "자동화된 문서화(Map-Reduce)" 단계는 전체 코드 파일을 수십 번 반복해서 읽고 병합해야 하므로 막대한 입력 토큰을 소모합니다. 시스템 유지 보수 및 운영 비용 절감을 위해 전처리 과정에 이 모델을 배치하는 것은 필수적인 전략입니다.

**공식 참조 문서**

[OpenAI API Pricing (공식 단가표)](https://openai.com/api/pricing/)

### 📌 소형 모델 중 최고 수준의 추론 능력 (MMLU)

**객관적 근거**

단순 언어 능력을 평가하는 MMLU 벤치마크에서 **`82.0%`**를 기록하여, 동급 경쟁 모델인 Gemini Flash(77.9%) 및 Claude Haiku(73.8%)를 공식적으로 앞서고 있습니다.

**프로젝트 매칭**

저렴하다고 해서 문해력이 떨어진다면 코드 요약의 품질을 보장할 수 없습니다. 하지만 GPT-4o-mini는 비용 대비 뛰어난 인지 능력을 공식 지표로 증명하였으므로, 백그라운드에서 하위 폴더와 파일들의 역할을 요약하고 관계망을 도출하는 작업에 충분하고도 넘치는 성능을 발휘합니다.

**공식 참조 문서**

[GPT-4o mini: advancing cost-efficient intelligence (OpenAI 공식 블로그)](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)
