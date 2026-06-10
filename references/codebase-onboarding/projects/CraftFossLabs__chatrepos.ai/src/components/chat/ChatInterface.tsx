import React, { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { useAnalysisStore } from "@/lib/store";
import { toast } from "sonner";

export function ChatInterface() {
  const { 
    messages, 
    addMessage, 
    isAnalysisComplete,
  } = useAnalysisStore();
  
  const [isLoading, setIsLoading] = React.useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // We've removed the automatic welcome message to prevent duplication
  // The welcome message will be sent from the server when needed

  const handleSendMessage = async (content: string) => {
    // Add user message to chat
    const userMessage = { role: "user" as const, content };
    addMessage(userMessage);
    
    setIsLoading(true);
    
    try {
      // Send message to API
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [...messages, userMessage],
        }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to get response");
      }
      
      const data = await response.json();
      
      // Add AI response to chat
      addMessage(data.message);
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to get a response. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages container - no scroll here as parent will scroll */}
      <div className="flex-1 p-4 pb-2">
        {messages.length > 0 ? (
          <div className="space-y-4">
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}
            {isLoading && <ThinkingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-center text-muted-foreground">
              {isAnalysisComplete 
                ? "Analysis complete! Ask me questions about the repository." 
                : "Submit a GitHub repository URL to start the analysis."}
            </p>
          </div>
        )}
      </div>
      
      {/* Fixed chat input at bottom */}
      <div className="p-3 bg-background">
        <ChatInput 
          onSendMessage={handleSendMessage} 
          isLoading={isLoading}
          placeholder={isAnalysisComplete 
            ? "Ask a question about this repository..." 
            : "Analysis in progress..."}
        />
      </div>
    </div>
  );
}
