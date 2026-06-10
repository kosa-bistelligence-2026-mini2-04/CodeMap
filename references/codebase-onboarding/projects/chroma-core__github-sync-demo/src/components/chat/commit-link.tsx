"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import TimeAgo from "javascript-time-ago";
import en from "javascript-time-ago/locale/en";
import type { CommitInfo } from "@/types/api";

TimeAgo.addDefaultLocale(en);
const timeAgo = new TimeAgo("en-US");

function formatCommitDate(date: Date | string | null): string {
  if (!date) return "Unknown date";
  const dateObj = typeof date === "string" ? new Date(date) : date;
  return timeAgo.format(dateObj);
}

export function CommitLink({ commit }: { commit: CommitInfo }) {
  const shortSha = commit.sha.substring(0, 7);
  const messageLines = commit.message.split("\n");
  const firstFiveLines = messageLines.slice(0, 5).join("\n");

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <a
          href={commit.htmlUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          {shortSha}
        </a>
      </TooltipTrigger>
      <TooltipContent
        className="bg-white text-black border border-black rounded-none font-mono max-w-xs text-xs"
        sideOffset={5}
      >
        <div className="flex flex-col gap-1">
          <div className="whitespace-pre-wrap">{firstFiveLines}</div>
          <div className="opacity-70 border-t border-black pt-1 mt-1">
            {commit.authorName || "Unknown author"}
            {commit.authorDate && ` • ${formatCommitDate(commit.authorDate)}`}
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
