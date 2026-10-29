"use client"

const chatFetcher = async () => {
  throw new Error("Append-only chat: no LLM transport")
}

export const chatOptions = {
  fetcher: chatFetcher,
  tools: [],
}

export type ChatOptions = typeof chatOptions
