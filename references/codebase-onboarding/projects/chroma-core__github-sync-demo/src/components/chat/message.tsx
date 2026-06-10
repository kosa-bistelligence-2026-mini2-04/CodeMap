import { ReactNode, useState, useEffect } from "react";
import { UIDataTypes, UIMessage, UIMessagePart, UITools } from "ai";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

import { CodeBlock } from "@/components/chat/code-block";
import { Reasoning } from "./reasoning";
import { MemoizedMarkdown } from "@/components/chat/memoized-markdown";
import { useWindows } from "@/contexts/window-context";
import { SearchResultWindow } from "@/components/windows/search-result-window";
import { VimWindow } from "@/components/windows/vim-window";
import { AnimatedEllipsis } from "@/components/shared/misc";

export interface MessageProps {
  message: UIMessage;
}

function AnimatedNumber({ value }: { value: number }) {
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (v) => Math.round(v));
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 0.3,
      ease: "easeOut",
    });
    return controls.stop;
  }, [motionValue, value]);

  useEffect(() => {
    return rounded.on("change", (v) => setDisplay(v));
  }, [rounded]);

  return <span>{display}</span>;
}

function formatParameterValue(value: any): string {
  if (typeof value === "string") {
    return `"${value}"`;
  }
  if (Array.isArray(value)) {
    return JSON.stringify(value);
  }
  return String(value);
}

export function Message({ message }: MessageProps): ReactNode {
  const { role } = message;

  if (role === "user") {
    return <UserMessage message={message} />;
  }

  if (role === "assistant") {
    return <AssistantMessage message={message} />;
  }

  return null;
}

function UserMessage({ message }: { message: UIMessage }) {
  return (
    <div className="min-w-[4ch] py-2 px-3 rounded-md bg-secondary border-[.1px] border-border mt-8">
      {message.parts.map((part, index) =>
        part.type === "text" ? (
          <MemoizedMarkdown
            key={`${message.id}-${index}`}
            id={`${message.id}-${index}`}
            content={part.text}
          />
        ) : null,
      )}
    </div>
  );
}

function AssistantMessage({ message }: { message: UIMessage }) {
  return (
    <div className="w-full px-3 font-serif text-lg">
      <MessageContent parts={message.parts} />
    </div>
  );
}

function MessageContent({
  parts,
}: {
  parts: UIMessagePart<UIDataTypes, UITools>[];
}) {
  return (
    <>
      {parts.map((part, index) => {
        if (part.type === "step-start") {
          return null;
        }

        if (typeof part.type === "string" && part.type.startsWith("tool-")) {
          return <ToolInvocation key={index} part={part} />;
        }

        switch (part.type) {
          case "text":
            return (
              <MemoizedMarkdown
                key={index}
                id={`content-${index}`}
                content={part.text}
              />
            );
          case "reasoning":
            return (
              <Reasoning key={index} isStreaming={part.state !== "done"}>
                {part.text}
              </Reasoning>
            );
          case "dynamic-tool":
            return <ToolInvocation key={index} part={part} />;
          case "tool-formatCode":
            const { language, code } =
              "input" in part
                ? (part.input as { language: string; code: string })
                : { language: "", code: "" };
            return <CodeBlock key={index} code={code} language={language} />;
          default:
            return null;
        }
      })}
    </>
  );
}

function ToolInvocation({
  part,
}: {
  part: UIMessagePart<UIDataTypes, UITools>;
}) {
  const partAny = part as any;
  const toolName =
    typeof part.type === "string" && part.type.startsWith("tool-")
      ? part.type.replace("tool-", "")
      : partAny.toolName || "unknown";
  const input = partAny.input;
  const output = partAny.output;
  const toolCallId = partAny.toolCallId;
  const state = partAny.state;

  const isLoading = !output || state !== "output-available";

  return (
    <div key={toolCallId} className="mb-2">
      {input && (
        <div className="font-mono text-sm flex flex-row items-center max-w-full">
          <div className="font-medium shrink-0">{toolName}</div>
          <div className="shrink-0">{"("}</div>
          <ToolCallParameters input={input} />
          <div className="shrink-0">{")"}</div>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-row gap-[1ch] font-mono text-sm">
          <span>⎿</span>
          <span>
            loading
            <AnimatedEllipsis />
          </span>
        </div>
      ) : (
        <ToolOutput toolName={toolName} output={output} />
      )}
    </div>
  );
}

function ToolCallParameters({ input }: { input: Record<string, any> }) {
  if (!input || typeof input !== "object") {
    return null;
  }

  const params = Object.entries(input);

  if (params.length === 0) {
    return null;
  }

  return (
    <div className="font-mono text-sm overflow-hidden text-ellipsis whitespace-nowrap min-w-0">
      {params.map(([key, value], index) => (
        <span key={key}>
          {formatParameterValue(value)}
          {index < params.length - 1 && ", "}
        </span>
      ))}
    </div>
  );
}

function ToolOutput({ toolName, output }: { toolName: string; output: any }) {
  switch (toolName) {
    case "search":
      return <SearchOutput output={output} />;
    case "grep":
      return <GrepOutput output={output} />;
    case "cat":
      return <CatOutput output={output} />;
    default:
      return (
        <div className="flex flex-row gap-[1ch] font-mono text-sm">
          <span>⎿</span>
          <span className="text-zinc-500">done</span>
        </div>
      );
  }
}

function SearchOutput({ output }: { output: any }) {
  const { openWindow } = useWindows();
  const [expanded, setExpanded] = useState(false);

  const results = output?.results;
  if (!results?.length) {
    return (
      <div className="flex flex-row gap-[1ch] font-mono text-sm">
        <span>⎿</span>
        <span className="text-zinc-500">no results</span>
      </div>
    );
  }

  const handleResultClick = (result: any, index: number) => {
    const fileName =
      (result.path || "unknown").split("/").pop() || "Unknown File";

    openWindow({
      title: fileName,
      content: (
        <SearchResultWindow
          result={{
            path: result.path || "unknown",
            content: result.content || "",
            relevanceScore: result.relevanceScore,
          }}
        />
      ),
      width: 600,
      height: 500,
      isMinimized: false,
      isMaximized: false,
    });
  };

  if (!expanded) {
    return (
      <div className="flex flex-row gap-[1ch] font-mono text-sm">
        <span>⎿</span>
        <span
          className="cursor-pointer hover:underline"
          onClick={() => setExpanded(true)}
        >
          found <AnimatedNumber value={results.length} />{" "}
          {results.length === 1 ? "result" : "results"}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-row gap-[1ch] font-mono text-sm max-w-full">
      <span className="shrink-0">⎿</span>
      <div className="flex-1 min-w-0">
        {results.map((result: any, index: number) => (
          <motion.div
            key={index}
            className="truncate w-full cursor-pointer hover:underline"
            onClick={() => handleResultClick(result, index)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.03, duration: 0.01 }}
          >
            {result.path || "unknown"}
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function GrepOutput({ output }: { output: any }) {
  const { openWindow } = useWindows();

  const matchCount = output?.matchCount ?? 0;
  const fileCount = output?.fileCount ?? 0;
  const grepOutput = output?.output ?? "";

  const handleClick = () => {
    if (matchCount === 0) return;

    openWindow({
      title: `grep results (${matchCount} matches)`,
      content: <VimWindow initialBuffer={grepOutput} />,
      width: 700,
      height: 500,
      isMinimized: false,
      isMaximized: false,
    });
  };

  if (matchCount === 0) {
    return (
      <div className="flex flex-row gap-[1ch] font-mono text-sm">
        <span>⎿</span>
        <span className="text-zinc-500">no matches</span>
      </div>
    );
  }

  return (
    <div className="flex flex-row gap-[1ch] font-mono text-sm">
      <span>⎿</span>
      <span className="cursor-pointer hover:underline" onClick={handleClick}>
        found <AnimatedNumber value={matchCount} />{" "}
        {matchCount === 1 ? "match" : "matches"} in{" "}
        <AnimatedNumber value={fileCount} />{" "}
        {fileCount === 1 ? "file" : "files"}
      </span>
    </div>
  );
}

function CatOutput({ output }: { output: any }) {
  const { openWindow } = useWindows();

  const hasError = !!output?.error;
  const path = output?.path ?? "";
  const content = output?.content ?? "";

  const handleClick = () => {
    if (hasError) return;

    const fileName = path.split("/").pop() || "file";

    openWindow({
      title: fileName,
      content: <VimWindow initialBuffer={content} />,
      width: 700,
      height: 500,
      isMinimized: false,
      isMaximized: false,
    });
  };

  if (hasError) {
    return (
      <div className="flex flex-row gap-[1ch] font-mono text-sm">
        <span>⎿</span>
        <span className="text-zinc-500">file not found ✖︎</span>
      </div>
    );
  }

  return (
    <div className="flex flex-row gap-[1ch] font-mono text-sm">
      <span>⎿</span>
      <span className="cursor-pointer hover:underline" onClick={handleClick}>
        read file ✔︎
      </span>
    </div>
  );
}
