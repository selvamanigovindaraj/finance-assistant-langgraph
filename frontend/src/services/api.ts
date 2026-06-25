import type { FeedbackPayload, Message } from "../types";

const BASE_URL = "/api";

export interface ChatApiResponse {
  answer: string;
  disclaimer: string;
  tool_used: string | null;
  session_id: string;
  usage: Record<string, unknown>;
}

export async function sendMessage(
  messages: Message[],
  sessionId: string
): Promise<ChatApiResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      session_id: sessionId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<ChatApiResponse>;
}

export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  const res = await fetch(`${BASE_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Feedback submission failed");
}

export { BASE_URL };
