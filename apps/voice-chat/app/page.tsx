import React from "react"
import { VoiceChatView } from "@/chat/realtime/VoiceChatView"
import { CenteredLayout } from "@/chat/shell/CenteredLayout"

export const dynamic = "force-dynamic"

const Home = () => {
  return <CenteredLayout chat={<VoiceChatView />} />
}

export default Home
