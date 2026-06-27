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
      signIn: "Sign In",
      signUp: "Sign Up",
      signOut: "Sign Out",
    },

    // ── Home hero ─────────────────────────────────────────────────────────────
    hero: {
      badge: "CodeMap AI",
      title: "Understand Any Codebase,\nWithout Reading It All",
      subtitle:
        "Find the structure, key flows, and important context of an unfamiliar repository. Multiple analysis agents turn scattered code into a clear, connected view.",
      sourceLabel: "Repository source",
      sourceGithub: "GitHub repository",
      sourceLocal: "Local folder",
      placeholder: "Search by repository name or paste a GitHub URL",
      submit: "Analyze repository",
      searchHint: "Try “react” or “fastapi” — we’ll find the repository for you.",
      searching: "Searching GitHub repositories...",
      searchError: "GitHub search is temporarily unavailable. You can still paste a full repository URL.",
      searchPrompt: "Choose a suggested repository or paste its full GitHub URL.",
      noResults: "No matching public repositories found.",
      noDescription: "No repository description",
      chooseFolder: "Choose a project folder",
      chooseAgain: "Choose again",
      browse: "Browse",
      folderPickerHint: "Opens your system folder picker on macOS and Windows.",
      folderReady: "Ready to analyze this folder",
      folderSelected: "{count} files ready",
      folderSafetyNote: "Only the source files needed for analysis will be uploaded.",
      localUploadDetail: "{skipped} generated, sensitive, or oversized files were excluded.",
      localAnalyze: "Analyze",
      localUploading: "Uploading project folder...",
      localUploadError: "The local folder could not be uploaded.",
      localEmptyError: "No analyzable source files remain after applying the safety filters.",
      localFolderReadError: "The selected folder could not be read. Please choose it again.",
      tryLabel: "Try:",
      statsLanguages: "Languages",
      statsAgents: "Agent Types",
      statsDepth: "Analysis Depth",
      statsDepthValue: "Full Repo",
      statsPrivacy: "Evidence",
      statsPrivacyValue: "Source-Linked",
      scroll: "Scroll",
    },

    trending: {
      eyebrow: "Explore",
      title: "Popular repositories, ready to analyze",
      subtitle: "Start with a well-known open-source project and see how CodeMap turns a large codebase into a navigable workspace.",
      curatedNote: "Curated examples · repository metadata may change",
      analyze: "Analyze",
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
            "CodeMap supports public GitHub repositories and project folders selected from macOS or Windows. Python, TypeScript, JavaScript, Go, and Rust codebases are especially well-supported.",
        },
        {
          question: "How does the multi-agent pipeline work?",
          answer:
            "CodeMap AI runs 4 specialized agents in parallel: a Static Analyzer that maps file structure and imports, a Behavior Inferer that understands runtime patterns, a Community Assessor that evaluates code quality signals, and a Reporter that synthesizes everything into an interactive onboarding guide.",
        },
        {
          question: "Is my code sent to the cloud?",
          answer:
            "Public GitHub repositories are cloned into a temporary server workspace. For local analysis, only the files you select are uploaded; dependency folders, build output, Git history, environment files, oversized files, and unsafe paths are excluded before analysis.",
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
        "Move from repository structure to key flows and risk signals without losing the code-level evidence.",
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
      subtitle: "Explore the structure, ask a question, and trace every answer back to the code in one continuous workflow.",
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
      title: "Every insight stays connected to the code.",
      desc: "CodeMap builds findings from the repository snapshot and preserves file and line references, so you can verify important claims instead of trusting a black-box summary.",
      badge: "Evidence-backed analysis",
    },

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: {
      tagline: "A clearer way to read codebases",
      desc: "Turn repository structure, key flows, and source-backed answers into one connected workspace.",
      featuresTitle: "Features",
      resourcesTitle: "Resources",
      features: ["Repo Analysis", "Architecture View", "Risk Signals", "Onboarding Report"],
      resources: ["Getting Started", "API Docs", "GitHub"],
      ctaTitle: "Ready to analyze?",
      ctaDesc: "Search for a public GitHub repository or paste its URL.",
      ctaButton: "Start Analysis →",
      statusOk: "Backend operational",
      copyright: "CODEMAP AI. BUILT FOR DEVELOPERS.",
      localFirst: "SOURCE-LINKED FINDINGS",
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

    repoInput: {
      title: "Analyze New Repository",
      subtitle: "Clones public GitHub repositories to analyze structure and code context.",
      tabGithub: "GitHub URL",
      tabLocal: "Local Path",
      labelGithub: "Repository URL",
      labelLocal: "Absolute Path",
      placeholderGithub: "https://github.com/owner/repo",
      placeholderLocal: "/path/to/local/repo",
      quickModelLabel: "Inference Model (Quick)",
      fast: "Fast",
      thinking: "Thinking",
      advancedSettings: "Advanced Settings",
      branchLabel: "Analysis Branch",
      branchPlaceholder: "Auto-detect default branch",
      customModelLabel: "Custom Model ID (Override)",
      customModelEmpty: "Use Quick Selection (Default)",
      comingSoon: "(Coming Soon)",
      forceRefresh: "Analyze with fresh snapshot",
      forceRefreshDesc: "Deletes existing clone on server and re-clones the remote repository.",
      submit: "Create Analysis Workspace",
      submitting: "Analyzing Repository...",
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
        fast: "Fast",
        deep: "Deep",
        fastDesc: "Fast responses using gpt-4o-mini — great for simple questions",
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

    // ── Auth ──────────────────────────────────────────────────────────────────
    auth: {
      errors: {
        INVALID_EMAIL: "The email format is invalid.",
        PASSWORD_TOO_SHORT: "The password must be at least 8 characters.",
        PASSWORD_RULE_VIOLATION: "The password does not meet the requirements.",
        INVALID_CREDENTIALS: "The email or password does not match.",
        USER_NOT_FOUND: "No account found with this email.",
        EMAIL_ALREADY_EXISTS: "This email is already registered.",
        default: "Authentication failed. Please try again.",
      },
      signup: {
        passwordMismatch: "Passwords do not match.",
        passwordTooShort: "Password must be at least 8 characters.",
        passwordLengthOk: "Password length is sufficient",
        passwordMatchOk: "Passwords match",
      },
      signInTitle: "Sign in to your account",
      signUpTitle: "Create a new account",
      emailLabel: "Email Address",
      emailPlaceholder: "you@example.com",
      passwordLabel: "Password",
      passwordPlaceholder: "••••••••",
      passwordMinPlaceholder: "At least 8 characters",
      confirmPasswordLabel: "Confirm Password",
      signInBtn: "Sign In",
      signUpBtn: "Sign Up",
      noAccount: "Don't have an account?",
      haveAccount: "Already have an account?",
      signUpSuccessTitle: "Welcome to CodeMap AI!",
      signUpSuccessDesc: "Your account has been created successfully. Redirecting...",
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
      signIn: "로그인",
      signUp: "회원가입",
      signOut: "로그아웃",
    },

    // ── Home hero ─────────────────────────────────────────────────────────────
    hero: {
      badge: "CodeMap AI",
      title: "복잡한 코드베이스도,\n한눈에 이해할 수 있게",
      subtitle:
        "낯선 저장소의 구조와 핵심 흐름, 꼭 알아야 할 맥락을 빠르게 파악하세요. 여러 분석 에이전트가 흩어진 코드를 연결해 이해하기 쉬운 화면으로 정리합니다.",
      sourceLabel: "저장소 가져오기 방식",
      sourceGithub: "GitHub 저장소",
      sourceLocal: "내 컴퓨터 폴더",
      placeholder: "저장소 이름을 검색하거나 GitHub URL을 붙여넣으세요",
      submit: "저장소 분석하기",
      searchHint: "‘react’ 또는 ‘fastapi’처럼 입력하면 저장소를 바로 찾아드려요.",
      searching: "GitHub 저장소를 찾고 있습니다...",
      searchError: "지금은 GitHub 검색을 사용할 수 없습니다. 전체 저장소 URL은 그대로 입력할 수 있어요.",
      searchPrompt: "추천 저장소를 선택하거나 전체 GitHub URL을 입력해주세요.",
      noResults: "일치하는 공개 저장소를 찾지 못했습니다.",
      noDescription: "저장소 설명이 없습니다.",
      chooseFolder: "프로젝트 폴더 선택",
      chooseAgain: "다시 선택",
      browse: "찾아보기",
      folderPickerHint: "macOS와 Windows의 기본 폴더 탐색기가 열립니다.",
      folderReady: "이 폴더를 분석할 준비가 됐어요",
      folderSelected: "파일 {count}개 준비됨",
      folderSafetyNote: "분석에 필요한 소스 파일만 업로드합니다.",
      localUploadDetail: "생성물·민감 파일·대용량 파일 {skipped}개를 제외했습니다.",
      localAnalyze: "분석 시작",
      localUploading: "프로젝트 폴더 업로드 중...",
      localUploadError: "로컬 폴더를 업로드하지 못했습니다.",
      localEmptyError: "안전 필터를 적용한 뒤 분석할 수 있는 소스 파일이 남지 않았습니다.",
      localFolderReadError: "선택한 폴더를 읽지 못했습니다. 다시 선택해주세요.",
      tryLabel: "예시:",
      statsLanguages: "언어",
      statsAgents: "에이전트 수",
      statsDepth: "분석 깊이",
      statsDepthValue: "전체 저장소",
      statsPrivacy: "검증 방식",
      statsPrivacyValue: "코드 근거",
      scroll: "스크롤",
    },

    trending: {
      eyebrow: "둘러보기",
      title: "인기 저장소로 바로 시작해보세요",
      subtitle: "잘 알려진 오픈소스 프로젝트를 골라 CodeMap이 큰 코드베이스를 탐색 가능한 워크스페이스로 바꾸는 과정을 확인해보세요.",
      curatedNote: "직접 고른 예시 목록 · 저장소 정보는 달라질 수 있습니다",
      analyze: "분석하기",
    },

    // ── Home sections ─────────────────────────────────────────────────────────
    howItWorks: {
      title: "저장소가 이해 가능한 지도가 되기까지",
      subtitle: "코드를 가져오는 순간부터 핵심 맥락을 정리한 리포트까지, 네 단계로 이어집니다.",
      steps: [
        {
          title: "저장소 선택",
          desc: "이름으로 공개 GitHub 저장소를 찾거나 URL을 붙여넣어 분석을 시작합니다.",
        },
        {
          title: "정적 분석",
          desc: "파일 구조와 임포트, 모듈 사이의 의존 관계를 코드에서 직접 읽어냅니다.",
        },
        {
          title: "핵심 흐름 파악",
          desc: "여러 분석 에이전트가 실행 흐름과 기술 스택, 코드 품질 신호를 함께 살펴봅니다.",
        },
        {
          title: "온보딩 리포트",
          desc: "분석 결과를 구조도와 근거 코드, 바로 질문할 수 있는 워크스페이스로 정리합니다.",
        },
      ],
    },

    // ── Use Cases ─────────────────────────────────────────────────────────────
    useCases: {
      title: "코드를 이해해야 하는 순간마다",
      subtitle: "기술 도입 검토부터 새 팀원의 적응, 보안 위험 확인까지 필요한 맥락을 빠르게 찾을 수 있습니다.",
      cases: [
        {
          title: "기술 도입 검토",
          desc: "낯선 라이브러리나 프로젝트를 도입하기 전에 구조와 의존성, 유지보수 신호를 먼저 확인하세요.",
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
          link: "위험 신호 확인",
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
            "공개 GitHub 저장소와 macOS·Windows에서 선택한 프로젝트 폴더를 분석할 수 있습니다. Python, TypeScript, JavaScript, Go, Rust 프로젝트를 특히 잘 분석합니다.",
        },
        {
          question: "멀티 에이전트 파이프라인은 어떻게 작동하나요?",
          answer:
            "서로 다른 역할을 맡은 분석 에이전트가 파일 구조와 의존 관계, 실행 흐름, 코드 품질 신호를 나눠 살펴봅니다. 마지막에는 결과를 한곳에서 탐색하고 바로 질문할 수 있는 워크스페이스로 정리합니다.",
        },
        {
          question: "코드가 클라우드로 전송되나요?",
          answer:
            "공개 GitHub 저장소는 서버의 임시 작업 공간에 복제됩니다. 로컬 분석은 사용자가 직접 고른 파일만 업로드하며, 의존성 폴더와 빌드 결과, Git 이력, 환경설정 파일, 대용량 파일, 안전하지 않은 경로는 분석 전에 제외합니다.",
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
      title: "궁금한 저장소부터 열어보세요",
      subtitle:
        "저장소 이름을 검색하거나 GitHub URL을 붙여넣으면 구조와 핵심 흐름을 바로 살펴볼 수 있습니다.",
      primary: "분석 시작",
      secondary: "GitHub에서 보기",
    },

    // ── BentoFeatures ─────────────────────────────────────────────────────────
    bento: {
      title: "코드를 이해하는 데 필요한 모든 것",
      subtitle:
        "저장소 구조부터 핵심 흐름과 위험 신호까지, 코드 근거를 놓치지 않고 한 화면에서 확인하세요.",
      features: [
        {
          title: "심층 코드 분석",
          desc: "여러 분석 에이전트가 파일과 의존성 흐름을 함께 읽어, 처음 보는 저장소도 중요한 부분부터 파악할 수 있게 돕습니다.",
        },
        {
          title: "구조 시각화",
          desc: "모듈 관계와 의존성 흐름을 한눈에 볼 수 있는 그래프로 정리합니다.",
          mockLabel: "출력:",
          mockValue: "dependency-graph.svg",
        },
        {
          title: "변경 이력 추적",
          desc: "커밋과 브랜치 흐름을 따라 코드가 어떻게 바뀌어 왔는지 살펴봅니다.",
        },
        {
          title: "보안 위험 점검",
          desc: "노출된 인증 정보와 주의가 필요한 코드 패턴을 찾아 우선순위와 함께 보여줍니다.",
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
      subtitle: "구조를 살펴보고 질문한 뒤 답변의 근거 코드로 돌아가는 과정을 한 흐름에서 확인하세요.",
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
      title: "분석 결과를 코드에서 바로 확인하세요",
      desc: "CodeMap은 저장소 스냅샷을 바탕으로 결과를 만들고 파일과 라인 근거를 함께 남깁니다. 중요한 설명은 요약만 믿지 않고 실제 코드로 돌아가 직접 확인할 수 있습니다.",
      badge: "코드 근거 기반 분석",
    },

    // ── Footer ────────────────────────────────────────────────────────────────
    footer: {
      tagline: "코드베이스를 더 선명하게 읽는 방법",
      desc: "저장소 구조와 핵심 흐름, 코드 근거가 있는 답변을 하나의 워크스페이스로 연결합니다.",
      featuresTitle: "기능",
      resourcesTitle: "리소스",
      features: ["저장소 분석", "구조 시각화", "위험 신호", "온보딩 리포트"],
      resources: ["시작하기", "API 문서", "GitHub"],
      ctaTitle: "분석할 준비가 됐나요?",
      ctaDesc: "공개 GitHub 저장소를 검색하거나 URL을 붙여넣어 시작하세요.",
      ctaButton: "분석 시작 →",
      statusOk: "백엔드 정상 작동",
      copyright: "CODEMAP AI. 개발자를 위해 만들었습니다.",
      localFirst: "코드 근거 연결",
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

    repoInput: {
      title: "새 저장소 분석",
      subtitle: "공개 GitHub 저장소를 실제로 복제해 구조와 코드 근거를 분석합니다.",
      tabGithub: "GitHub URL",
      tabLocal: "로컬 경로",
      labelGithub: "Repository URL",
      labelLocal: "절대 경로",
      placeholderGithub: "https://github.com/owner/repo",
      placeholderLocal: "/경로/로컬/저장소",
      quickModelLabel: "분석 모델 (빠른 선택)",
      fast: "Fast",
      thinking: "Thinking",
      advancedSettings: "고급 분석 설정",
      branchLabel: "분석 브랜치",
      branchPlaceholder: "기본 브랜치 자동 감지",
      customModelLabel: "사용자 지정 모델 ID (오버라이드)",
      customModelEmpty: "빠른 선택 사용 (기본)",
      comingSoon: "(준비중)",
      forceRefresh: "새 스냅샷으로 다시 분석",
      forceRefreshDesc: "서버에 남은 기존 clone을 삭제하고 원격 저장소를 다시 복제합니다.",
      submit: "분석 워크스페이스 만들기",
      submitting: "저장소 분석 중",
      errorGithubEmpty: "GitHub URL을 입력해주세요.",
      errorLocalEmpty: "로컬 경로를 입력해주세요.",
      errorGithubInvalid: "https://github.com/owner/repository 형식으로 입력해주세요.",
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
        fast: "Fast",
        deep: "Deep",
        fastDesc: "gpt-4o-mini로 빠른 응답 — 간단한 질문에 적합",
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

    // ── Auth ──────────────────────────────────────────────────────────────────
    auth: {
      errors: {
        INVALID_EMAIL: "이메일 형식이 올바르지 않습니다.",
        PASSWORD_TOO_SHORT: "비밀번호는 최소 8자 이상이어야 합니다.",
        PASSWORD_RULE_VIOLATION: "비밀번호가 서비스 규칙을 만족하지 않습니다.",
        INVALID_CREDENTIALS: "이메일 또는 비밀번호가 일치하지 않습니다.",
        USER_NOT_FOUND: "해당 이메일로 등록된 계정을 찾을 수 없습니다.",
        EMAIL_ALREADY_EXISTS: "이미 등록된 이메일입니다.",
        default: "인증에 실패했습니다. 다시 시도해주세요.",
      },
      signup: {
        passwordMismatch: "비밀번호가 일치하지 않습니다.",
        passwordTooShort: "비밀번호는 최소 8자 이상이어야 합니다.",
        passwordLengthOk: "비밀번호 길이가 적절합니다",
        passwordMatchOk: "비밀번호가 일치합니다",
      },
      signInTitle: "계정에 로그인하세요",
      signUpTitle: "새 계정 만들기",
      emailLabel: "이메일 주소",
      emailPlaceholder: "you@example.com",
      passwordLabel: "비밀번호",
      passwordPlaceholder: "••••••••",
      passwordMinPlaceholder: "최소 8자 이상",
      confirmPasswordLabel: "비밀번호 확인",
      signInBtn: "로그인",
      signUpBtn: "가입하기",
      noAccount: "계정이 없으신가요?",
      haveAccount: "이미 계정이 있으신가요?",
      signUpSuccessTitle: "CodeMap AI에 오신 것을 환영합니다!",
      signUpSuccessDesc: "계정이 성공적으로 생성되었습니다. 이동 중입니다...",
    },
  },
} as const;

export type TranslationKeys = typeof translations.en;
