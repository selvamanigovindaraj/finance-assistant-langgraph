import { useState } from "react";
import type { Message } from "../types";

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  sessionId: string;
  send: (content: string) => Promise<void>;
  clear: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, _setMessages] = useState<Message[]>([]);
  const [isLoading, _setIsLoading] = useState(false);
  const [sessionId, _setSessionId] = useState("");

  async function send(_content: string): Promise<void> {
    // TODO: implement
    throw new Error("Not implemented");
  }

  function clear(): void {
    // TODO: implement
    throw new Error("Not implemented");
  }

  return { messages, isLoading, sessionId, send, clear };
}
