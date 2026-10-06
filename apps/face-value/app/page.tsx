import { getPublicOutcomes } from "@/outcomes";
import { ChatClient } from "@/components/assistant-ui/chat-client";

export const dynamic = "force-dynamic";

export default async function Home() {
  return (
    <main className="min-h-screen bg-background flex">
      <aside className="hidden md:flex md:w-2/3 bg-secondary border-r border-border" />
      <div className="flex-1 md:w-1/3 min-w-0 px-5 py-7">
        <ChatClient outcomes={getPublicOutcomes()} />
      </div>
    </main>
  );
}
