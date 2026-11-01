"use client"
import React from "react"
import { vocabulary } from "@/chat/vocabulary/en"

export const GenerateImageArtifact = ({ url }: { url: string }) => (
  <figure className="animate-in fade-in-50 slide-in-from-bottom-2 duration-500">
    <img src={url} alt={vocabulary.messages.resultAlt} className="w-full rounded-xl" />
  </figure>
)
