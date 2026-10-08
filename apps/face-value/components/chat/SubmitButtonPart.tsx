"use client"
import React from "react"
import { vocabulary } from "@/messages"
import { useGenerateImage } from "@tanstack/ai-react"
import { generateImageAction } from "@/app/actions/generate-image"

export interface SubmitButtonPartProps {
  append: (message: { id: string; role: "user" | "assistant"; parts: any[] }) => void
}

export const SubmitButtonPart = React.memo(function SubmitButtonPart({ append }: SubmitButtonPartProps) {
  const { generate, isLoading } = useGenerateImage({
    fetcher: (input) => generateImageAction(input)
  })

  return (
    <div className="animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
      <button
        type="button"
        onClick={async () => {
          await append({
            id: crypto.randomUUID(),
            role: "assistant",
            parts: [{ type: "text", content: vocabulary.messages.working }],
          })
          await generate({
            prompt: [{ type: "text", content: "placeholder" }],
            modelOptions: { outcomeId: "placeholder" },
          })
        }}
        disabled={isLoading}
        aria-labelledby="requestInference"
        className="my-2 px-4 py-3 bg-primary text-primary-foreground rounded w-full"
      >
        <span id="requestInference" className="sr-only">{vocabulary.messages.requestInference}</span>
        {vocabulary.messages.requestInference}
      </button>
    </div>
  )
})