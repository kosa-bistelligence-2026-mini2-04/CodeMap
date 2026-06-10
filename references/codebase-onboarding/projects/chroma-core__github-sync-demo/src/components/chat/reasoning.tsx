"use client";

import { memo } from "react";
import { useWindows } from "@/contexts/window-context";
import { VimWindow } from "@/components/windows/vim-window";

function wrapText(text: string, maxWidth: number): string {
  const lines: string[] = [];
  const paragraphs = text.split("\n");

  for (const paragraph of paragraphs) {
    if (paragraph.length <= maxWidth) {
      lines.push(paragraph);
      continue;
    }

    const words = paragraph.split(" ");
    let currentLine = "";

    for (const word of words) {
      if (currentLine.length === 0) {
        currentLine = word;
      } else if (currentLine.length + 1 + word.length <= maxWidth) {
        currentLine += " " + word;
      } else {
        lines.push(currentLine);
        currentLine = word;
      }
    }

    if (currentLine.length > 0) {
      lines.push(currentLine);
    }
  }

  return lines.join("\n");
}

export type ReasoningProps = {
  children: string;
  isStreaming?: boolean;
};

export const Reasoning = memo(
  ({ children, isStreaming = false }: ReasoningProps) => {
    const { openWindow } = useWindows();

    const isEmpty = !children || children.trim().length === 0;
    const showPlaceholder = isEmpty && isStreaming;
    const firstLine = children.split("\n")[0] || "";
    const truncated = showPlaceholder
      ? "Thinking..."
      : firstLine.length > 80
        ? firstLine.slice(0, 80) + "..."
        : firstLine;

    const handleClick = () => {
      const wrappedContent = wrapText(children, 60);

      openWindow({
        title: "Reasoning",
        content: <VimWindow initialBuffer={wrappedContent} />,
        x: 500,
        y: 100,
        width: 500,
        height: 400,
        isMinimized: false,
        isMaximized: false,
      });
    };

    if (isEmpty && !isStreaming) {
      return null;
    }

    return (
      <p
        className={`text-muted-foreground text-lg truncate ${showPlaceholder ? "" : "cursor-pointer hover:underline"}`}
        onClick={showPlaceholder ? undefined : handleClick}
      >
        {truncated}
      </p>
    );
  },
);

Reasoning.displayName = "Reasoning";
