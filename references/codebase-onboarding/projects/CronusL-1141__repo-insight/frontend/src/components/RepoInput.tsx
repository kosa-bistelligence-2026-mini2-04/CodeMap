import { useEffect, useId, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { LlmModel, ProviderCatalog } from '@/types/contracts';

export type RepoSource = 'local' | 'github';

const PROVIDER_BADGES: Record<ProviderCatalog['provider'], { label: string; color: string }> = {
  openai:   { label: 'OpenAI',   color: 'bg-emerald-100 text-emerald-700' },
  deepseek: { label: 'DeepSeek', color: 'bg-blue-100 text-blue-700' },
  qwen:     { label: '通义千问', color: 'bg-purple-100 text-purple-700' },
  zhipu:    { label: '智谱 GLM', color: 'bg-indigo-100 text-indigo-700' },
  moonshot: { label: 'Kimi',     color: 'bg-pink-100 text-pink-700' },
  custom:   { label: 'Custom',   color: 'bg-gray-100 text-gray-700' },
};

export interface RepoInputProps {
  onSubmit: (input: {
    source: RepoSource;
    path: string;
    force_refresh?: boolean;
    model?: LlmModel;
  }) => void;
  disabled?: boolean;
  defaultMode?: RepoSource;
}

const WINDOWS_PATH = /^[a-zA-Z]:[\\/](?:[^<>:"|?*\r\n]+[\\/]?)*$/;
const UNIX_PATH = /^\/(?:[^<>:"|?*\r\n\0]+\/?)*$/;
const GITHUB_URL = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+?(?:\.git)?\/?$/;

function validate(mode: RepoSource, value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return mode === 'github' ? 'GitHub URL 不能为空' : '本地路径不能为空';
  }
  if (mode === 'github') {
    return GITHUB_URL.test(trimmed)
      ? null
      : '请输入有效的 GitHub 仓库 URL（https://github.com/owner/repo）';
  }
  return WINDOWS_PATH.test(trimmed) || UNIX_PATH.test(trimmed)
    ? null
    : '请输入有效的本地路径（Windows 或 Unix 格式）';
}

export function RepoInput({
  onSubmit,
  disabled = false,
  defaultMode = 'local',
}: RepoInputProps) {
  const [mode, setMode] = useState<RepoSource>(defaultMode);
  const [value, setValue] = useState('');
  const [touched, setTouched] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [selectedModel, setSelectedModel] = useState<LlmModel>('');
  const inputId = useId();
  const forceId = useId();
  const modelId = useId();

  // Fetch the live provider catalog on mount. This is what makes the frontend
  // adapt to OpenAI / DeepSeek / Qwen / Zhipu / Moonshot based on backend .env.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch('/api/models');
        if (!resp.ok) return;
        const data = (await resp.json()) as ProviderCatalog;
        if (cancelled) return;
        setCatalog(data);
        setSelectedModel(data.default_model || data.models[0]?.id || '');
      } catch {
        // ignore — user can still submit, backend will use env default
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const error = useMemo(
    () => (touched ? validate(mode, value) : null),
    [mode, value, touched],
  );

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setTouched(true);
    const err = validate(mode, value);
    if (err) return;
    onSubmit({
      source: mode,
      path: value.trim(),
      force_refresh: forceRefresh,
      // Send undefined (not empty string) so backend uses env default
      model: selectedModel || undefined,
    });
  };

  const switchMode = (next: RepoSource) => {
    setMode(next);
    setTouched(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>仓库分析</CardTitle>
        <CardDescription>支持本地 Git 路径或 GitHub 仓库 URL</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="mb-3 inline-flex rounded-md border border-border p-1"
          role="tablist"
          aria-label="输入模式"
        >
          {(['local', 'github'] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => switchMode(m)}
              className={cn(
                'rounded-sm px-3 py-1 text-sm transition-colors',
                mode === m
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary',
              )}
            >
              {m === 'github' ? 'GitHub URL' : '本地路径'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          <label htmlFor={inputId} className="block text-sm font-medium">
            {mode === 'github' ? '仓库 URL' : '仓库路径'}
          </label>
          <Input
            id={inputId}
            value={value}
            placeholder={
              mode === 'github'
                ? 'https://github.com/owner/repo'
                : 'C:\\path\\to\\repo 或 /home/user/repo'
            }
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => setTouched(true)}
            disabled={disabled}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? `${inputId}-error` : undefined}
          />
          {error && (
            <p id={`${inputId}-error`} className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div>
            <label htmlFor={modelId} className="mb-1 flex items-center justify-between text-xs font-medium">
              <span>主推理模型</span>
              {catalog && (
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase',
                    PROVIDER_BADGES[catalog.provider].color,
                  )}
                >
                  {PROVIDER_BADGES[catalog.provider].label}
                </span>
              )}
            </label>
            <select
              id={modelId}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as LlmModel)}
              disabled={disabled || !catalog}
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
            >
              {!catalog && <option value="">加载中...</option>}
              {catalog?.models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
            {catalog && (
              <p className="mt-1 text-[10px] text-muted-foreground">
                {catalog.models.find((m) => m.id === selectedModel)?.hint}
              </p>
            )}
          </div>

          <div className="flex items-start gap-2">
            <input
              id={forceId}
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
              disabled={disabled}
              className="mt-1 h-4 w-4 rounded border-border"
            />
            <label htmlFor={forceId} className="text-xs text-muted-foreground">
              跳过响应缓存
            </label>
          </div>
          <Button type="submit" disabled={disabled} className="w-full">
            {disabled ? '分析中…' : '开始分析'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
