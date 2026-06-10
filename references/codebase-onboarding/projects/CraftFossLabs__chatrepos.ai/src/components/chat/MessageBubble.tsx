import React from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { ChatMessage } from "@/lib/gemini/gemini-service";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import { CopyIcon, CheckIcon } from "@radix-ui/react-icons";
import { Button } from "@/components/ui/button";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        "flex w-full gap-3 p-4",
        message.role === "user" ? "justify-end" : "justify-start"
      )}
    >
      {message.role === "assistant" && (
        <Avatar className="h-8 w-8 bg-gray-100">
          <AvatarImage src="/gitreposlogo-g.svg" alt="AI Assistant" />
          <AvatarFallback>AI</AvatarFallback>
        </Avatar>
      )}

      <Card
        className={cn(
          "max-w-[80%] p-4",
          message.role === "user"
            ? "bg-gray-50 text-primary-foreground"
            : "bg-muted"
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="markdown-content prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>

          {message.role === "assistant" && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0 text-muted-foreground"
              onClick={copyToClipboard}
              title="Copy to clipboard"
            >
              {copied ? (
                <CheckIcon className="h-4 w-4" />
              ) : (
                <CopyIcon className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </Card>

      {message.role === "user" && (
        <Avatar className="h-8 w-8">
          <AvatarImage src="/user-avatar.svg" alt="User" />
          <AvatarFallback>U</AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
