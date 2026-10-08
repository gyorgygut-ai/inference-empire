"use client";

import React from "react";
import { ChatPhase } from "../chat";
import { vocabulary } from "@/messages/vocabulary";

export const MessageArtifact = ({
  state,
  image,
  width,
  height,
}: {
  state: ChatPhase;
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
        <div className="mt-2 text-sm text-secondary-foreground">
          {vocabulary.messages.busy}
        </div>
      )}
      {isRejected && <p>{vocabulary.messages.rejected}</p>}
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