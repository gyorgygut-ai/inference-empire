import { getPublicOutcomes } from "@/outcomes"
import { ChatClient } from "@/app/components/assistant-ui/chat-client"
import type { Outcome } from "@/outcomes"

export const dynamic = "force-dynamic"

export default async function Home() {
  const outcomes = getPublicOutcomes() as Outcome[]

  return (
    <main className="grid grid-cols-1 lg:grid-cols-3 gap-0 min-h-screen">
      <div className="hidden bg-muted lg:col-span-2 lg:block" />
      <div className="col-span-1 lg:col-span-1 flex flex-col">
        <ChatClient outcomes={outcomes} />
      </div>
    </main>
  )
}
