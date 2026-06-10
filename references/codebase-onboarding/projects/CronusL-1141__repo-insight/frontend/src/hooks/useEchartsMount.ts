import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

type EChartInstance = {
  setOption: (option: unknown) => void;
  dispose: () => void;
  resize: () => void;
  on: (event: string, handler: (params: { data?: unknown }) => void) => void;
};

type EChartsModule = {
  init: (el: HTMLElement) => EChartInstance;
};

export interface UseEchartsMountOptions {
  option: unknown;
  onReady?: (chart: EChartInstance) => void;
  deps?: unknown[];
}

export function useEchartsMount<T extends HTMLElement>(
  containerRef: RefObject<T>,
  { option, onReady, deps = [] }: UseEchartsMountOptions,
) {
  const chartRef = useRef<EChartInstance | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let disposed = false;
    let ro: ResizeObserver | null = null;
    let rafId: number | null = null;
    let chart: EChartInstance | null = null;

    const mount = (mod: EChartsModule) => {
      if (disposed || !containerRef.current) return;
      const node = containerRef.current;
      const rect = node.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        rafId = requestAnimationFrame(() => mount(mod));
        return;
      }
      chart = mod.init(node);
      chart.setOption(option);
      chartRef.current = chart;
      onReady?.(chart);
      ro = new ResizeObserver(() => {
        chart?.resize();
      });
      ro.observe(node);
    };

    void import('echarts').then((mod) => {
      if (disposed) return;
      mount(mod as unknown as EChartsModule);
    });

    return () => {
      disposed = true;
      if (rafId !== null) cancelAnimationFrame(rafId);
      ro?.disconnect();
      chart?.dispose();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return chartRef;
}
