"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Maximize2, Minimize2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
  fontFamily: "Inter, sans-serif",
});

interface MermaidViewerProps {
  chart: string;
}

export function MermaidViewer({ chart }: MermaidViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    let isMounted = true;
    
    // Guard: chart must be non-empty and contain a newline (multi-line diagram)
    if (!chart || chart.trim().length < 10) return;

    const renderChart = async () => {
      try {
        setError(null);
        // Generate a unique ID for the svg to avoid collisions
        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, chart);
        
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Mermaid parsing error:", err);
          setError("Failed to render diagram. Syntax error in Mermaid code.");
        }
      }
    };

    if (chart) {
      renderChart();
    }

    return () => {
      isMounted = false;
    };
  }, [chart]);

  if (error) {
    return (
      <div className="p-4 my-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-mono">
        {error}
        <pre className="mt-2 text-xs opacity-70 whitespace-pre-wrap">{chart}</pre>
      </div>
    );
  }

  if (!svgContent) {
    return (
      <div className="flex items-center justify-center p-8 my-2 rounded-xl bg-zinc-900 border border-zinc-800">
        <div className="w-5 h-5 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <>
      {/* Inline Viewer */}
      <div className="relative my-4 group">
        <div
          ref={containerRef}
          className="overflow-auto p-6 rounded-xl bg-zinc-900/50 border border-zinc-800 flex justify-center items-center mermaid-container"
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
        <button
          onClick={() => setIsExpanded(true)}
          className="absolute top-2 right-2 p-1.5 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-white"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Expanded Modal */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8 bg-black/80 backdrop-blur-sm"
            onClick={() => setIsExpanded(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-5xl max-h-full flex flex-col bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
                <h3 className="text-sm font-medium text-zinc-300">Architecture Diagram</h3>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                >
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
              <div
                className="flex-1 overflow-auto p-8 flex justify-center items-center min-h-[50vh] mermaid-container"
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
