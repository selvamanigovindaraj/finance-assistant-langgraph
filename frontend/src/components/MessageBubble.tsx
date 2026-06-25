import type { JSX } from "react";
import type { Message } from "../types";

const TOOL_LABELS: Record<string, string> = {
  get_quote: "Stock Quote",
  budget_calc: "Budget Calc",
  categorise_expense: "Expense Category",
};

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
        {/* Tool badge */}
        {message.tool_used && (
          <span className="mb-1.5 inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md-full bg-md-secondary-container text-md-on-secondary-container md-label-small">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
            </svg>
            {TOOL_LABELS[message.tool_used] ?? message.tool_used}
          </span>
        )}
        {/* MD3 Chat bubble — assistant: surface variant */}
        <div className="bg-md-surface border border-md-outline-variant px-4 py-3 rounded-[20px] rounded-tl-[4px] shadow-md-1">
          <p className="md-body-large text-md-on-surface whitespace-pre-wrap leading-relaxed">{message.content}</p>
          {message.disclaimer && (
            <p className="md-label-small text-md-on-surface-variant mt-2 pt-2 border-t border-md-outline-variant">
              {message.disclaimer}
            </p>
          )}
        </div>
        <p className="md-label-small text-md-on-surface-variant mt-1 ml-1">{time}</p>
      </div>
    </div>
  );
}
