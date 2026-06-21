import type { JSX } from "react";
import { InputBar } from "./InputBar";
import { MessageBubble } from "./MessageBubble";
import { useChat } from "../hooks/useChat";

export function ChatWindow(): JSX.Element {
  // TODO: implement scroll-to-bottom, streaming, empty state
  const { messages, isLoading, send } = useChat();

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
      </div>
      <InputBar onSend={send} isLoading={isLoading} />
    </div>
  );
}
