import clsx from "clsx";

export type SeoVisualVariant =
  | "hero-flow"
  | "analysis-workflow"
  | "review-workflow"
  | "security-workflow"
  | "comparison-grid"
  | "trust-signal";

type SeoVisualProps = {
  variant: SeoVisualVariant;
  ariaLabel: string;
  sizeMode?: "compact" | "wide";
  animate?: boolean;
  priority?: "low" | "high";
};

const sizeClasses = {
  compact: "max-w-2xl",
  wide: "max-w-4xl",
};

function Dot({
  x,
  y,
  color,
  animate,
}: {
  x: number;
  y: number;
  color: string;
  animate: boolean;
}) {
  return (
    <circle
      cx={x}
      cy={y}
      r="5"
      fill={color}
      className={animate ? "motion-safe:animate-pulse" : undefined}
    />
  );
}

export default function SeoVisual({
  variant,
  ariaLabel,
  sizeMode = "wide",
  animate = true,
  priority = "low",
}: SeoVisualProps) {
  const wrapperClass = clsx(
    "mx-auto w-full rounded-2xl border border-white/10 bg-zinc-900/40 p-4",
    sizeClasses[sizeMode],
  );

  const commonSvgProps = {
    role: "img",
    "aria-label": ariaLabel,
    viewBox: "0 0 800 340",
    className: "w-full h-auto",
    "data-priority": priority,
  };

  if (variant === "hero-flow") {
    return (
      <div className={wrapperClass}>
        <svg {...commonSvgProps}>
          <title>{ariaLabel}</title>
          <desc>Repository analysis flow from URL input to architecture and security output.</desc>
          <rect x="20" y="40" width="180" height="84" rx="14" fill="#1f2937" stroke="#3b82f6" />
          <rect x="310" y="40" width="180" height="84" rx="14" fill="#18181b" stroke="#22d3ee" />
          <rect x="600" y="40" width="180" height="84" rx="14" fill="#18181b" stroke="#a3e635" />
          <text x="110" y="78" textAnchor="middle" fill="#e5e7eb" fontSize="18">Repo URL</text>
          <text x="400" y="78" textAnchor="middle" fill="#e5e7eb" fontSize="18">Agentic CAG</text>
          <text x="690" y="78" textAnchor="middle" fill="#e5e7eb" fontSize="18">Actionable Output</text>
          <line x1="200" y1="82" x2="310" y2="82" stroke="#60a5fa" strokeWidth="3" />
          <line x1="490" y1="82" x2="600" y2="82" stroke="#67e8f9" strokeWidth="3" />
          <Dot x={255} y={82} color="#60a5fa" animate={animate} />
          <Dot x={545} y={82} color="#67e8f9" animate={animate} />

          <rect x="70" y="200" width="190" height="92" rx="12" fill="#111827" stroke="#4f46e5" />
          <rect x="310" y="200" width="190" height="92" rx="12" fill="#111827" stroke="#f59e0b" />
          <rect x="550" y="200" width="190" height="92" rx="12" fill="#111827" stroke="#10b981" />
          <text x="165" y="250" textAnchor="middle" fill="#d1d5db" fontSize="16">Architecture Map</text>
          <text x="405" y="250" textAnchor="middle" fill="#d1d5db" fontSize="16">Code Review</text>
          <text x="645" y="250" textAnchor="middle" fill="#d1d5db" fontSize="16">Security Scan</text>
        </svg>
      </div>
    );
  }

  if (variant === "analysis-workflow") {
    return (
      <div className={wrapperClass}>
        <svg {...commonSvgProps}>
          <title>{ariaLabel}</title>
          <desc>Repository analysis pipeline showing ingestion, mapping, and report generation.</desc>
          <rect x="40" y="120" width="170" height="80" rx="12" fill="#1f2937" stroke="#60a5fa" />
          <rect x="315" y="120" width="170" height="80" rx="12" fill="#111827" stroke="#22d3ee" />
          <rect x="590" y="120" width="170" height="80" rx="12" fill="#111827" stroke="#34d399" />
          <text x="125" y="164" textAnchor="middle" fill="#e5e7eb" fontSize="15">Ingest Repository</text>
          <text x="400" y="164" textAnchor="middle" fill="#e5e7eb" fontSize="15">Map Architecture</text>
          <text x="675" y="164" textAnchor="middle" fill="#e5e7eb" fontSize="15">Generate Insights</text>
          <line x1="210" y1="160" x2="315" y2="160" stroke="#60a5fa" strokeWidth="3" />
          <line x1="485" y1="160" x2="590" y2="160" stroke="#34d399" strokeWidth="3" />
          <Dot x={262} y={160} color="#60a5fa" animate={animate} />
          <Dot x={537} y={160} color="#34d399" animate={animate} />
        </svg>
      </div>
    );
  }

  if (variant === "review-workflow") {
    return (
      <div className={wrapperClass}>
        <svg {...commonSvgProps}>
          <title>{ariaLabel}</title>
          <desc>AI code review workflow from change intent through context-aware feedback.</desc>
          <rect x="40" y="70" width="240" height="95" rx="12" fill="#1f2937" stroke="#818cf8" />
          <rect x="300" y="70" width="240" height="95" rx="12" fill="#111827" stroke="#60a5fa" />
          <rect x="560" y="70" width="200" height="95" rx="12" fill="#111827" stroke="#22d3ee" />
          <text x="160" y="122" textAnchor="middle" fill="#e5e7eb" fontSize="15">Review Scope + Intent</text>
          <text x="420" y="122" textAnchor="middle" fill="#e5e7eb" fontSize="15">Repository Context Graph</text>
          <text x="660" y="122" textAnchor="middle" fill="#e5e7eb" fontSize="15">Actionable Feedback</text>
          <line x1="280" y1="118" x2="300" y2="118" stroke="#818cf8" strokeWidth="3" />
          <line x1="540" y1="118" x2="560" y2="118" stroke="#22d3ee" strokeWidth="3" />
          <rect x="115" y="210" width="570" height="80" rx="12" fill="#09090b" stroke="#3f3f46" />
          <text x="400" y="258" textAnchor="middle" fill="#d4d4d8" fontSize="14">
            Flags logic gaps, dependency impact, and quality risks with full-file context.
          </text>
        </svg>
      </div>
    );
  }

  if (variant === "security-workflow") {
    return (
      <div className={wrapperClass}>
        <svg {...commonSvgProps}>
          <title>{ariaLabel}</title>
          <desc>Security scanning pipeline for detection, validation, and remediation prioritization.</desc>
          <rect x="40" y="95" width="220" height="88" rx="12" fill="#1f2937" stroke="#f59e0b" />
          <rect x="290" y="95" width="220" height="88" rx="12" fill="#111827" stroke="#ef4444" />
          <rect x="540" y="95" width="220" height="88" rx="12" fill="#111827" stroke="#10b981" />
          <text x="150" y="147" textAnchor="middle" fill="#fef3c7" fontSize="15">Detect Signals</text>
          <text x="400" y="147" textAnchor="middle" fill="#fecaca" fontSize="15">Verify Findings</text>
          <text x="650" y="147" textAnchor="middle" fill="#dcfce7" fontSize="15">Prioritize Fixes</text>
          <line x1="260" y1="139" x2="290" y2="139" stroke="#f59e0b" strokeWidth="3" />
          <line x1="510" y1="139" x2="540" y2="139" stroke="#10b981" strokeWidth="3" />
          <Dot x={275} y={139} color="#f59e0b" animate={animate} />
          <Dot x={525} y={139} color="#10b981" animate={animate} />
          <path d="M95 250 L205 250 L185 225 M205 250 L185 275" stroke="#f59e0b" strokeWidth="2.5" fill="none" />
          <path d="M345 250 L455 250 L435 225 M455 250 L435 275" stroke="#ef4444" strokeWidth="2.5" fill="none" />
          <path d="M595 250 L705 250 L685 225 M705 250 L685 275" stroke="#22c55e" strokeWidth="2.5" fill="none" />
        </svg>
      </div>
    );
  }

  if (variant === "comparison-grid") {
    return (
      <div className={wrapperClass}>
        <svg {...commonSvgProps}>
          <title>{ariaLabel}</title>
          <desc>Comparison matrix for methodology, context depth, and security signal quality.</desc>
          <rect x="35" y="40" width="730" height="255" rx="14" fill="#09090b" stroke="#3f3f46" />
          <line x1="35" y1="105" x2="765" y2="105" stroke="#27272a" />
          <line x1="260" y1="40" x2="260" y2="295" stroke="#27272a" />
          <line x1="510" y1="40" x2="510" y2="295" stroke="#27272a" />
          <text x="148" y="82" textAnchor="middle" fill="#e4e4e7" fontSize="16">Criteria</text>
          <text x="385" y="82" textAnchor="middle" fill="#93c5fd" fontSize="16">RepoMind</text>
          <text x="637" y="82" textAnchor="middle" fill="#d4d4d8" fontSize="16">Traditional Tools</text>
          <text x="145" y="145" textAnchor="middle" fill="#d4d4d8" fontSize="14">Context Depth</text>
          <text x="145" y="195" textAnchor="middle" fill="#d4d4d8" fontSize="14">Security Signal</text>
          <text x="145" y="245" textAnchor="middle" fill="#d4d4d8" fontSize="14">Actionability</text>
          <text x="385" y="145" textAnchor="middle" fill="#bbf7d0" fontSize="14">Full-file, graph-aware</text>
          <text x="385" y="195" textAnchor="middle" fill="#bbf7d0" fontSize="14">Validated findings</text>
          <text x="385" y="245" textAnchor="middle" fill="#bbf7d0" fontSize="14">Prioritized fixes</text>
          <text x="637" y="145" textAnchor="middle" fill="#f5f5f5" fontSize="14">Snippet-first</text>
          <text x="637" y="195" textAnchor="middle" fill="#f5f5f5" fontSize="14">Alert-heavy noise</text>
          <text x="637" y="245" textAnchor="middle" fill="#f5f5f5" fontSize="14">Manual triage</text>
        </svg>
      </div>
    );
  }

  return (
    <div className={wrapperClass}>
      <svg {...commonSvgProps}>
        <title>{ariaLabel}</title>
        <desc>Trust and operational reliability summary.</desc>
        <rect x="60" y="70" width="220" height="190" rx="14" fill="#111827" stroke="#38bdf8" />
        <rect x="300" y="70" width="220" height="190" rx="14" fill="#111827" stroke="#34d399" />
        <rect x="540" y="70" width="220" height="190" rx="14" fill="#111827" stroke="#a3e635" />
        <text x="170" y="140" textAnchor="middle" fill="#bae6fd" fontSize="15">Privacy-First</text>
        <text x="170" y="175" textAnchor="middle" fill="#e5e7eb" fontSize="13">No model training</text>
        <text x="410" y="140" textAnchor="middle" fill="#bbf7d0" fontSize="15">Evidence-First</text>
        <text x="410" y="175" textAnchor="middle" fill="#e5e7eb" fontSize="13">Actionable outputs</text>
        <text x="650" y="140" textAnchor="middle" fill="#d9f99d" fontSize="15">Operationally Reliable</text>
        <text x="650" y="175" textAnchor="middle" fill="#e5e7eb" fontSize="13">Fast repeatable scans</text>
      </svg>
    </div>
  );
}
