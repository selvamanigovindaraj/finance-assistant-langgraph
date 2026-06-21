import type { ChatSession, FeedbackPayload, Message } from "../types";

const BASE_URL = "/api";

export async function sendMessage(
  _messages: Message[],
  _sessionId: string
): Promise<{ answer: string; sources: unknown[]; sessionId: string }> {
  // TODO: POST /chat
  throw new Error("Not implemented");
}

export async function submitFeedback(_payload: FeedbackPayload): Promise<void> {
  // TODO: POST /feedback
  throw new Error("Not implemented");
}

export async function fetchSessions(): Promise<ChatSession[]> {
  // TODO: GET /sessions
  throw new Error("Not implemented");
}

export { BASE_URL };
