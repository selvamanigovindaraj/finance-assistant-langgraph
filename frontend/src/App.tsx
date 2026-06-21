import type { JSX } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
import { useChat } from "./hooks/useChat";

export default function App(): JSX.Element {
  const chat = useChat();

  return (
    <div className="flex h-screen overflow-hidden bg-md-background">
      <Sidebar onNewChat={chat.clear} />
      <main className="flex-1 overflow-hidden">
        <ChatWindow chat={chat} />
      </main>
    </div>
  );
}
