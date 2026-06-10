import { useMemo, useRef } from 'react';
import type { FileHeatmap, Severity } from '@/types/contracts';
import { useEchartsMount } from '@/hooks/useEchartsMount';

export interface HeatmapChartProps {
  fileHeatmap: FileHeatmap;
  onLineClick?: (file: string, line: number) => void;
  /** Optional fixed height; if omitted, height scales with number of files */
  height?: number;
}

const RISK_VALUE: Record<Severity, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const RISK_LABEL: Record<Severity, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '极高',
};

const RISK_COLOR: Record<Severity, string> = {
  low: '#16a34a',
  medium: '#ca8a04',
  high: '#ea580c',
  critical: '#dc2626',
};

type HeatPoint = [number, number, number, string, number, Severity, string];

/** Shorten a file path for y-axis display — keep the last 2 path segments max. */
function shortenPath(path: string, maxLen = 28): string {
  const normalized = path.replace(/\\/g, '/');
  const parts = normalized.split('/');
  let label = parts.length > 2 ? '…/' + parts.slice(-2).join('/') : normalized;
  if (label.length > maxLen) {
    label = '…' + label.slice(-(maxLen - 1));
  }
  return label;
}

/** Compute a readable axis interval for a line-number range so ticks look clean. */
function pickAxisInterval(range: number): number {
  if (range <= 10) return 1;
  if (range <= 50) return 5;
  if (range <= 100) return 10;
  if (range <= 300) return 25;
  if (range <= 600) return 50;
  if (range <= 1500) return 100;
  if (range <= 5000) return 500;
  return 1000;
}

const ROW_HEIGHT = 28; // px per file row — keeps labels readable
const MIN_CHART_HEIGHT = 200;
const VIEWPORT_MAX_HEIGHT = 560; // outer scroll container cap
const TOP_PADDING = 24;
const BOTTOM_PADDING = 56; // space for visualMap + axis name

export function HeatmapChart({
  fileHeatmap,
  onLineClick,
  height,
}: HeatmapChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const { files, displayFiles, minLine, maxLine, data, gridLeft } = useMemo(() => {
    // Sort files by number of risks (desc) so busiest files are on top
    const fileList = Object.keys(fileHeatmap).sort((a, b) => {
      const aLen = fileHeatmap[a]?.length ?? 0;
      const bLen = fileHeatmap[b]?.length ?? 0;
      return bLen - aLen;
    });

    let minL = Number.POSITIVE_INFINITY;
    let maxL = 0;
    const points: HeatPoint[] = [];

    fileList.forEach((file, fileIdx) => {
      for (const risk of fileHeatmap[file] ?? []) {
        if (risk.line < minL) minL = risk.line;
        if (risk.line > maxL) maxL = risk.line;
        points.push([
          risk.line,
          fileIdx,
          RISK_VALUE[risk.risk_level],
          file,
          risk.line,
          risk.risk_level,
          risk.reason,
        ]);
      }
    });

    if (!Number.isFinite(minL)) minL = 0;
    if (maxL === 0) maxL = 1;

    const display = fileList.map((f) => shortenPath(f));
    // Dynamic left padding: ~7px per char, capped
    const longestLabelLen = display.reduce((m, s) => Math.max(m, s.length), 0);
    const left = Math.min(220, Math.max(96, longestLabelLen * 7 + 16));

    return {
      files: fileList,
      displayFiles: display,
      minLine: minL,
      maxLine: maxL,
      data: points,
      gridLeft: left,
    };
  }, [fileHeatmap]);

  // Chart height grows linearly with file count — NO hard cap.
  // The parent <div> wraps it in an overflow-y-auto scroll container so
  // users can scroll through large repos without squishing rows.
  const chartHeight = useMemo(() => {
    if (height) return height;
    const h = files.length * ROW_HEIGHT + TOP_PADDING + BOTTOM_PADDING;
    return Math.max(MIN_CHART_HEIGHT, h);
  }, [files.length, height]);

  // When chart exceeds viewport cap, enable scroll. Otherwise let it fit naturally.
  const needsScroll = chartHeight > VIEWPORT_MAX_HEIGHT;

  const option = useMemo(() => {
    // Pad the x-axis range by ~5% so endpoint markers aren't clipped
    const range = Math.max(1, maxLine - minLine);
    const pad = Math.max(1, Math.round(range * 0.05));
    const xMin = Math.max(0, minLine - pad);
    const xMax = maxLine + pad;
    const interval = pickAxisInterval(xMax - xMin);

    // Dot size scales down as data gets denser
    const symbolSize = Math.max(8, Math.min(16, 800 / Math.max(1, data.length)));

    return {
      tooltip: {
        position: 'top',
        formatter: (params: { data?: unknown }) => {
          const d = params.data as HeatPoint | undefined;
          if (!Array.isArray(d) || d.length < 7) return '';
          const [, , , file, line, level, reason] = d;
          return `<div style="font-size:12px"><b>${file}:${line}</b><br/>风险: ${RISK_LABEL[level]}<br/>${reason}</div>`;
        },
      },
      grid: { left: gridLeft, right: 24, top: TOP_PADDING, bottom: BOTTOM_PADDING },
      xAxis: {
        type: 'value',
        name: '行号',
        nameLocation: 'middle',
        nameGap: 26,
        min: xMin,
        max: xMax,
        interval,
        minorTick: { show: true, splitNumber: 5 },
        minorSplitLine: { show: true, lineStyle: { color: '#f1f5f9' } },
        axisLabel: { fontSize: 11, formatter: (v: number) => `${v}` },
      },
      yAxis: {
        type: 'category',
        data: displayFiles,
        axisLabel: {
          fontSize: 11,
          width: gridLeft - 12,
          overflow: 'truncate',
        },
      },
      visualMap: {
        min: 1,
        max: 4,
        dimension: 2, // ← 映射第三维（风险值 1-4），而不是默认的 x 轴行号
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemWidth: 14,
        itemHeight: 10,
        text: ['极高', '低'],
        textStyle: { fontSize: 11 },
        inRange: {
          color: ['#86efac', '#fde047', '#fb923c', '#ef4444'],
        },
      },
      series: [
        {
          type: 'scatter',
          symbolSize,
          data,
          label: {
            // Only show inline labels when density is low enough to avoid clutter.
            // When hidden, users still see full info on hover via tooltip.
            show: data.length <= 15,
            position: 'top',
            distance: 4,
            fontSize: 10,
            formatter: (p: { data?: unknown }) => {
              const d = p.data as HeatPoint | undefined;
              if (!Array.isArray(d) || d.length < 6) return '';
              // Short label — x-axis already shows line numbers; keep it minimal.
              return `L${d[4]}`;
            },
            color: (p: { data?: unknown }) => {
              const d = p.data as HeatPoint | undefined;
              if (!Array.isArray(d) || d.length < 6) return '#475569';
              return RISK_COLOR[d[5]];
            },
          },
          labelLayout: {
            // Force-hide any label whose bounding box overlaps a neighbor's.
            hideOverlap: true,
          },
          emphasis: {
            focus: 'series',
            label: {
              show: true,
              fontWeight: 'bold',
              formatter: (p: { data?: unknown }) => {
                const d = p.data as HeatPoint | undefined;
                if (!Array.isArray(d) || d.length < 6) return '';
                return `${RISK_LABEL[d[5]]}·L${d[4]}`;
              },
            },
          },
        },
      ],
    };
  }, [displayFiles, minLine, maxLine, data, gridLeft]);

  useEchartsMount(containerRef, {
    option,
    onReady: (chart) => {
      if (!onLineClick) return;
      chart.on('click', (params) => {
        const point = params.data as HeatPoint | undefined;
        if (Array.isArray(point) && point.length >= 5) {
          onLineClick(point[3], point[4]);
        }
      });
    },
    deps: [files.join('|'), minLine, maxLine, data.length, gridLeft, chartHeight, onLineClick],
  });

  if (files.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        暂无热力图数据
      </div>
    );
  }

  if (needsScroll) {
    return (
      <div className="relative">
        <div
          className="overflow-y-auto rounded-md border border-border"
          style={{ maxHeight: VIEWPORT_MAX_HEIGHT }}
        >
          <div ref={containerRef} style={{ width: '100%', height: chartHeight }} />
        </div>
        <p className="mt-1 text-[11px] text-muted-foreground">
          共 {files.length} 个高风险文件 · 向下滚动查看全部
        </p>
      </div>
    );
  }

  return <div ref={containerRef} style={{ width: '100%', height: chartHeight }} />;
}
