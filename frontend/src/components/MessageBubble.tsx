import type { JSX } from "react";
import type { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
}

function AssistantAvatar(): JSX.Element {
  return (
    <div className="flex-shrink-0 w-8 h-8 rounded-md-full bg-md-primary flex items-center justify-center shadow-md-1 mr-3 mt-0.5">
      <svg className="w-4 h-4 text-md-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    </div>
  );
}

function UserAvatar(): JSX.Element {
  return (
    <div className="flex-shrink-0 w-8 h-8 rounded-md-full bg-md-secondary-container flex items-center justify-center ml-3 mt-0.5">
      <svg className="w-4 h-4 text-md-on-secondary-container" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps): JSX.Element {
  const isUser = message.role === "user";
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (isUser) {
    return (
      <div className="flex justify-end items-start">
        <div className="flex flex-col items-end max-w-[70%]">
          {/* MD3 Chat bubble — user: primary container */}
          <div className="bg-md-primary text-md-on-primary px-4 py-3 rounded-[20px] rounded-tr-[4px] shadow-md-1">
            <p className="md-body-large whitespace-pre-wrap">{message.content}</p>
          </div>
          <p className="md-label-small text-md-on-surface-variant mt-1 mr-1">{time}</p>
        </div>
        <UserAvatar />
      </div>
    );
  }

  return (
    <div className="flex justify-start items-start">
      <AssistantAvatar />
      <div className="flex flex-col items-start max-w-[70%]">
        {/* MD3 Chat bubble — assistant: surface variant */}
        <div className="bg-md-surface border border-md-outline-variant px-4 py-3 rounded-[20px] rounded-tl-[4px] shadow-md-1">
          <p className="md-body-large text-md-on-surface whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
        <p className="md-label-small text-md-on-surface-variant mt-1 ml-1">{time}</p>
      </div>
    </div>
  );
}
