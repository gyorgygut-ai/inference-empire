"use client"
import React from "react"
import { vocabulary } from "@/targets/face-value/vocabulary/en"

export const Spinner = () => (
  <div className="my-2 flex items-center gap-2" role="status" aria-label={vocabulary.messages.working}>
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    <span className="text-sm text-secondary-foreground">{vocabulary.messages.working}</span>
  </div>
)
