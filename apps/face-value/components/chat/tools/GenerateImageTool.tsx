"use client";

import React from "react";
import { vocabulary } from "@/messages";

export const GenerateImageTool = ({ part, result }: any) => {
  if (part.state === "error") {
    return (
      <div className="p-4 text-red-500 animate-in fade-in-50" aria-labelledby="errorRejected">
        <span id="errorRejected" className="sr-only">{vocabulary.messages.rejected}</span>
        {vocabulary.messages.rejected}
      </div>
    );
  }

  if (result?.imageUrl) {
    return (
      <figure style={{ aspectRatio: `${result.width} / ${result.height}` }} className="w-full overflow-hidden rounded-lg animate-in fade-in-50 slide-in-from-bottom-2 duration-300" aria-labelledby="resultDownload">
        <span id="resultDownload" className="sr-only">{vocabulary.messages.download}</span>
        <img src={result.imageUrl} alt={vocabulary.messages.resultAlt} className="h-full w-full object-cover" />
        <figcaption className="sr-only">{vocabulary.messages.fulfilled}</figcaption>
      </figure>
    );
  }

  return (
    <div className="flex items-center gap-2 text-sm text-secondary-foreground animate-in fade-in-50" aria-labelledby="statusWorking">
      <span id="statusWorking" className="sr-only">{vocabulary.messages.working}</span>
      <span className="flex space-x-1">
        <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "300ms" }} />
      </span>
      <span className="ml-2 opacity-0 animate-in fade-in-50 [animation-delay:35s] [animation-fill-mode:forwards]">{vocabulary.messages.busyForAWhile}</span>
    </div>
  );
};
