import { NextResponse } from "next/server";
import { GeminiService } from "@/lib/gemini/gemini-service";
import { ChatMessage } from "@/lib/gemini/gemini-service";
import { mcpServer } from "@/lib/gemini/mcp-server";

export async function POST(request: Request) {
  try {
    const { messages } = await request.json();

    // Validate messages array
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: "Invalid request. Messages array is required." },
        { status: 400 }
      );
    }

    // Validate message format
    const isValidMessages = messages.every(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (msg: any) =>
        msg &&
        typeof msg === "object" &&
        (msg.role === "user" || msg.role === "assistant") &&
        typeof msg.content === "string"
    );

    if (!isValidMessages) {
      return NextResponse.json(
        { error: "Invalid message format." },
        { status: 400 }
      );
    }

    // Log detailed information about repository context
    const hasContext = mcpServer.hasContext();
    console.log(`Chat API: Repository context available: ${hasContext}`);
    
    if (hasContext) {
      const context = mcpServer.getContext();
      console.log(`Chat about repository: ${context?.repositoryName}`);
      console.log(`Repository URL: ${context?.repositoryUrl}`);
      
      // Log the first user message to help with debugging
      const firstUserMessage = messages.find((msg: ChatMessage) => msg.role === "user");
      console.log(`User question: ${firstUserMessage?.content}`);
      
      // Log if we have setup instructions
      if (context?.analysisData?.setupInstructions) {
        console.log("Setup instructions are available for this repository");
      }
    } else {
      console.warn("No repository context available. The AI might give generic responses.");
    }
    
    // Process chat with Gemini
    const geminiService = new GeminiService();
    const response = await geminiService.chat(messages as ChatMessage[]);

    // Log a sample of the response for debugging
    console.log(`Chat response (first 100 chars): ${response.substring(0, 100)}...`);
    
    // Create the assistant message
    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: response,
    };
    
    // Store the AI response in chat history if we have repository context
    if (mcpServer.hasContext()) {
      mcpServer.addMessageToHistory(assistantMessage);
      console.log("Stored AI response in chat history");
    }
    
    return NextResponse.json(
      {
        message: assistantMessage,
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("Error processing chat:", error);
    return NextResponse.json(
      { error: "Failed to process chat message." },
      { status: 500 }
    );
  }
}
