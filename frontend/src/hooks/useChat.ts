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

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        const res = await sendMessage([userMsg], sessionId);
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.answer,
          disclaimer: res.disclaimer || undefined,
          tool_used: res.tool_used ?? undefined,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  const clear = useCallback((): void => {
    setMessages([]);
    setError(null);
    setSessionId(crypto.randomUUID());
  }, []);

  return { messages, isLoading, sessionId, error, send, clear };
}
