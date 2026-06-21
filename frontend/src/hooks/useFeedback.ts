import { useState } from "react";
import type { FeedbackPayload } from "../types";

interface UseFeedbackReturn {
  isSubmitting: boolean;
  submit: (payload: FeedbackPayload) => Promise<void>;
}

export function useFeedback(): UseFeedbackReturn {
  const [isSubmitting, _setIsSubmitting] = useState(false);

  async function submit(_payload: FeedbackPayload): Promise<void> {
    // TODO: implement
    throw new Error("Not implemented");
  }

  return { isSubmitting, submit };
}
