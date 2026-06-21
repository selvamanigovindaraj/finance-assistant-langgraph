import { type JSX, useEffect, useRef } from "react";
import { InputBar } from "./InputBar";
import { MessageBubble } from "./MessageBubble";
import type { useChat } from "../hooks/useChat";

interface ChatWindowProps {
  chat: ReturnType<typeof useChat>;
}

const SUGGESTIONS = [
  "What is a P/E ratio and how do I use it?",
  "Explain dollar-cost averaging",
  "How do I evaluate a company's balance sheet?",
  "What's the difference between ETFs and mutual funds?",
];

function TypingIndicator(): JSX.Element {
  return (
    <div className="flex items-start">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-md-full bg-md-primary flex items-center justify-center shadow-md-1 mr-3 mt-0.5">
        <svg className="w-4 h-4 text-md-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
        </svg>
      </div>
      {/* Bubble */}
      <div className="bg-md-surface border border-md-outline-variant px-5 py-4 rounded-[20px] rounded-tl-[4px] shadow-md-1">
        <div className="flex gap-1.5 items-center">
          <span className="w-2 h-2 rounded-full bg-md-primary animate-md-bounce-1" />
          <span className="w-2 h-2 rounded-full bg-md-primary animate-md-bounce-2" />
          <span className="w-2 h-2 rounded-full bg-md-primary animate-md-bounce-3" />
        </div>
      </div>
    </div>
  );
}

export function ChatWindow({ chat }: ChatWindowProps): JSX.Element {
  const { messages, isLoading, error, send } = chat;
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full bg-md-background">

      {/* MD3 Top App Bar */}
      <header className="bg-md-surface border-b border-md-outline-variant px-6 py-4 shadow-md-1 flex items-center gap-4 z-10">
        <div className="flex-1">
          <h1 className="md-title-large text-md-on-surface">Finance Assistant</h1>
          <p className="md-label-medium text-md-on-surface-variant mt-0.5">
            {messages.length > 0
              ? `${messages.length} message${messages.length !== 1 ? "s" : ""} in this session`
              : "Start a new conversation"}
          </p>
        </div>
        {/* Session badge */}
        <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md-full bg-md-secondary-container text-md-on-secondary-container md-label-small">
          <span className="w-1.5 h-1.5 rounded-full bg-[#386A20]" />
          Connected
        </span>
      </header>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">

        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center min-h-full pb-16 text-center">
            {/* Hero icon — MD3 surface container */}
            <div className="w-20 h-20 rounded-[28px] bg-md-primary-container flex items-center justify-center mb-6 shadow-md-2">
              <svg className="w-10 h-10 text-md-on-primary-container" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
            </div>

            <h2 className="md-headline-medium text-md-on-surface mb-2">How can I help you?</h2>
            <p className="md-body-medium text-md-on-surface-variant max-w-sm mb-8">
              Ask me about stocks, markets, portfolio strategy, or any financial concept.
            </p>

            {/* MD3 suggestion chips */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl w-full px-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className="
                    relative text-left px-4 py-3 rounded-md-sm
                    border border-md-outline text-md-on-surface-variant
                    bg-md-surface hover:bg-md-surface-variant
                    md-body-medium transition-colors shadow-md-1
                    hover:border-md-primary hover:text-md-primary
                  "
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}

        {error && (
          <div className="flex justify-center">
            <div className="flex items-center gap-3 bg-md-error-container text-md-on-error-container md-body-medium px-5 py-3 rounded-md-md shadow-md-1 max-w-sm">
              <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              <span>{error}</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <InputBar onSend={send} isLoading={isLoading} />
    </div>
  );
}
