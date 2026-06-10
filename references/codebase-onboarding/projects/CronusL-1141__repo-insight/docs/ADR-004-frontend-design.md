# ADR-004 前端架构与实时进度协议

- 状态：Accepted
- 日期：2026-04-12
- 决策者：frontend-arch
- 关联文档：[ARCHITECTURE.md](./ARCHITECTURE.md) · ADR-001 技术栈 · ADR-002 编排协议 · ADR-003 Guardrail · API-CONTRACT.md

## 1. 背景

RepoInsight 前端是一个单页应用（SPA），承载三类核心交互：

1. 用户输入本地 Git 路径或 GitHub URL 并提交分析任务。
2. 实时观察 4 个后端 Agent（StaticAnalyzer / BehaviorInferer / CommunityAssessor / Reporter）的并发进度、状态与降级提示。
3. 最终渲染由 Reporter 生成的 HTML 报告（含 ECharts 行级风险热力图），并允许用户点击代码行跳转到对应文件位置。

后端经 ADR-001/002 已锁定 FastAPI + WebSocket，前端必须与之严格对齐：契约优先、零 `any` 逃逸、HTML 渲染 XSS 安全、120 秒任务总预算下的鲁棒 UI。

## 2. 决策

### 2.1 技术栈锁定

| 维度 | 选型 | 版本 | 理由 |
|---|---|---|---|
| 构建工具 | Vite | 5.x | 冷启动快、HMR 体验好、与 React 18 原生兼容 |
| UI 框架 | React | 18.x | 并发渲染、`useTransition` 配合长任务 |
| 类型系统 | TypeScript | 5.x | strict 模式，禁用 `any` |
| 样式 | TailwindCSS | 3.x | 原子化、零运行时、与 shadcn/ui 默认集成 |
| 组件库 | shadcn/ui | latest | 复制源码而非依赖，按需裁剪 |
| 图表 | ECharts | 5.x | 与后端 Reporter 输出的热力图配置同构 |
| ECharts 适配 | echarts-for-react | 3.x | 声明式封装，替换 DOM 挂载样板 |
| 富文本渲染 | react-html-parser + DOMPurify | 1.4.x / 3.x | XSS 防护必选 |
| 状态管理 | zustand | 4.x | 极简 API、零 boilerplate、分片 selector 避免无谓 re-render |
| HTTP 客户端 | axios | 1.x | 拦截器统一处理错误码 |
| 实时通信 | 原生 WebSocket | — | 不引入 socket.io，避免 100KB+ 依赖 |
| 表单与校验 | react-hook-form + zod | 7.x / 3.x | 受控成本低、类型推导友好 |

**Bundle 预算**：首屏 gzip ≤ 250 KB（excluding ECharts，ECharts 通过动态 import 按需加载，仅在报告渲染阶段拉取）。

### 2.2 目录结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.cjs
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx                          # 应用入口
    ├── App.tsx                           # 路由 + 布局骨架
    ├── components/
    │   ├── RepoInput.tsx                 # 双模式输入框（local / github）
    │   ├── ProgressPanel.tsx             # 4 路并发进度面板（容器）
    │   ├── AgentStatusCard.tsx           # 单个 Agent 状态卡（叶子组件）
    │   ├── ReportViewer.tsx              # HTML 报告渲染入口
    │   ├── HeatmapChart.tsx              # ECharts 热力图封装
    │   ├── ConflictBanner.tsx            # 冲突消解提示横幅
    │   ├── DegradedNotice.tsx            # 超时降级提示
    │   ├── ErrorBoundary.tsx             # React 错误边界
    │   └── ui/                           # shadcn/ui 复制源码（button/input/card/toast …）
    ├── hooks/
    │   ├── useAnalysisJob.ts             # 提交任务 + 轮询兜底
    │   ├── useWebSocket.ts               # 实时进度订阅
    │   └── useEchartsMount.ts            # 报告内嵌图表挂载
    ├── store/
    │   └── analysisStore.ts              # zustand: jobId / agents / report / errors
    ├── lib/
    │   ├── api.ts                        # axios 实例 + REST 封装
    │   ├── sanitize.ts                   # DOMPurify 配置
    │   ├── validators.ts                 # 输入校验（路径 / URL）
    │   └── env.ts                        # 环境变量收口
    ├── types/
    │   ├── contracts.ts                  # 与后端 Pydantic 对齐的 TS 类型
    │   └── ws-events.ts                  # WebSocket 消息联合类型
    ├── styles/
    │   └── globals.css                   # Tailwind 指令 + 基础变量
    └── assets/
        └── logo.svg
```

**约束**：

- `components/` 仅承载 UI，禁止直接调用 `lib/api.ts`，必须通过 hooks 或 store。
- `lib/` 内的模块互不依赖 React，可被任意层引用。
- `types/contracts.ts` 是前后端契约的唯一前端镜像，其它文件禁止再声明同名类型。

### 2.3 组件契约

```typescript
// types/contracts.ts —— 与后端 Pydantic v2 严格对齐
export type AgentName =
  | 'static_analyzer'
  | 'behavior_inferer'
  | 'community_assessor'
  | 'reporter';

export type AgentStatusKind =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'degraded';

export interface AgentStatus {
  name: AgentName;
  status: AgentStatusKind;
  progress: number;          // 0-100
  message?: string;          // 最近一条进度日志
  startedAt?: string;        // ISO8601
  completedAt?: string;
  durationMs?: number;
}

export interface LineRisk {
  line: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  metric?: 'complexity' | 'coverage' | 'maintainability';
}

export type FileHeatmap = Record<string, LineRisk[]>;

export interface Recommendation {
  id: string;
  title: string;
  rationale: string;
  effort: 'S' | 'M' | 'L';
}

export interface AnalysisJob {
  jobId: string;
  source: 'local' | 'github';
  target: string;
  createdAt: string;
}

export interface AnalysisReport {
  jobId: string;
  htmlReport: string;        // 由 Reporter 输出，前端 DOMPurify 后渲染
  fileHeatmap: FileHeatmap;
  recommendations: Recommendation[];
  generatedAt: string;
}
```

```typescript
// 主要组件 Props
export interface RepoInputProps {
  onSubmit: (input: { source: 'local' | 'github'; path: string }) => void;
  disabled?: boolean;
  defaultMode?: 'local' | 'github';
}

export interface ProgressPanelProps {
  jobId: string;
  agents: AgentStatus[];     // 长度恒为 4，顺序固定
}

export interface AgentStatusCardProps {
  agent: AgentStatus;
  onRetry?: (name: AgentName) => void;
}

export interface ReportViewerProps {
  report: AnalysisReport;
  onLineClick?: (file: string, line: number) => void;
}

export interface HeatmapChartProps {
  fileHeatmap: FileHeatmap;
  onLineClick?: (file: string, line: number) => void;
  height?: number;
}

export interface ConflictBannerProps {
  module: string;
  staticVerdict: string;
  behaviorVerdict: string;
  resolution: string;
}

export interface DegradedNoticeProps {
  agent: AgentName;
  reason: string;
  fallbackUsed: string;
}
```

**Props 设计原则**：

1. 所有回调以 `on` 前缀，异步父组件可控。
2. 不传整个 store 切片进入叶子组件，仅传必要字段。
3. `progress: number` 限定 0–100，超出由组件内部 clamp，不抛错。

### 2.4 WebSocket Hook 设计

WebSocket 是任务进度的主通道，REST 轮询作为兜底（`useAnalysisJob` 内部以 5s 间隔拉取 `/jobs/{jobId}`，仅在 WS 断线 ≥ 10s 时启用）。

**消息类型**：

```typescript
// types/ws-events.ts
export type WsEvent =
  | { type: 'agent_status'; payload: AgentStatus }
  | { type: 'conflict_detected'; payload: ConflictBannerProps }
  | { type: 'degraded'; payload: DegradedNoticeProps }
  | { type: 'completed'; payload: { jobId: string } }
  | { type: 'failed'; payload: { jobId: string; error: string } }
  | { type: 'heartbeat'; payload: { ts: number } };
```

**`useWebSocket` 实现草案**：

```typescript
import { useEffect, useRef, useState } from 'react';
import type { WsEvent } from '@/types/ws-events';

interface UseWebSocketOptions {
  url: string;
  onEvent: (event: WsEvent) => void;
  enabled: boolean;
  maxRetries?: number;
}

interface UseWebSocketState {
  connected: boolean;
  retries: number;
  lastError?: string;
}

const BACKOFF_MS = [500, 1000, 2000, 4000, 8000] as const;

export function useWebSocket({
  url,
  onEvent,
  enabled,
  maxRetries = BACKOFF_MS.length,
}: UseWebSocketOptions): UseWebSocketState {
  const [state, setState] = useState<UseWebSocketState>({
    connected: false,
    retries: 0,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);

  // 用 ref 锁定最新回调，避免重连依赖 onEvent 的引用变化
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setState({ connected: true, retries: 0 });
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as WsEvent;
          if (data.type === 'heartbeat') return;
          onEventRef.current(data);
        } catch (err) {
          // 协议异常：丢弃单条消息，不断开连接
          console.warn('[ws] invalid payload', err);
        }
      };

      ws.onerror = () => {
        setState((s) => ({ ...s, lastError: 'connection_error' }));
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (cancelled) return;
        if (retryRef.current >= maxRetries) return;
        const delay = BACKOFF_MS[retryRef.current];
        retryRef.current += 1;
        setState((s) => ({ ...s, retries: retryRef.current }));
        timerRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (timerRef.current) window.clearTimeout(timerRef.current);
      const ws = wsRef.current;
      if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close(1000, 'unmount');
      }
      wsRef.current = null;
    };
  }, [url, enabled, maxRetries]);

  return state;
}
```

**重连策略**：指数退避 `500ms → 8s`，最多 5 次；超过则放弃 WS 并由 `useAnalysisJob` 切到 REST 轮询。`unmount` 主动 `close(1000)` 避免泄漏。

**消息分发**：在 `useAnalysisJob` 内消费 `WsEvent` 并写入 zustand：

```typescript
const handleEvent = useCallback((evt: WsEvent) => {
  switch (evt.type) {
    case 'agent_status':
      store.upsertAgent(evt.payload);
      break;
    case 'conflict_detected':
      store.setConflict(evt.payload);
      break;
    case 'degraded':
      store.addDegraded(evt.payload);
      break;
    case 'completed':
      store.markCompleted(evt.payload.jobId);
      void api.fetchReport(evt.payload.jobId).then(store.setReport);
      break;
    case 'failed':
      store.markFailed(evt.payload.jobId, evt.payload.error);
      break;
  }
}, []);
```

### 2.5 HTML 报告安全渲染

**问题**：Reporter 输出的 HTML 报告由后端 LLM 路径间接生成，存在 XSS 风险（`<script>`、`onerror`、`javascript:` URL）。同时报告内嵌 ECharts 配置占位符，需要在渲染后挂载图表。

**为什么不裸用 `dangerouslySetInnerHTML`**：

1. 后端任意阶段被注入即直通 DOM，攻击面 = 整个 Reporter 链路。
2. 团队规范要求所有第三方 HTML 必须经 sanitizer。
3. DOMPurify 的白名单是显式契约，比"全黑名单"更稳定。

**DOMPurify 配置**（`lib/sanitize.ts`）：

```typescript
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
  'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3',
  'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'span',
  'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
];

const ALLOWED_ATTR = [
  'href', 'title', 'alt', 'src', 'class', 'id',
  'data-echarts-config', 'data-file', 'data-line',
];

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('rel', 'noopener noreferrer');
    node.setAttribute('target', '_blank');
  }
  if (node.tagName === 'IMG') {
    const src = node.getAttribute('src') ?? '';
    if (!/^https?:\/\//i.test(src) && !src.startsWith('data:image/')) {
      node.removeAttribute('src');
    }
  }
});

export function sanitizeReport(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onclick', 'onload', 'onmouseover'],
  });
}
```

**ECharts 占位符策略**：

后端 Reporter 输出形如 `<div data-echarts-config='{"type":"heatmap",...}'></div>` 的占位节点，前端通过 `useEchartsMount` 在 `ReportViewer` 渲染完成后扫描并挂载：

```typescript
export function useEchartsMount(rootRef: React.RefObject<HTMLElement>) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const placeholders = root.querySelectorAll<HTMLDivElement>(
      '[data-echarts-config]',
    );
    const instances: Array<{ dispose: () => void }> = [];

    void import('echarts').then((echarts) => {
      placeholders.forEach((el) => {
        const raw = el.getAttribute('data-echarts-config');
        if (!raw) return;
        try {
          const option = JSON.parse(raw);
          const chart = echarts.init(el);
          chart.setOption(option);
          instances.push(chart);
        } catch (err) {
          console.warn('[echarts] invalid config', err);
        }
      });
    });

    return () => {
      instances.forEach((c) => c.dispose());
    };
  }, [rootRef]);
}
```

ECharts 通过动态 `import('echarts')` 按需加载，首屏不计入主 bundle。

### 2.6 输入校验

`lib/validators.ts`：

```typescript
import { z } from 'zod';

const WINDOWS_PATH = /^[a-zA-Z]:[\\/](?:[^<>:"|?*\r\n]+[\\/]?)*$/;
const UNIX_PATH = /^\/(?:[^<>:"|?*\r\n\0]+\/?)*$/;
const GITHUB_URL = /^https:\/\/github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/;

export const localPathSchema = z
  .string()
  .min(1, '路径不能为空')
  .refine(
    (v) => WINDOWS_PATH.test(v) || UNIX_PATH.test(v),
    '请输入有效的本地路径（Windows 或 Unix 格式）',
  );

export const githubUrlSchema = z
  .string()
  .min(1, 'URL 不能为空')
  .regex(GITHUB_URL, '请输入有效的 GitHub 仓库 URL');

export function parseGithubUrl(url: string): { owner: string; repo: string } | null {
  const m = url.match(GITHUB_URL);
  if (!m) return null;
  return { owner: m[1], repo: m[2] };
}
```

`RepoInput` 使用 `react-hook-form` + `zodResolver`，提交前同步校验，错误用 shadcn/ui 的 `<FormMessage>` 展示在输入框下方。空白字符在校验前 `.trim()`。

### 2.7 响应式布局

**断点**（Tailwind 默认 + 自定义）：

| 名称 | 宽度 | 布局策略 |
|---|---|---|
| `mobile` | < 768px | 垂直堆叠：输入 → 进度 → 报告 |
| `tablet` | 768–1023px | 输入与进度横向排列；报告下方全宽 |
| `desktop` | ≥ 1024px | 左右两栏：左 384px 输入+进度，右 1fr 报告 |
| `wide` | ≥ 1440px | 报告区限制最大 1280px 居中 |

**关键 Tailwind 模板**：

```tsx
<div className="min-h-screen bg-background text-foreground">
  <main className="mx-auto grid max-w-screen-2xl gap-6 p-4 lg:grid-cols-[384px_1fr] lg:p-8">
    <aside className="space-y-4">
      <RepoInput onSubmit={handleSubmit} disabled={running} />
      {jobId && <ProgressPanel jobId={jobId} agents={agents} />}
    </aside>
    <section className="min-h-[60vh]">
      {report ? <ReportViewer report={report} /> : <EmptyState />}
    </section>
  </main>
</div>
```

移动端额外处理：

- 进度面板在 `mobile` 折叠为 `<details>`，默认展开 `running` 中的 Agent。
- 报告热力图在 `< 768px` 切换为列表视图（按文件分组），避免横向滚动。
- 所有可点击区域 ≥ 44×44 px。

**可访问性**：

- 输入框 `<label htmlFor>` 显式绑定，焦点环使用 `focus-visible:ring-2`。
- Agent 状态用色差 + 图标 + 文本三重表达，色彩对比度 ≥ 4.5:1（WCAG AA）。
- WebSocket 进度通过 `aria-live="polite"` 通知屏幕阅读器。

### 2.8 与后端 API-CONTRACT 同步策略

**立项阶段**：手写 `types/contracts.ts`，与 `backend/app/models/` 中的 Pydantic v2 Schema 字段一一对应。命名规范：

- 后端 `snake_case` → 前端字段保持 `snake_case`（避免序列化层做 case 转换，简化调试）。
- 枚举类型同步使用字符串字面量联合类型，禁止 TS `enum`。

**演进阶段**（≥ M2）：引入 `openapi-typescript`，从 FastAPI `/openapi.json` 自动生成 `types/openapi.d.ts`，`contracts.ts` 改为 re-export 自动生成的类型。流程：

1. CI 在后端构建后导出 `openapi.json` → 上传 artifact。
2. 前端 `pnpm run sync:contracts` 拉取并执行 `openapi-typescript openapi.json -o src/types/openapi.d.ts`。
3. 类型差异 ≥ 1 处时 CI 标红，强制人工确认。

**契约破坏检测**：在 `lib/api.ts` 的 axios response interceptor 内用 zod schema parse 关键响应，运行时不匹配立即抛错并上报：

```typescript
const reportSchema = z.object({
  jobId: z.string(),
  htmlReport: z.string(),
  fileHeatmap: z.record(z.array(lineRiskSchema)),
  recommendations: z.array(recommendationSchema),
  generatedAt: z.string(),
});
```

## 3. 状态管理（zustand）

```typescript
// store/analysisStore.ts
interface AnalysisState {
  jobId: string | null;
  agents: Record<AgentName, AgentStatus>;
  report: AnalysisReport | null;
  conflict: ConflictBannerProps | null;
  degraded: DegradedNoticeProps[];
  error: string | null;

  startJob: (jobId: string) => void;
  upsertAgent: (status: AgentStatus) => void;
  setReport: (report: AnalysisReport) => void;
  setConflict: (c: ConflictBannerProps) => void;
  addDegraded: (d: DegradedNoticeProps) => void;
  markCompleted: (jobId: string) => void;
  markFailed: (jobId: string, error: string) => void;
  reset: () => void;
}
```

**re-render 控制**：组件订阅时使用分片 selector：

```typescript
const reporterStatus = useAnalysisStore((s) => s.agents.reporter);
```

避免全量订阅 `agents` 导致 4 个卡片同步 re-render。

## 4. 错误与加载状态

| 场景 | UI 表现 |
|---|---|
| WS 重连中 | 进度面板顶部黄色横幅 "正在重连…(N/5)" |
| WS 失败兜底轮询 | 横幅切换为 "已切换到轮询模式" |
| 单 Agent failed | 卡片红色描边 + 重试按钮（仅 BehaviorInferer 可重试） |
| 单 Agent degraded | 卡片橙色描边 + 降级原因 tooltip |
| 任务超总预算 | 全屏对话框，提供 "查看部分结果" 与 "重新分析" |
| 报告加载中 | 右侧区域 Skeleton（与最终布局等高，CLS = 0） |
| 输入校验失败 | 输入框下方红字提示，提交按钮 disabled |

所有顶层异常被 `ErrorBoundary` 捕获，展示降级页面并提供 "复制错误信息" 按钮（不上报第三方）。

## 5. 性能预算

| 指标 | 目标 |
|---|---|
| LCP | < 2.0 s（首屏不含 ECharts） |
| FID / INP | < 100 ms |
| CLS | < 0.05（Skeleton 与最终布局等高） |
| 主 bundle gzip | ≤ 250 KB |
| ECharts chunk gzip | ≤ 350 KB（动态 import） |
| Lighthouse Performance | ≥ 90 |

**优化手段**：

1. ECharts、DOMPurify 通过动态 import 拆 chunk。
2. `ProgressPanel` 内 `AgentStatusCard` 使用 `React.memo` + 自定义 `arePropsEqual`。
3. 报告 HTML 大于 100 KB 时分块渲染（`useTransition` 包裹 `setReport`）。
4. Tailwind JIT 模式 + `content` 精确匹配，生产 CSS 通常 ≤ 15 KB。

## 6. 安全清单

- [x] 所有 HTML 渲染走 `sanitizeReport`，禁用 `dangerouslySetInnerHTML` 直接调用（ESLint 规则 `react/no-danger` 仅在 `ReportViewer.tsx` 内白名单）。
- [x] WS 连接强制 `wss://`（生产环境），`ws://` 仅 `import.meta.env.DEV` 时允许。
- [x] axios 请求附带 `X-Request-Id`（uuid v4），便于后端审计。
- [x] `lib/env.ts` 集中读取 `VITE_*` 变量，禁止组件内直接 `import.meta.env.X`。
- [x] CSP 头由部署层注入：`default-src 'self'; script-src 'self'; connect-src 'self' wss:`。
- [x] 不在前端日志输出 LLM 原始返回（避免 token 泄漏）。

## 7. 测试策略（前置说明，实施在阶段 2）

- 单元：Vitest + @testing-library/react，覆盖 hooks 与纯组件。
- 契约：zod parse 运行时校验 + tsc 编译时校验。
- E2E：Playwright，三条 happy path（local / github / 超时降级）。
- 可访问性：axe-core 集成到 Playwright，零 violation 准入。

## 8. 后果

**正面**：

- 类型契约统一，前后端字段漂移可在编译期发现。
- WS 重连 + REST 兜底，120 秒任务窗口内 UI 永不"假死"。
- DOMPurify + CSP 双层防御，HTML 报告 XSS 风险可控。
- ECharts 动态加载使首屏加载与功能复杂度解耦。

**负面 / 取舍**：

- 手写 `contracts.ts` 在后端字段频繁变动期会有 drift，需在 M2 切到 `openapi-typescript`。
- 自渲染 ECharts 占位符的方案要求后端严格遵循 `data-echarts-config` 约定，跨团队协调成本存在。
- zustand 缺少 Redux DevTools 那样的时间旅行，复杂调试需手动加日志中间件。

## 9. 未决事项

1. 报告导出 PDF 是否在前端做（`html2pdf.js` ≈ 200KB）还是由后端 weasyprint 渲染——倾向后端，待 ADR-005 决议。
2. 多语言：当前默认中文，i18n 框架（`react-i18next` vs `lingui`）延后到 v1.1。
3. 用户登录与历史报告列表：M0 不做，仅 jobId 本地 `sessionStorage` 暂存。
