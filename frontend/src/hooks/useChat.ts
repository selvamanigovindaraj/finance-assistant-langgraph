import { useCallback, useState } from "react";
import type { Message } from "../types";
import { sendMessage } from "../services/api";

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  sessionId: string;
  error: string | null;
  send: (content: string) => Promise<void>;
  clear: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());

  const send = useCallback(
    async (content: string): Promise<void> => {
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };

      // Capture full history including the new user message before any state update
      const historyWithUser = [...messages, userMsg];
      setMessages(historyWithUser);
      setIsLoading(true);
      setError(null);

      try {
        const res = await sendMessage(historyWithUser, sessionId);
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.answer,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setIsLoading(false);
      }
    },
    [messages, sessionId]
  );

  const clear = useCallback((): void => {
    setMessages([]);
    setError(null);
    setSessionId(crypto.randomUUID());
  }, []);

  return { messages, isLoading, sessionId, error, send, clear };
}
