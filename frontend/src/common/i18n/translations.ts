// ─────────────────────────────────────────────────────────────────────────────
// Translation strings — EN / KO
// ─────────────────────────────────────────────────────────────────────────────

export type Locale = "en" | "ko";

export const translations = {
  en: {
    // ── Navbar ────────────────────────────────────────────────────────────────
    nav: {
      home: "Home",
      analyze: "Analyze",
      chat: "Chat",
      launchApp: "Launch App",
      github: "GitHub",
    },

    // ── Home hero ─────────────────────────────────────────────────────────────
    hero: {
      badge: "CodeMap AI",
      title: "Codebase Intelligence,\nPowered by Multi-Agent AI",
      subtitle:
        "Enter a GitHub repository URL or local path. CodeMap AI maps architecture, infers behavior, audits security, and generates interactive onboarding guides.",
      placeholder: "https://github.com/owner/repo  or  /local/absolute/path",
      tryLabel: "Try:",
      statsLanguages: "Languages",
      statsAgents: "Agent Types",
      statsDepth: "Analysis Depth",
      statsDepthValue: "Full Repo",
      statsPrivacy: "Privacy",
      statsPrivacyValue: "Local-First",
      scroll: "Scroll",
    },

    // ── Home sections ─────────────────────────────────────────────────────────
    howItWorks: {
      title: "How CodeMap AI Works",
      subtitle: "A four-agent pipeline that transforms any codebase into structured knowledge.",
      steps: [
        {
          title: "Submit a Repo",
          desc: "Paste a GitHub URL or local absolute path. CodeMap fetches or reads the codebase.",
        },
        {
          title: "Static Analysis",
          desc: "The static analyzer maps file structure, imports, and dependency chains.",
        },
        {
          title: "Deep Inference",
          desc: "Behavior and community agents infer runtime patterns, tech stack, and code quality.",
        },
        {
          title: "Onboarding Report",
          desc: "The reporter synthesizes findings into an interactive HTML guide and JSON output.",
        },
      ],
    },

    // ── Use Cases ─────────────────────────────────────────────────────────────
    useCases: {
      title: "Use Cases That Drive Decisions",
      subtitle: "CodeMap AI helps teams reduce uncertainty before adoption, onboarding, and audit decisions.",
      cases: [
        {
          title: "Repository Due Diligence",
          desc: "Evaluate unfamiliar repositories before adopting dependencies or onboarding teams. Get system-level snapshots for immediate clarity.",
          link: "Start Analysis",
        },
        {
          title: "Team Onboarding",
          desc: "Generate interactive onboarding guides for new developers joining a project. Reduce ramp-up time from weeks to hours.",
          link: "Generate Guide",
        },
        {
          title: "Security Prioritization",
          desc: "Surface actionable risk signals and triage findings with engineering context. Get severity-framed remediation direction.",
          link: "Security Audit",
        },
      ],
    },

    // ── FAQ ───────────────────────────────────────────────────────────────────
    faq: {
      title: "Frequently Asked Questions",
      items: [
        {
          question: "What types of repositories can CodeMap AI analyze?",
          answer:
            "CodeMap AI supports any Git repository — local paths on your machine (e.g. /Users/you/projects/myrepo) or public GitHub URLs. Python, TypeScript, JavaScript, Go, and Rust codebases are especially well-supported.",
        },
        {
          question: "How does the multi-agent pipeline work?",
          answer:
            "CodeMap AI runs 4 specialized agents in parallel: a Static Analyzer that maps file structure and imports, a Behavior Inferer that understands runtime patterns, a Community Assessor that evaluates code quality signals, and a Reporter that synthesizes everything into an interactive onboarding guide.",
        },
        {
          question: "Is my code sent to the cloud?",
          answer:
            "Local paths are processed entirely on your machine using the local FastAPI server. Only public GitHub URLs require fetching the repository. Your code is never stored or used for training.",
        },
        {
          question: "How long does an analysis take?",
          answer:
            "Most analyses complete in 30–120 seconds depending on repository size. The WebSocket progress panel shows real-time agent status so you can track progress live.",
        },
      ],
    },

    // ── CTA ───────────────────────────────────────────────────────────────────
    cta: {
      title: "Ready to map your codebase?",
      subtitle:
        "Start with any GitHub repository URL or a local absolute path. Get your first analysis in under 2 minutes.",
      primary: "Start Analysis",
      secondary: "View on GitHub",
    },

    // ── BentoFeatures ─────────────────────────────────────────────────────────
    bento: {
      title: "Everything you need to understand code",
      subtitle:
        "CodeMap AI gives you superpowers to digest entire repositories in seconds with multi-agent intelligence.",
      features: [
        {
          title: "Deep Code Analysis",
          desc: "Our multi-agent system ingests your entire codebase to give you expert-level understanding of any repository structure — completely eliminating the clone-and-browse phase.",
        },
        {
          title: "Architecture Mapping",
          desc: "Generate interactive dependency graphs and module maps automatically.",
          mockLabel: "Output:",
          mockValue: "dependency-graph.svg",
        },
        {
          title: "Git Archaeology",
          desc: "Trace code evolution through commit history and branch patterns.",
        },
        {
          title: "Security Audit",
          desc: "Detect exposed secrets and code vulnerabilities silently.",
        },
        {
          title: "Semantic Search",
          desc: "Ask natural language questions about any codebase. Find patterns, bugs, and missing pieces instantly.",
        },
        {
          title: "Onboarding Reports",
          desc: "Generate interactive HTML onboarding guides for any repository, instantly shareable with your team.",
        },
      ],
    },

    // ── InteractiveDemo ───────────────────────────────────────────────────────
    demo: {
      title: "See it in Action",
      subtitle: "Whether analyzing, mapping, or auditing — CodeMap AI handles it all.",
      scenarios: [
        {
          title: "Analyzing fastapi/fastapi",
          query: "Explain the dependency injection system and how routes register.",
          loadingText: "Reading repository index...",
          analyzingText: "Tracing injection patterns...",
          chatPart1: "In",
          chatPart1Bold: "FastAPI",
          chatPart1End: ", dependency injection is handled via the",
          chatPart1Code: "Depends()",
          chatPart1Tail: "mechanism.",
          chatPart2: "Each route declares its dependencies in the function signature. FastAPI resolves the dependency graph on request.",
          badgeTitle: "Key Pattern Found",
        },
        {
          title: "Architecture Map for numpy/numpy",
          query: "Generate a module dependency graph for the core numeric engine.",
          loadingText: "Parsing import graph...",
          analyzingText: "Generating architecture diagram...",
          archText: "NumPy's architecture separates the C extension layer from the Python interface layer.",
          archEntry: "numpy/__init__.py (Entry)",
          archCore: "numpy/core (C Extensions)",
          archModules: "numpy/linalg, fft, random",
        },
        {
          title: "Security Scan for requests/requests",
          query: "Are there any hardcoded credentials or unsafe deserialization patterns?",
          loadingText: "Scanning for secret patterns...",
          analyzingText: "Cross-referencing CVE database...",
          secText: "I analyzed the codebase for credentials, secrets, and unsafe patterns.",
          secBadge: "No Critical Issues Found",
          secDesc: "The requests library follows secure practices — no hardcoded credentials or unsafe deserialization patterns detected.",
        }
      ]
    },

    // ── SecurityBanner ────────────────────────────────────────────────────────
    security: {
      title: "Local-First. Privacy Guaranteed.",
      desc: "CodeMap AI runs entirely on your infrastructure. Your codebase never leaves your machine. Local paths are analyzed locally — no data is sent to external servers unless you explicitly choose a GitHub URL.",
      badge: "Multi-Agent Pipeline",
    },

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: {
      tagline: "Codebase Intelligence",
      desc: "Multi-agent AI system for deep codebase analysis, architecture mapping, and interactive onboarding guides. Understand any repository in seconds.",
      featuresTitle: "Features",
      resourcesTitle: "Resources",
      features: ["Repo Analysis", "Architecture Map", "Security Audit", "Onboarding Report"],
      resources: ["Getting Started", "API Docs", "GitHub"],
      ctaTitle: "Ready to analyze?",
      ctaDesc: "Enter any GitHub URL or local path to start.",
      ctaButton: "Start Analysis →",
      statusOk: "Backend operational",
      copyright: "CODEMAP AI. BUILT FOR DEVELOPERS.",
      localFirst: "LOCAL-FIRST PROCESSING",
      multiAgent: "MULTI-AGENT PIPELINE",
      poweredBy: "Powered by FastAPI + Next.js",
    },

    // ── Analyze page ──────────────────────────────────────────────────────────
    analyzePage: {
      pageTitle: "Analysis Dashboard",
      emptyTitle: "No Report Loaded",
      emptyDesc:
        'Enter a local Git path or GitHub URL in the sidebar and click "Start Analysis" to run the multi-agent pipeline.',
      emptyHint: 'Or select a past run from the "Analysis Records" list below.',
      loadingMsg: "Agents are mapping the codebase. Please wait...",
    },

    // ── RepoInput ─────────────────────────────────────────────────────────────
    repoInput: {
      title: "Analyze Repository",
      subtitle: "Supports local Git paths or public GitHub URLs.",
      tabGithub: "GitHub URL",
      tabLocal: "Local Path",
      labelGithub: "Repository URL",
      labelLocal: "Absolute Path",
      placeholderGithub: "https://github.com/owner/repo",
      placeholderLocal: "/path/to/local/repo",
      modelLabel: "Inference Model",
      cacheLabel: "Skip cached response",
      cacheHint: "Force re-analyze from scratch",
      submit: "Start Analysis →",
      submitting: "Analyzing...",
      errorGithubEmpty: "GitHub URL cannot be empty.",
      errorLocalEmpty: "Local path cannot be empty.",
      errorGithubInvalid: "Please enter a valid GitHub repository URL (e.g. https://github.com/owner/repo)",
      errorLocalInvalid: "Please enter a valid local absolute path.",
    },

    // ── HistoryList ───────────────────────────────────────────────────────────
    historyList: {
      title: "Analysis Records",
      refresh: "Refresh",
      loading: "Loading...",
      empty: "No analysis records yet.",
      emptyHint: "Your past runs will appear here.",
      loadFailed: "Load failed:",
      statusRunning: "Running",
      statusDone: "Done",
      statusFailed: "Failed",
    },

    // ── ProgressPanel ─────────────────────────────────────────────────────────
    progressPanel: {
      title: "Analysis Progress",
      wsLive: "● Live",
      wsReconnecting: "Reconnecting",
      wsDisconnected: "Disconnected",
      agents: {
        static_analyzer: "Static Analysis",
        behavior_inferer: "Behavior Inference",
        community_assessor: "Community Assessment",
        reporter: "Report Generation",
      },
      statusPending: "Pending",
      statusRunning: "Running",
      statusDone: "Done",
      statusFailed: "Failed",
      statusDegraded: "Degraded",
      retry: "Retry",
    },

    // ── ReportViewer ──────────────────────────────────────────────────────────
    reportViewer: {
      execSummary: "Executive Summary",
      aiGenerated: "AI Generated",
      healthScore: "Health Score",
      strengths: "Strengths",
      risks: "Risks",
      confidence: "Model Confidence",
      analysisReport: "Analysis Report",
      completedAt: "Completed At",
      totalTime: "Total Time",
      communityHealth: "Community Health",
      commitsPerWeek: "Commits / Week",
      contributors: "Contributors",
      avgIssueResponse: "Avg Issue Response",
      degraded: "Degraded",
      llmInterpretation: "LLM Interpretation",
      noRecentCommits: "No recent commits found or history is empty. Metric has low statistical significance.",
      recommendations: "Improvement Recommendations",
      conflictResolution: "Multi-Agent Conflict Resolution",
      llmJudge: "LLM Judge",
      conflictsResolved: "Conflict(s) Resolved",
      conflictDesc: "When StaticAnalyzer and BehaviorInferer disagree on a module, the LLM Judge balances risk vs. value to resolve it.",
      staticView: "Static View (StaticAnalyzer)",
      behaviorView: "Behavioral View (BehaviorInferer)",
      judgeDecision: "Judge Decision",
      escalated: "Escalated",
      guardrail: "Hallucination Guardrail Telemetry",
      guardrailBadge: "Guardrail",
      guardrailDesc: "Dual-layer filtering (Regex + Semantic Similarity) blocks hallucinations in LLM output.",
      regexBlocked: "Regex Blocked",
      semanticFiltered: "Semantic Filtered",
      regenerations: "Regenerations",
      fallbackStatus: "Fallback Status",
      fallbackTriggered: "Triggered",
      fallbackInactive: "Inactive",
      fullReport: "Full Detailed Report",
    },

    // ── Chat ──────────────────────────────────────────────────────────────────
    chat: {
      title: "AI Code Chat",
      subtitle: "Ask questions about the analyzed repository",
      placeholder: "Ask anything about this codebase...",
      send: "Send",
      clear: "Clear conversation",
      copy: "Copy",
      copied: "Copied!",
      disclaimer: "AI can make mistakes. Verify important information.",
      mode: {
        lite: "Lite",
        deep: "Deep",
        liteDesc: "Fast responses using gpt-4o-mini — great for simple questions",
        deepDesc: "Deep analysis using gpt-4o — best for complex architecture questions",
      },
      status: {
        searching: "Searching relevant files...",
        buildingContext: "Building code context...",
        generating: "Generating answer...",
      },
      suggestions: [
        "Explain the overall architecture of this project",
        "What are the key files and recommended reading order?",
        "How do I run this project locally?",
        "Where is the entry point of this application?",
        "Are there any risky or complex files to watch out for?",
        "Analyze the tech stack used in this project",
      ],
      empty: {
        title: "Start a conversation",
        subtitle: "Choose a suggestion below or type your own question",
      },
    },
  },

  ko: {
    // ── Navbar ────────────────────────────────────────────────────────────────
    nav: {
      home: "홈",
      analyze: "분석",
      chat: "채팅",
      launchApp: "앱 실행",
      github: "GitHub",
    },

    // ── Home hero ─────────────────────────────────────────────────────────────
    hero: {
      badge: "CodeMap AI",
      title: "코드베이스 인텔리전스,\n멀티 에이전트 AI로",
      subtitle:
        "GitHub 저장소 URL 또는 로컬 경로를 입력하세요. CodeMap AI가 아키텍처를 매핑하고, 동작을 추론하며, 보안을 감사하고, 인터랙티브 온보딩 가이드를 생성합니다.",
      placeholder: "https://github.com/owner/repo  또는  /로컬/절대/경로",
      tryLabel: "예시:",
      statsLanguages: "언어",
      statsAgents: "에이전트 수",
      statsDepth: "분석 깊이",
      statsDepthValue: "전체 저장소",
      statsPrivacy: "프라이버시",
      statsPrivacyValue: "로컬 우선",
      scroll: "스크롤",
    },

    // ── Home sections ─────────────────────────────────────────────────────────
    howItWorks: {
      title: "CodeMap AI 작동 방식",
      subtitle: "모든 코드베이스를 구조적 지식으로 변환하는 4단계 에이전트 파이프라인.",
      steps: [
        {
          title: "저장소 제출",
          desc: "GitHub URL 또는 로컬 절대 경로를 붙여넣으세요. CodeMap이 코드베이스를 가져오거나 읽습니다.",
        },
        {
          title: "정적 분석",
          desc: "정적 분석기가 파일 구조, 임포트, 의존성 체인을 매핑합니다.",
        },
        {
          title: "심층 추론",
          desc: "동작 및 커뮤니티 에이전트가 런타임 패턴, 기술 스택, 코드 품질을 추론합니다.",
        },
        {
          title: "온보딩 리포트",
          desc: "리포터가 분석 결과를 인터랙티브 HTML 가이드와 JSON 출력물로 합성합니다.",
        },
      ],
    },

    // ── Use Cases ─────────────────────────────────────────────────────────────
    useCases: {
      title: "의사결정을 이끄는 활용 사례",
      subtitle: "CodeMap AI는 도입, 온보딩, 감사 결정 전의 불확실성을 줄이는 데 도움을 줍니다.",
      cases: [
        {
          title: "저장소 실사",
          desc: "의존성 도입이나 팀 온보딩 전에 낯선 저장소를 평가하세요. 즉각적인 명확성을 위한 시스템 수준 스냅샷을 얻으세요.",
          link: "분석 시작",
        },
        {
          title: "팀 온보딩",
          desc: "프로젝트에 합류하는 신규 개발자를 위한 인터랙티브 온보딩 가이드를 생성하세요. 적응 시간을 주에서 시간 단위로 줄이세요.",
          link: "가이드 생성",
        },
        {
          title: "보안 우선순위 지정",
          desc: "실행 가능한 위험 신호를 발견하고 엔지니어링 맥락으로 분류하세요. 심각도 기반의 해결 방향을 얻으세요.",
          link: "보안 감사",
        },
      ],
    },

    // ── FAQ ───────────────────────────────────────────────────────────────────
    faq: {
      title: "자주 묻는 질문",
      items: [
        {
          question: "CodeMap AI가 분석할 수 있는 저장소 유형은?",
          answer:
            "CodeMap AI는 모든 Git 저장소를 지원합니다 — 로컬 경로(예: /Users/you/projects/myrepo)나 공개 GitHub URL 모두 가능합니다. Python, TypeScript, JavaScript, Go, Rust 코드베이스가 특히 잘 지원됩니다.",
        },
        {
          question: "멀티 에이전트 파이프라인은 어떻게 작동하나요?",
          answer:
            "CodeMap AI는 4개의 전문 에이전트를 병렬로 실행합니다: 파일 구조와 임포트를 매핑하는 정적 분석기, 런타임 패턴을 이해하는 동작 추론기, 코드 품질 신호를 평가하는 커뮤니티 평가자, 모든 것을 인터랙티브 온보딩 가이드로 합성하는 리포터.",
        },
        {
          question: "코드가 클라우드로 전송되나요?",
          answer:
            "로컬 경로는 로컬 FastAPI 서버를 사용하여 전적으로 사용자 컴퓨터에서 처리됩니다. 공개 GitHub URL의 경우에만 저장소를 가져와야 합니다. 코드는 절대 저장되거나 학습에 사용되지 않습니다.",
        },
        {
          question: "분석에 얼마나 걸리나요?",
          answer:
            "저장소 크기에 따라 대부분의 분석은 30~120초 내에 완료됩니다. WebSocket 진행 패널이 에이전트 상태를 실시간으로 표시하므로 진행 상황을 실시간으로 추적할 수 있습니다.",
        },
      ],
    },

    // ── CTA ───────────────────────────────────────────────────────────────────
    cta: {
      title: "코드베이스를 매핑할 준비가 되셨나요?",
      subtitle:
        "GitHub 저장소 URL이나 로컬 절대 경로로 시작하세요. 2분 이내에 첫 번째 분석 결과를 받아보세요.",
      primary: "분석 시작",
      secondary: "GitHub에서 보기",
    },

    // ── BentoFeatures ─────────────────────────────────────────────────────────
    bento: {
      title: "코드를 이해하는 데 필요한 모든 것",
      subtitle:
        "CodeMap AI는 멀티 에이전트 인텔리전스로 전체 저장소를 수 초 만에 이해하는 초능력을 제공합니다.",
      features: [
        {
          title: "심층 코드 분석",
          desc: "멀티 에이전트 시스템이 전체 코드베이스를 분석하여 모든 저장소 구조에 대한 전문가 수준의 이해를 제공합니다 — 클론-브라우즈 단계를 완전히 제거합니다.",
        },
        {
          title: "아키텍처 매핑",
          desc: "인터랙티브 의존성 그래프와 모듈 맵을 자동으로 생성합니다.",
          mockLabel: "출력:",
          mockValue: "dependency-graph.svg",
        },
        {
          title: "Git 고고학",
          desc: "커밋 히스토리와 브랜치 패턴을 통해 코드 진화를 추적합니다.",
        },
        {
          title: "보안 감사",
          desc: "노출된 비밀과 코드 취약점을 자동으로 감지합니다.",
        },
        {
          title: "시맨틱 검색",
          desc: "코드베이스에 대해 자연어 질문을 하세요. 패턴, 버그, 누락된 부분을 즉시 찾을 수 있습니다.",
        },
        {
          title: "온보딩 리포트",
          desc: "모든 저장소에 대한 인터랙티브 HTML 온보딩 가이드를 생성하고 팀과 즉시 공유하세요.",
        },
      ],
    },

    // ── InteractiveDemo ───────────────────────────────────────────────────────
    demo: {
      title: "실제 동작 확인",
      subtitle: "분석, 매핑, 감사 등 — CodeMap AI가 모두 처리합니다.",
      scenarios: [
        {
          title: "fastapi/fastapi 분석 중",
          query: "의존성 주입 시스템과 라우트 등록 방식을 설명해줘.",
          loadingText: "저장소 인덱스 읽는 중...",
          analyzingText: "주입 패턴 추적 중...",
          chatPart1: "",
          chatPart1Bold: "FastAPI",
          chatPart1End: "에서 의존성 주입은",
          chatPart1Code: "Depends()",
          chatPart1Tail: "메커니즘을 통해 처리됩니다.",
          chatPart2: "각 라우트는 함수 시그니처에 의존성을 선언합니다. FastAPI는 요청 시 의존성 그래프를 해결합니다.",
          badgeTitle: "핵심 패턴 발견",
        },
        {
          title: "numpy/numpy 아키텍처 맵",
          query: "핵심 숫자 엔진의 모듈 의존성 그래프를 생성해.",
          loadingText: "임포트 그래프 파싱 중...",
          analyzingText: "아키텍처 다이어그램 생성 중...",
          archText: "NumPy의 아키텍처는 C 확장 계층과 Python 인터페이스 계층을 분리합니다.",
          archEntry: "numpy/__init__.py (진입점)",
          archCore: "numpy/core (C 확장)",
          archModules: "numpy/linalg, fft, random",
        },
        {
          title: "requests/requests 보안 스캔",
          query: "하드코딩된 자격 증명이나 안전하지 않은 역직렬화 패턴이 있어?",
          loadingText: "비밀 패턴 스캔 중...",
          analyzingText: "CVE 데이터베이스 교차 참조 중...",
          secText: "자격 증명, 비밀 및 안전하지 않은 패턴에 대해 코드베이스를 분석했습니다.",
          secBadge: "치명적인 문제 없음",
          secDesc: "requests 라이브러리는 안전한 관행을 따릅니다 — 하드코딩된 자격 증명이나 안전하지 않은 역직렬화 패턴이 감지되지 않았습니다.",
        }
      ]
    },

    // ── SecurityBanner ────────────────────────────────────────────────────────
    security: {
      title: "로컬 우선. 프라이버시 보장.",
      desc: "CodeMap AI는 전적으로 사용자 인프라에서 실행됩니다. 코드베이스는 절대 외부로 전송되지 않습니다. 로컬 경로는 로컬에서 분석됩니다 — GitHub URL을 명시적으로 선택하지 않는 한 데이터는 외부 서버로 전송되지 않습니다.",
      badge: "멀티 에이전트 파이프라인",
    },

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: {
      tagline: "코드베이스 인텔리전스",
      desc: "심층 코드베이스 분석, 아키텍처 매핑, 인터랙티브 온보딩 가이드를 위한 멀티 에이전트 AI 시스템. 모든 저장소를 수 초 만에 이해하세요.",
      featuresTitle: "기능",
      resourcesTitle: "리소스",
      features: ["저장소 분석", "아키텍처 맵", "보안 감사", "온보딩 리포트"],
      resources: ["시작하기", "API 문서", "GitHub"],
      ctaTitle: "분석할 준비가 됐나요?",
      ctaDesc: "GitHub URL 또는 로컬 경로를 입력하여 시작하세요.",
      ctaButton: "분석 시작 →",
      statusOk: "백엔드 정상 작동",
      copyright: "CODEMAP AI. 개발자를 위해 만들었습니다.",
      localFirst: "로컬 우선 처리",
      multiAgent: "멀티 에이전트 파이프라인",
      poweredBy: "FastAPI + Next.js 기반",
    },

    // ── Analyze page ──────────────────────────────────────────────────────────
    analyzePage: {
      pageTitle: "분석 대시보드",
      emptyTitle: "로드된 리포트 없음",
      emptyDesc: '사이드바에 로컬 Git 경로 또는 GitHub URL을 입력하고 "분석 시작"을 클릭하여 멀티 에이전트 파이프라인을 실행하세요.',
      emptyHint: '또는 아래 "분석 기록" 목록에서 이전 실행을 선택하세요.',
      loadingMsg: "에이전트가 코드베이스를 매핑하고 있습니다. 잠시 기다려주세요...",
    },

    // ── RepoInput ─────────────────────────────────────────────────────────────
    repoInput: {
      title: "저장소 분석",
      subtitle: "로컬 Git 경로 또는 공개 GitHub URL을 지원합니다.",
      tabGithub: "GitHub URL",
      tabLocal: "로컬 경로",
      labelGithub: "저장소 URL",
      labelLocal: "절대 경로",
      placeholderGithub: "https://github.com/owner/repo",
      placeholderLocal: "/경로/로컬/저장소",
      modelLabel: "추론 모델",
      cacheLabel: "캐시 건너뛰기",
      cacheHint: "처음부터 다시 분석",
      submit: "분석 시작 →",
      submitting: "분석 중...",
      errorGithubEmpty: "GitHub URL을 입력해주세요.",
      errorLocalEmpty: "로컬 경로를 입력해주세요.",
      errorGithubInvalid: "유효한 GitHub 저장소 URL을 입력해주세요 (예: https://github.com/owner/repo)",
      errorLocalInvalid: "유효한 로컬 절대 경로를 입력해주세요.",
    },

    // ── HistoryList ───────────────────────────────────────────────────────────
    historyList: {
      title: "분석 기록",
      refresh: "새로고침",
      loading: "로딩 중...",
      empty: "아직 분석 기록이 없습니다.",
      emptyHint: "이전 실행 내역이 여기에 표시됩니다.",
      loadFailed: "로드 실패:",
      statusRunning: "실행 중",
      statusDone: "완료",
      statusFailed: "실패",
    },

    // ── ProgressPanel ─────────────────────────────────────────────────────────
    progressPanel: {
      title: "분석 진행 상황",
      wsLive: "● 실시간",
      wsReconnecting: "재연결 중",
      wsDisconnected: "연결 끊김",
      agents: {
        static_analyzer: "정적 분석",
        behavior_inferer: "동작 추론",
        community_assessor: "커뮤니티 평가",
        reporter: "리포트 생성",
      },
      statusPending: "대기",
      statusRunning: "실행 중",
      statusDone: "완료",
      statusFailed: "실패",
      statusDegraded: "저하됨",
      retry: "재시도",
    },

    // ── ReportViewer ──────────────────────────────────────────────────────────
    reportViewer: {
      execSummary: "실행 요약",
      aiGenerated: "AI 생성",
      healthScore: "건강 점수",
      strengths: "강점",
      risks: "위험",
      confidence: "모델 신뢰도",
      analysisReport: "분석 리포트",
      completedAt: "완료 시각",
      totalTime: "총 소요 시간",
      communityHealth: "커뮤니티 건강",
      commitsPerWeek: "주간 커밋",
      contributors: "기여자",
      avgIssueResponse: "평균 이슈 응답",
      degraded: "저하됨",
      llmInterpretation: "LLM 해석",
      noRecentCommits: "최근 커밋이 없거나 히스토리가 비어 있습니다. 지표의 통계적 유의성이 낮습니다.",
      recommendations: "개선 권고사항",
      conflictResolution: "멀티 에이전트 충돌 해결",
      llmJudge: "LLM 심판",
      conflictsResolved: "개 충돌 해결됨",
      conflictDesc: "StaticAnalyzer와 BehaviorInferer가 모듈에 대해 의견이 다를 경우, LLM 심판이 위험과 가치의 균형을 맞춰 해결합니다.",
      staticView: "정적 관점 (StaticAnalyzer)",
      behaviorView: "동작 관점 (BehaviorInferer)",
      judgeDecision: "심판 결정",
      escalated: "에스컬레이션됨",
      guardrail: "환각 가드레일 텔레메트리",
      guardrailBadge: "가드레일",
      guardrailDesc: "이중 레이어 필터링(정규식 + 시맨틱 유사도)이 LLM 출력의 환각을 차단합니다.",
      regexBlocked: "정규식 차단",
      semanticFiltered: "시맨틱 필터링",
      regenerations: "재생성 횟수",
      fallbackStatus: "폴백 상태",
      fallbackTriggered: "작동됨",
      fallbackInactive: "비활성",
      fullReport: "전체 상세 리포트",
    },

    // ── Chat ──────────────────────────────────────────────────────────────────
    chat: {
      title: "AI 코드 채팅",
      subtitle: "분석된 저장소에 대해 질문하세요",
      placeholder: "이 코드베이스에 대해 무엇이든 물어보세요...",
      send: "전송",
      clear: "대화 초기화",
      copy: "복사",
      copied: "복사됨!",
      disclaimer: "AI는 실수할 수 있습니다. 중요한 정보는 직접 확인하세요.",
      mode: {
        lite: "Lite",
        deep: "Deep",
        liteDesc: "gpt-4o-mini로 빠른 응답 — 간단한 질문에 적합",
        deepDesc: "gpt-4o로 심층 분석 — 복잡한 아키텍처 질문에 최적",
      },
      status: {
        searching: "관련 파일 검색 중...",
        buildingContext: "코드 컨텍스트 구성 중...",
        generating: "답변 생성 중...",
      },
      suggestions: [
        "이 프로젝트의 전체 아키텍처를 설명해줘",
        "핵심 파일과 추천 읽기 순서를 알려줘",
        "이 프로젝트를 로컬에서 실행하는 방법은?",
        "이 애플리케이션의 진입점(entry point)은 어디야?",
        "주의해야 할 위험하거나 복잡한 파일이 있어?",
        "이 프로젝트에서 사용된 기술 스택을 분석해줘",
      ],
      empty: {
        title: "대화를 시작하세요",
        subtitle: "아래 추천 질문을 선택하거나 직접 질문을 입력하세요",
      },
    },
  },
} as const;

export type TranslationKeys = typeof translations.en;
