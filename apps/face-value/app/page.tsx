import React from "react"
import { ChatClient } from "@/chat/client"
import { getPublicOutcomes } from "@/outcomes"
import { SplitLayout } from "@/chat/shell/SplitLayout"

export const dynamic = "force-dynamic"

const Home = async () => {
  const outcomes = getPublicOutcomes()
  return <SplitLayout chat={<ChatClient outcomes={outcomes} />} />
}

export default Home