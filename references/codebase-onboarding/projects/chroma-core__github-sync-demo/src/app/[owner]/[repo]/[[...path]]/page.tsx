"use client";

import { useChat } from "@ai-sdk/react";
import { useQuery } from "@tanstack/react-query";
import { DefaultChatTransport } from "ai";
import { motion } from "framer-motion";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChatInput } from "@/components/chat/chat-input";
import { CommitLink } from "@/components/chat/commit-link";
import { Message } from "@/components/chat/message";
import { RepoTree } from "@/components/chat/repo-tree";
import { useScrollToBottom } from "@/components/chat/use-scroll-to-bottom";
import { AnimatedEllipsis, Spinner } from "@/components/shared/misc";
import type { ErrorResponse, StatusResponse } from "@/types/api";

const POLLING_INTERVAL_MS = 1000;
const LARGE_REPO_SIZE_BYTES = 500 * 1024 * 1024;

async function fetchRepoStatus(
  owner: string,
  repo: string,
): Promise<StatusResponse> {
  const response = await fetch(`/api/repos/${owner}/${repo}/status`);
  const data: StatusResponse | ErrorResponse = await response.json();

  if (!response.ok || "error" in data) {
    throw new Error(
      (data as ErrorResponse).error || "Failed to check repository",
    );
  }

  if (!data.exists) {
    throw new Error("Repository not found");
  }

  if (data.is_private) {
    throw new Error("Private repositories are not supported");
  }

  if (data.sync_status === "failed") {
    throw new Error("Sync failed. Please try again.");
  }

  return data;
}

export default function ChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const owner = params.owner as string;
  const repo = params.repo as string;
  const queryParam = searchParams.get("q");

  const initialQuerySent = useRef(false);

  const { data: repoInfo, error: queryError } = useQuery({
    queryKey: ["repoStatus", owner, repo],
    queryFn: () => fetchRepoStatus(owner, repo),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return POLLING_INTERVAL_MS;
      if (data.sync_status === "up_to_date") return false;
      return POLLING_INTERVAL_MS;
    },
    retry: false,
  });

  const syncStatus = repoInfo?.sync_status ?? null;
  const chatEnabled =
    syncStatus === "up_to_date" || syncStatus === "out_of_date";
  const error = queryError?.message ?? "";

  const {
    messages,
    sendMessage,
    status,
    error: chatError,
  } = useChat({
    transport: new DefaultChatTransport({
      api: `/api/repos/${owner}/${repo}/chat`,
    }),
  });

  const [input, setInput] = useState<string>("");
  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>();

  useEffect(() => {
    if (queryParam && !initialQuerySent.current && input === "") {
      setInput(queryParam);
    }
  }, [queryParam, input]);

  const onSubmit = useMemo(
    () => async (inputValue: string) => {
      if (!chatEnabled) return;
      sendMessage({
        text: inputValue,
      });
      setInput("");
    },
    [sendMessage, chatEnabled],
  );

  useEffect(() => {
    if (chatEnabled && queryParam && !initialQuerySent.current) {
      initialQuerySent.current = true;
      onSubmit(queryParam);
    }
  }, [chatEnabled, queryParam, onSubmit]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-white px-4">
        <div className="max-w-md text-center">
          <h2 className="text-2xl font-semibold text-red-600 mb-4">Error</h2>
          <p className="text-zinc-600 mb-6">{error}</p>
          <a
            href="/"
            className="px-6 py-2 text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
          >
            Go Back
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-dvh bg-white">
      <a
        href="/"
        className="absolute top-2 md:top-6 left-4 text-zinc-500 hover:underline font-mono text-sm"
      >
        ↩ home
      </a>
      <div className="flex-1 overflow-y-scroll">
        <div ref={messagesContainerRef} className="py-8">
          <div className="w-full max-w-xl flex flex-col items-start gap-[1em] mx-auto px-4">
            <div className="flex flex-col w-full font-mono text-sm leading-relaxed">
              <div className="whitespace-pre font-bold">
                <a
                  href={
                    repoInfo?.repo_info?.htmlUrl ||
                    `https://github.com/${owner}/${repo}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  {repoInfo?.repo_info?.fullName || `${owner}/${repo}`}
                </a>
              </div>
              {!repoInfo?.repo_info ||
              (repoInfo.repo_info &&
                !repoInfo.repo_info.stargazersCount &&
                !repoInfo.latest_commit &&
                !repoInfo.repo_info.description) ? (
                <div className="flex items-center gap-2 text-zinc-500 whitespace-pre">
                  <Spinner />
                  <span>loading repo</span>
                </div>
              ) : (
                <>
                  <div className="whitespace-pre">
                    {repoInfo.repo_info.stargazersCount.toLocaleString()} stars
                    {repoInfo.latest_commit &&
                    (syncStatus === "up_to_date" ||
                      syncStatus === "out_of_date") ? (
                      <>
                        {" | "}
                        {syncStatus === "up_to_date" ? (
                          <CommitLink commit={repoInfo.latest_commit} />
                        ) : (
                          <>
                            {repoInfo.latest_processed_commit ? (
                              <>
                                <CommitLink
                                  commit={repoInfo.latest_processed_commit}
                                />
                                {" → "}
                                <CommitLink commit={repoInfo.latest_commit} />
                                {" (updating)"}
                              </>
                            ) : (
                              <CommitLink commit={repoInfo.latest_commit} />
                            )}
                          </>
                        )}
                      </>
                    ) : (
                      ""
                    )}
                  </div>
                  {repoInfo.repo_info.description && (
                    <div>{repoInfo.repo_info.description}</div>
                  )}
                </>
              )}
            </div>
            {repoInfo?.repo_info && !repoInfo?.tree ? (
              <div className="flex items-center gap-2 text-sm font-mono text-zinc-500">
                <Spinner />
                <span>loading files</span>
              </div>
            ) : repoInfo?.tree && repoInfo.latest_commit ? (
              <>
                <RepoTree
                  tree={repoInfo.tree}
                  repoUrl={
                    repoInfo.repo_info?.htmlUrl ||
                    `https://github.com/${owner}/${repo}`
                  }
                  commitSha={repoInfo.latest_commit.sha}
                  className="w-full"
                  autoScroll={syncStatus === "processing"}
                  scrollSpeed={10}
                />
                <span className="text-sm font-mono text-zinc-500">
                  {syncStatus === "processing" ? (
                    <>
                      syncing...
                      {repoInfo.tree.reduce(
                        (sum, entry) => sum + (entry.size || 0),
                        0,
                      ) > LARGE_REPO_SIZE_BYTES && (
                        <span className="text-zinc-400">
                          {" "}
                          (large repo, this might take a while)
                        </span>
                      )}
                    </>
                  ) : (
                    "✔︎ synced"
                  )}
                </span>
              </>
            ) : null}
            {messages.length === 0 && chatEnabled && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full"
              >
                <div className="rounded-lg p-6 bg-zinc-50">
                  <h2 className="font-medium mb-2">
                    Ready to chat with {owner}/{repo}
                  </h2>
                  <p className="text-zinc-600">
                    Ask questions about the codebase, architecture, or specific
                    features.
                  </p>
                </div>
              </motion.div>
            )}
            {messages.map((message) => (
              <Message key={message.id} message={message} />
            ))}
            {status === "submitted" && (
              <div className="text-gray-500 font-serif px-3 text-lg">
                Thinking
                <AnimatedEllipsis />
              </div>
            )}
            {status === "error" && chatError && (
              <div className="text-red-500">Error: {chatError?.message}</div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      <div className="pb-4 px-4">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            input={input}
            setInput={setInput}
            onSubmit={onSubmit}
            disabled={!chatEnabled}
          />
        </div>
      </div>
    </div>
  );
}
