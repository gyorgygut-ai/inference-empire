"use client";

import React from "react";
import { ChatPhase } from "../chat";
import { vocabulary } from "@/messages/vocabulary";

export const MessageArtifact = ({
  state,
  content,
  image,
  width,
  height,
}: {
  state: ChatPhase;
  content?: string;
  image?: string;
  width?: number;
  height?: number;
}) => {
  const isBusy = state === ChatPhase.INFERENCE_BUSY;
  const isRejected = state === ChatPhase.INFERENCE_REJECTED;
  const isFulfilled = state === ChatPhase.INFERENCE_FULFILLED && image;

  return (
    <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4">
      {isBusy && (
        <div className="flex items-center gap-2 text-sm text-secondary-foreground">
          <span className="flex space-x-1">
            <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "300ms" }} />
          </span>
          {content && <span className="ml-2">{content}</span>}
        </div>
      )}
      {isRejected && <p>{content ?? vocabulary.messages.rejected}</p>}
      {isFulfilled && (
        <>
          <figure
            style={{ aspectRatio: `${width} / ${height}` }}
            className="w-full overflow-hidden rounded-lg"
          >
            <img
              src={image}
              alt="Generated"
              className="h-full w-full object-cover"
            />
          </figure>
        </>
      )}
    </div>
  );
};