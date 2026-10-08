"use client";

import React from "react";
import { vocabulary } from "@/messages/vocabulary";

export const MessageRequestInference = ({
  disabled,
  onGenerateAction,
}: {
  disabled: boolean;
  onGenerateAction: () => void;
}) => (
  <div className="animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
    <button
      type="button"
      disabled={disabled}
      onClick={onGenerateAction}
      className="my-2 px-4 py-3 bg-primary text-primary-foreground rounded w-full disabled:bg-muted disabled:text-muted-foreground"
    >
      {vocabulary.messages.requestInference}
    </button>
  </div>
);