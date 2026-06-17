export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export async function sendChatMessage(message: string): Promise<ChatMessage> {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content: `TODO: connect AGENT-CHAT API for "${message}".`,
  };
}
