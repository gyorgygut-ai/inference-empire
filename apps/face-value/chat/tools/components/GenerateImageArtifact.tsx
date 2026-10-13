"use client"
import React from "react"
import { vocabulary } from "@/targets/face-value/vocabulary/en"

export const GenerateImageArtifact = ({ url }: { url: string }) => (
  <figure className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500">
    <img src={url} alt={vocabulary.messages.resultAlt} className="w-full rounded-xl" />
    <figcaption className="mt-2">
      <a href={url} download aria-labelledby="resultDownload" className="text-sm text-secondary-foreground underline">
        <span id="resultDownload" className="sr-only">{vocabulary.messages.download}</span>
        {vocabulary.messages.download}
      </a>
    </figcaption>
  </figure>
)
