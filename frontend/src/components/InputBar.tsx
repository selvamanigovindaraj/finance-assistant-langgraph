import type { JSX } from "react";

interface InputBarProps {
  onSend: (content: string) => Promise<void>;
  isLoading: boolean;
}

export function InputBar(_props: InputBarProps): JSX.Element {
  // TODO: implement controlled textarea, submit on Enter, disable while loading
  return <></>;
}
