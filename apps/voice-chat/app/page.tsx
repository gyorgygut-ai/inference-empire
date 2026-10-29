import React from "react"
import { ChatClient } from "@/chat/client"
import { SplitLayout } from "@/chat/shell/SplitLayout"

export const dynamic = "force-dynamic"

const Home = async () => {
  return <SplitLayout chat={<ChatClient />} />
}

export default Home
