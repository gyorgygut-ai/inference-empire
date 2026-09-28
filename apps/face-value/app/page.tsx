import { getPublicOutcomes } from "@/outcomes"
import { ChatClient } from "@/components/assistant-ui/chat-client"
import type { Outcome } from "@/outcomes"

export const dynamic = "force-dynamic"

export default async function Home() {
  const outcomes = getPublicOutcomes() as Outcome[]

  return (
    <main className="min-h-screen bg-background flex">
      <aside className="hidden lg:flex lg:w-2/3 bg-muted/30 items-center justify-center p-8 border-r border-border">
        <div className="text-center max-w-xl">
          <h1 className="text-4xl lg:text-6xl font-bold tracking-tight text-foreground mb-4">
            Transform Your Face
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Select an outcome, upload a reference image, and generate stunning AI transformations.
          </p>
          <div className="relative aspect-square max-w-md mx-auto rounded-2xl overflow-hidden bg-gradient-to-br from-primary/20 to-accent/20">
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-muted-foreground/50 text-lg">Hero Preview</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="flex-1 lg:w-1/3 min-w-0">
        <div className="h-full flex flex-col">
          <ChatClient outcomes={outcomes} />
        </div>
      </div>
    </main>
  )
}