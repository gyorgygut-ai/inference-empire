import { getPublicOutcomes } from "@/outcomes"
import ChatClient from "@/app/components/assistant-ui/chat-client"

export const dynamic = "force-dynamic"

export default async function Home() {
  const outcomes = await getPublicOutcomes()

  return (
    <main className="grid grid-cols-1 lg:grid-cols-3 gap-0 min-h-screen">
      <div className="hidden lg:block lg:col-span-2 bg-gray-100">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/hero.jpg" alt="" className="w-full h-full object-cover" />
      </div>
      <div className="col-span-1 lg:col-span-1 flex flex-col">
        <ChatClient outcomes={outcomes} />
      </div>
    </main>
  )
}
