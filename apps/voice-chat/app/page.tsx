import React from "react"
import { VoiceChatView } from "@/chat/realtime/VoiceChatView"
import { CenteredLayout } from "@/chat/shell/CenteredLayout"

export const dynamic = "force-dynamic"

const Home = async ({ searchParams }: { searchParams: Promise<{ provider?: string }> }) => {
  const { provider } = await searchParams
  const selectedProvider = provider === "openai" ? "openai" : "workers"
  return <CenteredLayout chat={<VoiceChatView key={selectedProvider} provider={selectedProvider} />} />
}

export default Home
