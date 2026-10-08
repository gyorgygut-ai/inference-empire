"use client";

import { useGenerateImage, fetchServerSentEvents } from "@tanstack/ai-react";
import { useRef, useState, useEffect } from "react";
import { vocabulary } from "@/messages/vocabulary";

export function GenerateImageTool({ part, result, interrupt }: any) {
  const { generate, isLoading, error } = useGenerateImage({
    connection: fetchServerSentEvents("/api/image"),
    threadId: `face-value-${part.id}`,
  });

  const [showBusyForAWhile, setShowBusyForAWhile] = useState(false);
  const busyTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  useEffect(() => {
    if (isLoading && !busyTimerRef.current) {
      busyTimerRef.current = setTimeout(() => setShowBusyForAWhile(true), 35000);
    }
    if (!isLoading) {
      if (busyTimerRef.current) {
        clearTimeout(busyTimerRef.current);
        busyTimerRef.current = null;
      }
      setShowBusyForAWhile(false);
    }
    return () => {
      if (busyTimerRef.current) {
        clearTimeout(busyTimerRef.current);
      }
    };
  }, [isLoading]);

  const firedRef = useRef(false);
  if (part.state === "awaiting-input" && part.arguments && !firedRef.current) {
    firedRef.current = true;
    const input = JSON.parse(part.arguments);
    const file = input.referenceImage;
    const reader = new FileReader();
    reader.onload = () => {
      generate({
        prompt: [
          { type: "image", source: { type: "data", value: reader.result as string, mimeType: file.type } },
          { type: "text", content: input.outcomePrompt },
        ],
      });
    };
    reader.readAsDataURL(file);
  }

  if (part.state === "error" || error) {
    return (
      <div className="p-4 text-red-500 animate-in fade-in-50">
        {vocabulary.messages.rejected}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-secondary-foreground animate-in fade-in-50">
        <span className="flex space-x-1">
          <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="size-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "300ms" }} />
        </span>
        {showBusyForAWhile && <span className="ml-2">{vocabulary.messages.busyForAWhile}</span>}
      </div>
    );
  }

  if (result?.imageUrl) {
    return (
      <figure style={{ aspectRatio: `${result.width} / ${result.height}` }} className="w-full overflow-hidden rounded-lg animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
        <img src={result.imageUrl} alt="Generated" className="h-full w-full object-cover" />
      </figure>
    );
  }

  return null;
}
