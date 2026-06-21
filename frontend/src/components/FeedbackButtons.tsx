import type { JSX } from "react";
import type { Message } from "../types";

interface FeedbackButtonsProps {
  message: Message;
  sessionId: string;
}

export function FeedbackButtons(_props: FeedbackButtonsProps): JSX.Element {
  // TODO: implement thumbs up / down with optimistic UI
  return <></>;
}
