"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import type { GitHubTree } from "@/types/github";
import { cn } from "@/lib/utils";

interface RepoTreeProps {
  tree: GitHubTree["tree"];
  repoUrl: string;
  commitSha: string;
  className?: string;
  previewLineCount?: number;
  autoScroll?: boolean;
  scrollSpeed?: number;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)}${sizes[i]}`;
}

export function RepoTree({
  tree,
  repoUrl,
  commitSha,
  className,
  previewLineCount = 6,
  autoScroll = false,
  scrollSpeed = 300,
}: RepoTreeProps) {
  const filePaths = useMemo(() => {
    return tree
      .filter((entry) => entry.type === "blob")
      .map((entry) => ({
        path: entry.path,
        size: entry.size ? formatFileSize(entry.size) : undefined,
        url: `${repoUrl}/blob/${commitSha}/${entry.path}`,
      }))
      .sort((a, b) => a.path.localeCompare(b.path));
  }, [tree, repoUrl, commitSha]);

  const totalLines = filePaths.length;
  const [lineOffset, setLineOffset] = useState(0);
  const treeRef = useRef<HTMLDivElement>(null);
  const scrollAccumulatorRef = useRef(0);
  const autoScrollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const userInteractedRef = useRef(false);

  const hasMoreAbove = lineOffset > 0;
  const defaultLinesToShow = previewLineCount;

  const wouldHaveMoreBelow = lineOffset + defaultLinesToShow < totalLines;
  const linesToShow =
    hasMoreAbove && wouldHaveMoreBelow
      ? previewLineCount - 1
      : previewLineCount;

  const hasMoreBelow = lineOffset + linesToShow < totalLines;

  const maxOffset = Math.max(0, totalLines - linesToShow);
  const clampedOffset = Math.min(lineOffset, maxOffset);
  const visibleLines = filePaths.slice(
    clampedOffset,
    clampedOffset + linesToShow,
  );

  useEffect(() => {
    if (
      !autoScroll ||
      userInteractedRef.current ||
      totalLines === 0 ||
      totalLines < 2 * previewLineCount
    ) {
      if (autoScrollIntervalRef.current) {
        clearInterval(autoScrollIntervalRef.current);
        autoScrollIntervalRef.current = null;
      }
      if (!autoScroll) {
        userInteractedRef.current = false;
      }
      return;
    }

    const baseSpeed = scrollSpeed;
    const minSpeed = 50;
    const speedFactor = Math.max(minSpeed, baseSpeed - totalLines * 2);

    autoScrollIntervalRef.current = setInterval(() => {
      setLineOffset((prev) => (prev + 1) % totalLines);
    }, speedFactor);

    return () => {
      if (autoScrollIntervalRef.current) {
        clearInterval(autoScrollIntervalRef.current);
        autoScrollIntervalRef.current = null;
      }
    };
  }, [autoScroll, totalLines, scrollSpeed]);

  useEffect(() => {
    const treeElement = treeRef.current;
    if (!treeElement) return;

    const handleWheel = (e: WheelEvent) => {
      if (autoScroll && !userInteractedRef.current) {
        userInteractedRef.current = true;
        if (autoScrollIntervalRef.current) {
          clearInterval(autoScrollIntervalRef.current);
          autoScrollIntervalRef.current = null;
        }
      }

      e.preventDefault();

      const scrollDelta = e.deltaY;
      scrollAccumulatorRef.current += scrollDelta;

      const lineHeight = 24;
      const linesToMove = Math.floor(
        Math.abs(scrollAccumulatorRef.current) / lineHeight,
      );

      if (linesToMove > 0) {
        const direction = scrollAccumulatorRef.current > 0 ? 1 : -1;

        setLineOffset((prev) => {
          const newOffset = prev + direction * linesToMove;
          const totalLinesCount = totalLines;

          const willHaveMoreAbove = newOffset > 0;
          const willHaveMoreBelow =
            newOffset + defaultLinesToShow < totalLinesCount;
          const willShowBothIndicators = willHaveMoreAbove && willHaveMoreBelow;
          const effectiveLinesToShow = willShowBothIndicators
            ? previewLineCount - 1
            : previewLineCount;

          const maxOffset = Math.max(0, totalLinesCount - effectiveLinesToShow);
          const clampedOffset = Math.max(0, Math.min(newOffset, maxOffset));

          scrollAccumulatorRef.current =
            scrollAccumulatorRef.current % lineHeight;

          return clampedOffset;
        });
      }
    };

    treeElement.addEventListener("wheel", handleWheel, { passive: false });
    return () => treeElement.removeEventListener("wheel", handleWheel);
  }, [totalLines, previewLineCount, defaultLinesToShow, autoScroll]);

  return (
    <div ref={treeRef} className={cn(className)}>
      <div className="font-mono text-sm leading-relaxed">
        {hasMoreAbove && <div className="whitespace-pre">...</div>}
        {visibleLines.map((item, index) => {
          const actualIndex = clampedOffset + index;
          const isLastInList = actualIndex === totalLines - 1;
          const prefix = isLastInList ? "└── " : "├── ";

          return (
            <div key={actualIndex} className="flex items-center whitespace-pre">
              <span className="whitespace-pre">{prefix}</span>
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="truncate hover:underline"
              >
                {item.path}
              </a>
              {item.size && (
                <span className="text-right ml-auto pl-2">({item.size})</span>
              )}
            </div>
          );
        })}
        {hasMoreBelow && <div className="whitespace-pre">...</div>}
      </div>
    </div>
  );
}
