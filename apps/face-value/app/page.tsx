import { getPublicOutcomes } from "@/outcomes"
import { ChatClient } from "@/components/assistant-ui/chat-client"
import type { PublicOutcome } from "@/outcomes"

export const dynamic = "force-dynamic"

export default async function Home() {
  const outcomes = getPublicOutcomes() as PublicOutcome[]

  return (
    <main className="min-h-screen bg-background flex">
      <aside className="hidden lg:flex lg:w-2/3 bg-muted/30 border-r border-border" />

      <div className="flex-1 lg:w-1/3 min-w-0">
        <div className="h-full flex flex-col">
          <ChatClient outcomes={outcomes} />
        </div>
      </div>
    </main>
  )
}