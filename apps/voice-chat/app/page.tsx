import React from "react"
import { VoiceChatView } from "@/chat/realtime/VoiceChatView"
import { CenteredLayout } from "@/chat/shell/CenteredLayout"

export const dynamic = "force-dynamic"

const Home = async () => {
  return <CenteredLayout chat={<VoiceChatView connected={false} />} />
}

export default Home
