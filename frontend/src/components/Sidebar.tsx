import type { JSX } from "react";

interface SidebarProps {
  onNewChat?: () => void;
}

export function Sidebar({ onNewChat }: SidebarProps): JSX.Element {
  return (
    <aside className="w-[280px] flex-shrink-0 flex flex-col h-full bg-md-surface-1 border-r border-md-outline-variant">
      {/* Header */}
      <div className="px-6 pt-8 pb-4">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-md-md bg-md-primary flex items-center justify-center shadow-md-1">
            <svg className="w-5 h-5 text-md-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <div>
            <p className="md-title-medium text-md-on-surface">Finance AI</p>
            <p className="md-label-small text-md-on-surface-variant">Powered by Claude</p>
          </div>
        </div>

        {/* New Chat — MD3 FAB extended style */}
        <button
          onClick={onNewChat}
          className="relative overflow-hidden w-full flex items-center gap-3 px-4 py-3.5 rounded-md-lg bg-md-primary-container text-md-on-primary-container md-label-large transition-colors hover:bg-[#e2d1ff] active:bg-[#d8c5ff] shadow-md-1"
        >
          <svg className="w-[18px] h-[18px] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New conversation
        </button>
      </div>

      {/* Nav label */}
      <div className="px-6 py-2">
        <p className="md-label-small text-md-on-surface-variant uppercase tracking-widest">Recent</p>
      </div>

      {/* Empty state for recents */}
      <div className="flex-1 px-3 py-2">
        <div className="flex flex-col items-center justify-center h-32 gap-2">
          <svg className="w-8 h-8 text-md-outline-variant" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="md-body-small text-md-on-surface-variant text-center">
            Your conversations<br />will appear here
          </p>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 border-t border-md-outline-variant" />

      {/* Footer */}
      <div className="px-6 py-5 flex items-start gap-3">
        <svg className="w-4 h-4 flex-shrink-0 text-md-on-surface-variant mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
        </svg>
        <p className="md-body-small text-md-on-surface-variant leading-relaxed">
          For informational purposes only. Not financial advice.
        </p>
      </div>
    </aside>
  );
}
