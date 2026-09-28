import { getPublicOutcomes } from "@/outcomes"
import { ChatClient } from "@/components/assistant-ui/chat-client"
import type { Outcome } from "@/outcomes"

export const dynamic = "force-dynamic"

export default async function Home() {
  const outcomes = getPublicOutcomes() as Outcome[]

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <ChatClient outcomes={outcomes} />
      </div>
    </main>
  )
}