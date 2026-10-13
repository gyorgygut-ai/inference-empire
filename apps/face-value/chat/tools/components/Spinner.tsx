"use client"
import React from "react"
import { vocabulary } from "@packages/ui/chat/vocabulary/en"

export const Spinner = () => (
  <div className="my-2 flex items-center gap-2" role="status" aria-labelledby="statusWorking">
    <span id="statusWorking" className="sr-only">{vocabulary.messages.working}</span>
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    <span className="text-sm text-secondary-foreground">{vocabulary.messages.working}</span>
  </div>
)