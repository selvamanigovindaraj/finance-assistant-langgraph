import { type JSX, useRef, useState } from "react";

interface InputBarProps {
  onSend: (content: string) => Promise<void>;
  isLoading: boolean;
}

export function InputBar({ onSend, isLoading }: InputBarProps): JSX.Element {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  }

  async function submit(): Promise<void> {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await onSend(trimmed);
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  const canSubmit = value.trim().length > 0 && !isLoading;

  return (
    <div className="bg-md-background border-t border-md-outline-variant px-4 pt-3 pb-4">
      {/* MD3 Filled text field */}
      <div className="max-w-3xl mx-auto">
        <div
          className={`
            flex items-end gap-3 bg-md-surface-variant rounded-t-[4px] rounded-b-none
            border-b-2 transition-colors px-4 py-3
            ${isLoading ? "border-md-outline-variant" : "border-md-primary focus-within:border-md-primary"}
          `}
          style={{ borderBottom: `2px solid ${canSubmit || isLoading ? "#6750A4" : "#79747E"}` }}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            placeholder="Ask a financial question…"
            className="
              flex-1 bg-transparent resize-none outline-none
              md-body-large text-md-on-surface placeholder:text-md-on-surface-variant
              disabled:opacity-40 py-0.5 max-h-40 leading-relaxed
            "
          />

          {/* MD3 Icon button — send */}
          <button
            onClick={() => void submit()}
            disabled={!canSubmit}
            title="Send (Enter)"
            className="
              relative overflow-hidden flex-shrink-0 w-10 h-10 rounded-md-full
              flex items-center justify-center transition-colors
              disabled:opacity-30
              bg-md-primary text-md-on-primary
              hover:shadow-md-1 active:shadow-none
            "
          >
            {isLoading ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            )}
          </button>
        </div>

        <p className="md-label-small text-md-on-surface-variant text-center mt-2">
          Shift + Enter for new line · AI may be inaccurate — verify financial decisions independently
        </p>
      </div>
    </div>
  );
}
