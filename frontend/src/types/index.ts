export type Role = "user" | "assistant" | "system";

export interface Message {
  id: string;
  role: Role;
  content: string;
  sources?: Source[];
  disclaimer?: string;
  tool_used?: string;
  timestamp: string;
}

export interface Source {
  title: string;
  url?: string;
  snippet: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
}

export interface FeedbackPayload {
  sessionId: string;
  messageId: string;
  rating: -1 | 0 | 1;
  comment?: string;
}

export interface ApiError {
  detail: string;
  status: number;
}
