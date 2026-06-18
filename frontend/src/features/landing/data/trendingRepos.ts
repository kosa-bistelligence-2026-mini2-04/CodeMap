export type TrendingRepository = {
  name: string;
  url: string;
  language: string;
  accent: string;
  description: {
    en: string;
    ko: string;
  };
};

export const TRENDING_REPOSITORIES: TrendingRepository[] = [
  {
    name: "react/react",
    url: "https://github.com/react/react",
    language: "JavaScript",
    accent: "#f7df1e",
    description: {
      en: "A library for building web and native user interfaces.",
      ko: "웹과 네이티브 사용자 인터페이스를 만드는 대표 라이브러리",
    },
  },
  {
    name: "vercel/next.js",
    url: "https://github.com/vercel/next.js",
    language: "TypeScript",
    accent: "#3178c6",
    description: {
      en: "The React framework for production applications.",
      ko: "프로덕션 React 애플리케이션을 위한 풀스택 프레임워크",
    },
  },
  {
    name: "tiangolo/fastapi",
    url: "https://github.com/fastapi/fastapi",
    language: "Python",
    accent: "#00a67e",
    description: {
      en: "A modern, high-performance Python API framework.",
      ko: "빠르고 현대적인 Python API 프레임워크",
    },
  },
  {
    name: "microsoft/vscode",
    url: "https://github.com/microsoft/vscode",
    language: "TypeScript",
    accent: "#3178c6",
    description: {
      en: "The open-source code editor that powers Visual Studio Code.",
      ko: "Visual Studio Code의 기반이 되는 오픈소스 편집기",
    },
  },
  {
    name: "pytorch/pytorch",
    url: "https://github.com/pytorch/pytorch",
    language: "Python",
    accent: "#3572a5",
    description: {
      en: "Tensor computation and deep neural networks with GPU support.",
      ko: "GPU 가속을 지원하는 텐서 연산·딥러닝 플랫폼",
    },
  },
  {
    name: "rust-lang/rust",
    url: "https://github.com/rust-lang/rust",
    language: "Rust",
    accent: "#dea584",
    description: {
      en: "A language empowering everyone to build reliable software.",
      ko: "안전하고 신뢰할 수 있는 소프트웨어를 위한 시스템 언어",
    },
  },
  {
    name: "kubernetes/kubernetes",
    url: "https://github.com/kubernetes/kubernetes",
    language: "Go",
    accent: "#00add8",
    description: {
      en: "Production-grade container orchestration.",
      ko: "프로덕션 환경을 위한 컨테이너 오케스트레이션 플랫폼",
    },
  },
  {
    name: "langchain-ai/langchain",
    url: "https://github.com/langchain-ai/langchain",
    language: "Python",
    accent: "#3572a5",
    description: {
      en: "A framework for building context-aware AI applications.",
      ko: "컨텍스트를 활용하는 AI 애플리케이션 개발 프레임워크",
    },
  },
  {
    name: "supabase/supabase",
    url: "https://github.com/supabase/supabase",
    language: "TypeScript",
    accent: "#3178c6",
    description: {
      en: "An open-source platform for Postgres-powered applications.",
      ko: "Postgres 기반 애플리케이션을 위한 오픈소스 플랫폼",
    },
  },
  {
    name: "tailwindlabs/tailwindcss",
    url: "https://github.com/tailwindlabs/tailwindcss",
    language: "TypeScript",
    accent: "#3178c6",
    description: {
      en: "A utility-first CSS framework for rapid interface development.",
      ko: "빠른 UI 개발을 돕는 유틸리티 중심 CSS 프레임워크",
    },
  },
];
